"""Statistics over a run.

Both arms are reduced to the same object — a probability distribution over the
answer set for each (probe, persona, arm) — so they can be compared directly:

    Jev arm       mean of the distributions returned across replicates
    baseline arm  empirical frequency of parsed answers across resamples

That reduction is the whole point of the study. Jev reports its distribution;
the baseline's has to be paid for N times and estimated. Downstream, every
statistic consumes a distribution, never an argmax.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .benchmarks import BENCHMARKS

Dist = dict[str, float]
Key = tuple[str, str, str]  # (probe_id, persona, arm)


def latest_run(raw_dir: Path) -> Path | None:
    runs = sorted(raw_dir.glob("run_*.jsonl"))
    return runs[-1] if runs else None


def load_records(path: Path) -> pd.DataFrame:
    with path.open(encoding="utf-8") as fh:
        rows = [json.loads(line) for line in fh if line.strip()]
    df = pd.DataFrame(rows)
    backends = set(df["backend"].unique())
    if "simulator" in backends and len(backends) > 1:
        raise ValueError(
            f"Run mixes simulated and live records ({sorted(backends)}). "
            "Simulated output is structurally valid nonsense and must never be "
            "pooled with live data."
        )
    return df


def distributions(df: pd.DataFrame) -> dict[Key, Dist]:
    """Collapse replicates into one distribution per (probe, persona, arm)."""
    out: dict[Key, Dist] = {}
    ok = df[df["error"].isna()] if "error" in df.columns else df

    jev = ok[ok["arm"] == "jev"]
    for (pid, persona), grp in jev.groupby(["probe_id", "persona"]):
        acc: dict[str, list[float]] = defaultdict(list)
        for probs in grp["probabilities"]:
            if not probs:
                continue
            for k, v in probs.items():
                acc[k].append(float(v))
        if not acc:
            continue
        n = float(len(grp))
        # Options absent from a given replicate contribute zero to the mean.
        dist = {k: float(np.sum(v)) / n for k, v in acc.items()}
        total = sum(dist.values()) or 1.0
        out[(pid, persona, "jev")] = {k: v / total for k, v in dist.items()}

    base = ok[ok["arm"] == "baseline"]
    for (pid, persona), grp in base.groupby(["probe_id", "persona"]):
        vals = [v for v in grp["value"].tolist() if v is not None and v == v]
        if not vals:
            continue
        counts: dict[str, float] = defaultdict(float)
        for v in vals:
            counts[str(v)] += 1.0
        n = float(len(vals))
        out[(pid, persona, "baseline")] = {k: c / n for k, c in counts.items()}
    return out


# -- primitives ---------------------------------------------------------


def prob_of(dist: Dist, *keys: str) -> float:
    return float(sum(dist.get(k, 0.0) for k in keys))


def expected_numeric(dist: Dist, parse: Any = None) -> float | None:
    """Expected value of a distribution whose keys encode numbers."""
    parse = parse or _default_parse
    num, den = 0.0, 0.0
    for k, p in dist.items():
        v = parse(k)
        if v is None:
            continue
        num += v * p
        den += p
    return None if den == 0 else num / den


def _default_parse(key: str) -> float | None:
    s = key.strip().lstrip("$").replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def expected_level(dist: Dist, n_levels: int, *, reverse: bool = False) -> float | None:
    """Expected 1-based level for a Score item, from the returned index weights."""
    num, den = 0.0, 0.0
    for k, p in dist.items():
        try:
            idx = int(k)
        except ValueError:
            continue
        if reverse:
            idx = (n_levels - 1) - idx
        num += (idx + 1) * p
        den += p
    return None if den == 0 else num / den


def tv_distance(a: Dist, b: Dist) -> float:
    keys = set(a) | set(b)
    return 0.5 * float(sum(abs(a.get(k, 0.0) - b.get(k, 0.0)) for k in keys))


def bootstrap_ci(values: list[float], n: int = 10000, seed: int = 7) -> tuple[float, float]:
    arr = np.asarray([v for v in values if v is not None and np.isfinite(v)], dtype=float)
    if arr.size == 0:
        return (float("nan"), float("nan"))
    if arr.size == 1:
        return (float(arr[0]), float(arr[0]))
    rng = np.random.default_rng(seed)
    means = rng.choice(arr, size=(n, arr.size), replace=True).mean(axis=1)
    return (float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)))


# -- per-instrument statistics -----------------------------------------


@dataclass(slots=True)
class Stat:
    instrument: str
    statistic: str
    persona: str
    arm: str
    value: float
    ci_low: float = float("nan")
    ci_high: float = float("nan")
    benchmark_key: str = ""
    human_value: float = float("nan")
    reliability: str = ""
    note: str = ""


def _meta_for(df: pd.DataFrame) -> dict[str, dict[str, Any]]:
    meta: dict[str, dict[str, Any]] = {}
    for pid, grp in df.groupby("probe_id"):
        m = grp.iloc[0]["meta"]
        meta[str(pid)] = m if isinstance(m, dict) else {}
    return meta


def _replicate_dists(df: pd.DataFrame, pid: str, persona: str) -> list[Dist]:
    sel = df[(df["probe_id"] == pid) & (df["persona"] == persona) & (df["arm"] == "jev")]
    return [p for p in sel["probabilities"].tolist() if p]


def compute_stats(df: pd.DataFrame) -> list[Stat]:
    dists = distributions(df)
    meta = _meta_for(df)
    personas = sorted(df["persona"].unique())
    arms = sorted(df["arm"].unique())
    stats: list[Stat] = []

    def add(
        inst: str,
        name: str,
        persona: str,
        arm: str,
        value: float | None,
        *,
        ci: tuple[float, float] | None = None,
        bench: str = "",
        note: str = "",
    ) -> None:
        if value is None or not np.isfinite(value):
            return
        b = BENCHMARKS.get(bench)
        stats.append(
            Stat(
                instrument=inst,
                statistic=name,
                persona=persona,
                arm=arm,
                value=float(value),
                ci_low=ci[0] if ci else float("nan"),
                ci_high=ci[1] if ci else float("nan"),
                benchmark_key=bench,
                human_value=b.value if b else float("nan"),
                reliability=b.reliability if b else "",
                note=note,
            )
        )

    def by_probe(pids: list[str]) -> dict[str, dict[Key, Dist]]:
        return {pid: {k: v for k, v in dists.items() if k[0] == pid} for pid in pids}

    for persona in personas:
        for arm in arms:

            def g(pid: str, _p: str = persona, _a: str = arm) -> Dist | None:
                return dists.get((pid, _p, _a))

            # --- cognitive reflection -------------------------------
            crt = [p for p in meta if p.startswith("crt_")]
            corr, lure = [], []
            for pid in crt:
                d = g(pid)
                if not d:
                    continue
                corr.append(prob_of(d, str(meta[pid].get("correct"))))
                lure.append(prob_of(d, str(meta[pid].get("lure"))))
            if corr:
                add(
                    "crt",
                    "proportion_correct",
                    persona,
                    arm,
                    float(np.mean(corr)),
                    ci=bootstrap_ci(corr),
                    bench="crt_proportion_correct",
                )
                add(
                    "crt",
                    "probability_mass_on_lure",
                    persona,
                    arm,
                    float(np.mean(lure)),
                    ci=bootstrap_ci(lure),
                )

            # --- fluid reasoning ------------------------------------
            rea = [p for p in meta if p.startswith("reason_")]
            acc_all: list[float] = []
            by_steps: dict[int, list[float]] = defaultdict(list)
            for pid in rea:
                d = g(pid)
                if not d:
                    continue
                a = prob_of(d, str(meta[pid].get("correct")))
                acc_all.append(a)
                by_steps[int(meta[pid].get("steps", 0))].append(a)
            if acc_all:
                add(
                    "fluid_reasoning",
                    "accuracy",
                    persona,
                    arm,
                    float(np.mean(acc_all)),
                    ci=bootstrap_ci(acc_all),
                    note="accuracy on an authored ICAR-format item set; not an IQ score",
                )
                for steps in sorted(by_steps):
                    add(
                        "fluid_reasoning",
                        f"accuracy_steps_{steps}",
                        persona,
                        arm,
                        float(np.mean(by_steps[steps])),
                        ci=bootstrap_ci(by_steps[steps]),
                    )
                shallow = by_steps.get(1, [])
                deep = by_steps.get(3, []) + by_steps.get(4, [])
                if shallow and deep:
                    add(
                        "fluid_reasoning",
                        "depth_penalty_1_vs_3plus",
                        persona,
                        arm,
                        float(np.mean(shallow) - np.mean(deep)),
                        note="H8: accuracy at 1 step minus accuracy at 3+ steps",
                    )

            # --- allocation games -----------------------------------
            for pid, inst, bench in (
                ("dictator_allocation", "dictator", "dictator_mean_share"),
                ("ultimatum_offer", "ultimatum_proposer", "ultimatum_mean_offer"),
                ("trust_send", "trust_sender", "trust_sender_share"),
                ("pgg_round1", "public_goods", "pgg_round1_share"),
            ):
                d = g(pid)
                if d:
                    ev = expected_numeric(d)
                    pie = float(meta.get(pid, {}).get("pie", 10) or 10)
                    add(
                        inst,
                        "mean_share",
                        persona,
                        arm,
                        None if ev is None else ev / pie,
                        bench=bench,
                    )
                    if pid == "dictator_allocation":
                        add(
                            inst,
                            "prob_give_zero",
                            persona,
                            arm,
                            prob_of(d, "$0"),
                            bench="dictator_share_zero",
                        )
                        add(
                            inst,
                            "prob_give_half",
                            persona,
                            arm,
                            prob_of(d, "$5"),
                            bench="dictator_share_half",
                        )

            # --- ultimatum responder curve --------------------------
            low_rej = []
            for offer in range(11):
                d = g(f"ultimatum_respond_{offer}")
                if not d:
                    continue
                rej = prob_of(d, "reject")
                add("ultimatum_responder", f"prob_reject_offer_{offer}", persona, arm, rej)
                if offer <= 1:
                    low_rej.append(rej)
            if low_rej:
                add(
                    "ultimatum_responder",
                    "prob_reject_low_offer",
                    persona,
                    arm,
                    float(np.mean(low_rej)),
                    bench="ultimatum_rejection_low_offer",
                )

            # --- trustee reciprocity --------------------------------
            for sent in (2, 5, 10):
                d = g(f"trust_return_{sent}")
                if d:
                    ev = expected_numeric(d)
                    add(
                        "trust_trustee",
                        f"return_share_sent_{sent}",
                        persona,
                        arm,
                        None if ev is None else ev / (sent * 3),
                        bench="trust_return_share" if sent == 5 else "",
                    )

            # --- conditional cooperation ----------------------------
            for label in ("low", "mid", "high"):
                d = g(f"pgg_conditional_{label}")
                if d:
                    ev = expected_numeric(d)
                    add(
                        "public_goods_conditional",
                        f"contribution_{label}",
                        persona,
                        arm,
                        None if ev is None else ev / 10.0,
                    )

            # --- prisoner's dilemma ---------------------------------
            for pid, label, bench in (
                ("pd_oneshot", "cooperation_one_shot", "pd_cooperation_oneshot"),
                ("pd_after_cooperation", "cooperation_after_cooperation", ""),
                ("pd_after_defection", "cooperation_after_defection", ""),
            ):
                d = g(pid)
                if d:
                    add(
                        "prisoners_dilemma",
                        label,
                        persona,
                        arm,
                        prob_of(d, "cooperate"),
                        bench=bench,
                    )

            # --- framing --------------------------------------------
            gain, loss = g("framing_gain"), g("framing_loss")
            if gain:
                add(
                    "framing",
                    "prob_certain_gain_frame",
                    persona,
                    arm,
                    prob_of(gain, "program_a"),
                    bench="framing_gain_certain",
                )
            if loss:
                add(
                    "framing",
                    "prob_certain_loss_frame",
                    persona,
                    arm,
                    prob_of(loss, "program_c"),
                    bench="framing_loss_certain",
                )
            if gain and loss:
                add(
                    "framing",
                    "framing_swing",
                    persona,
                    arm,
                    prob_of(gain, "program_a") - prob_of(loss, "program_c"),
                    note="H4: human swing is about 0.50 (0.72 - 0.22)",
                )

            # --- Allais ---------------------------------------------
            p1, p2 = g("allais_problem1"), g("allais_problem2")
            if p1:
                add(
                    "allais",
                    "prob_certain_pair1",
                    persona,
                    arm,
                    prob_of(p1, "option_a"),
                    bench="allais_p1_certain",
                )
            if p2:
                add(
                    "allais",
                    "prob_safer_pair2",
                    persona,
                    arm,
                    prob_of(p2, "option_c"),
                    bench="allais_p2_certain",
                )
            if p1 and p2:
                add(
                    "allais",
                    "independence_violation",
                    persona,
                    arm,
                    prob_of(p1, "option_a") * prob_of(p2, "option_d"),
                    note="joint probability of the A-then-D pattern that violates independence",
                )

            # --- conjunction ----------------------------------------
            forced = g("conjunction_forced_choice")
            if forced:
                add(
                    "conjunction",
                    "prob_fallacy_forced_choice",
                    persona,
                    arm,
                    prob_of(forced, "teller_and_feminist"),
                    bench="conjunction_fallacy_rate",
                )
            single, conj = g("conjunction_p_single"), g("conjunction_p_conjunction")
            if single and conj:
                p_a, p_ab = single.get("true", 0.0), conj.get("true", 0.0)
                add("conjunction_axiom", "p_single", persona, arm, p_a)
                add("conjunction_axiom", "p_conjunction", persona, arm, p_ab)
                add(
                    "conjunction_axiom",
                    "axiom_margin",
                    persona,
                    arm,
                    p_a - p_ab,
                    note="H5: negative means P(A and B) > P(A), violating the conjunction rule",
                )

            # --- base rate ------------------------------------------
            d = g("base_rate_mammogram")
            if d:
                add(
                    "base_rate",
                    "prob_correct_band",
                    persona,
                    arm,
                    prob_of(d, "0-10%"),
                    bench="base_rate_correct_band",
                )
                add("base_rate", "prob_lure_band", persona, arm, prob_of(d, "70-90%"))

            # --- anchoring ------------------------------------------
            band_mid = {
                "0-15%": 7.5,
                "15-25%": 20,
                "25-35%": 30,
                "35-45%": 40,
                "45-55%": 50,
                "55-100%": 70,
            }
            lo, hi = g("anchoring_low"), g("anchoring_high")
            if lo:
                add(
                    "anchoring",
                    "estimate_low_anchor",
                    persona,
                    arm,
                    expected_numeric(lo, band_mid.get),
                    bench="anchoring_low_median",
                )
            if hi:
                add(
                    "anchoring",
                    "estimate_high_anchor",
                    persona,
                    arm,
                    expected_numeric(hi, band_mid.get),
                    bench="anchoring_high_median",
                )
            if lo and hi:
                a_val = expected_numeric(lo, band_mid.get)
                b_val = expected_numeric(hi, band_mid.get)
                if a_val is not None and b_val is not None:
                    add(
                        "anchoring",
                        "anchoring_effect",
                        persona,
                        arm,
                        b_val - a_val,
                        note="human gap is about 20 points",
                    )

            # --- sunk cost ------------------------------------------
            d = g("sunk_cost")
            if d:
                add(
                    "sunk_cost",
                    "prob_continue",
                    persona,
                    arm,
                    prob_of(d, "continue"),
                    bench="sunk_cost_continue",
                )

            # --- Holt-Laury -----------------------------------------
            safe = []
            for row in range(1, 11):
                d = g(f"holt_laury_{row:02d}")
                if d:
                    safe.append(prob_of(d, "option_a"))
            if len(safe) == 10:
                add(
                    "holt_laury",
                    "expected_safe_choices",
                    persona,
                    arm,
                    float(np.sum(safe)),
                    bench="holt_laury_safe_choices",
                    note="risk neutral is 4; higher means more risk averse",
                )

            # --- discounting ----------------------------------------
            for delay in (7, 30, 180):
                vals = []
                for later in (52, 60, 75, 100):
                    d = g(f"discount_{delay}d_{later}")
                    if d:
                        vals.append(prob_of(d, "later"))
                if vals:
                    add(
                        "discounting",
                        f"prob_patient_{delay}d",
                        persona,
                        arm,
                        float(np.mean(vals)),
                        ci=bootstrap_ci(vals),
                    )
            now_d, del_d = g("present_bias_now"), g("present_bias_delayed")
            if now_d and del_d:
                add(
                    "present_bias",
                    "prob_patient_immediate_frontend",
                    persona,
                    arm,
                    prob_of(now_d, "later"),
                )
                add(
                    "present_bias",
                    "prob_patient_delayed_frontend",
                    persona,
                    arm,
                    prob_of(del_d, "later"),
                )
                add(
                    "present_bias",
                    "present_bias_gap",
                    persona,
                    arm,
                    prob_of(del_d, "later") - prob_of(now_d, "later"),
                    bench="present_bias_reversal",
                    note="positive means more patient when both options are delayed",
                )

            # --- strategic ------------------------------------------
            d = g("beauty_contest_2_3")
            if d:
                add(
                    "beauty_contest",
                    "expected_guess",
                    persona,
                    arm,
                    expected_numeric(d),
                    bench="beauty_contest_mean",
                )
                add("beauty_contest", "mass_at_33", persona, arm, prob_of(d, "33"))
                add("beauty_contest", "mass_at_22", persona, arm, prob_of(d, "22"))
                add("beauty_contest", "mass_at_0", persona, arm, prob_of(d, "0"))
            d = g("money_request_11_20")
            if d:
                add(
                    "money_request",
                    "expected_request",
                    persona,
                    arm,
                    expected_numeric(d),
                    bench="money_request_modal",
                )
                for lvl_name, val in (
                    ("level0", 20),
                    ("level1", 19),
                    ("level2", 18),
                    ("level3", 17),
                ):
                    add(
                        "money_request",
                        f"mass_{lvl_name}_{val}",
                        persona,
                        arm,
                        prob_of(d, str(val)),
                    )

            # --- personality ----------------------------------------
            traits: dict[str, list[float]] = defaultdict(list)
            for pid, m in meta.items():
                if not pid.startswith("ipip_"):
                    continue
                d = g(pid)
                if not d:
                    continue
                lvl = expected_level(d, int(m.get("n_levels", 5)), reverse=bool(m.get("reverse")))
                if lvl is not None:
                    traits[str(m.get("trait"))].append(lvl)
            for trait, vals in traits.items():
                add(
                    "mini_ipip",
                    trait,
                    persona,
                    arm,
                    float(np.mean(vals)),
                    ci=bootstrap_ci(vals),
                    bench=f"mini_ipip_{trait}",
                )

            # --- dark triad -----------------------------------------
            dd: dict[str, list[float]] = defaultdict(list)
            for pid, m in meta.items():
                if not pid.startswith("dd_"):
                    continue
                d = g(pid)
                if not d:
                    continue
                lvl = expected_level(d, int(m.get("n_levels", 9)))
                if lvl is not None:
                    dd[str(m.get("trait"))].append(lvl)
                    dd["_total"].append(lvl)
            for trait, vals in dd.items():
                name = "overall" if trait == "_total" else trait
                add(
                    "dirty_dozen",
                    name,
                    persona,
                    arm,
                    float(np.mean(vals)),
                    ci=bootstrap_ci(vals),
                    note="9-point agreement scale; manipulation check only",
                )

    return stats


def order_effects(df: pd.DataFrame) -> pd.DataFrame:
    """H6: how much does permuting option order move the distribution?"""
    rows = []
    jev = df[(df["arm"] == "jev") & (df["error"].isna())] if "error" in df.columns else df
    for (pid, persona), grp in jev.groupby(["probe_id", "persona"]):
        ds = [p for p in grp["probabilities"].tolist() if p]
        if len(ds) < 2:
            continue
        pair_tv = [tv_distance(ds[i], ds[j]) for i in range(len(ds)) for j in range(i + 1, len(ds))]
        rows.append(
            {
                "probe_id": pid,
                "persona": persona,
                "n_replicates": len(ds),
                "mean_tv_distance": float(np.mean(pair_tv)),
                "max_tv_distance": float(np.max(pair_tv)),
            }
        )
    return pd.DataFrame(rows)


def analyse_run(path: Path, out_dir: Path) -> dict[str, Any]:
    df = load_records(path)
    out_dir.mkdir(parents=True, exist_ok=True)

    stats = compute_stats(df)
    sdf = pd.DataFrame([asdict(s) for s in stats])
    sdf.to_csv(out_dir / "statistics.csv", index=False)

    odf = order_effects(df)
    odf.to_csv(out_dir / "order_effects.csv", index=False)

    n_err = int(df["error"].notna().sum()) if "error" in df.columns else 0
    cost = float(sum(float((u or {}).get("cost") or 0.0) for u in df["usage"]))
    summary = {
        "run_file": path.name,
        "backend": sorted(df["backend"].unique()),
        "models": sorted(df["model"].unique()),
        "n_records": len(df),
        "n_errors": n_err,
        "total_cost_usd": round(cost, 4),
        "personas": sorted(df["persona"].unique()),
        "arms": sorted(df["arm"].unique()),
        "n_statistics": len(sdf),
        "mean_order_tv": float(odf["mean_tv_distance"].mean()) if len(odf) else None,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))

    print(json.dumps(summary, indent=2))
    print(f"\nwrote {out_dir / 'statistics.csv'} ({len(sdf)} rows)")
    print(f"wrote {out_dir / 'order_effects.csv'} ({len(odf)} rows)")
    return summary
