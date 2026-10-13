"""Statistics over a run.

Both arms are reduced to the same object — a probability distribution over the
answer set for each (probe, persona, arm) — so they can be compared directly:

    Jev arm       mean of the distributions returned across replicates
    baseline arm  empirical frequency of parsed answers across resamples

That reduction is the whole point of the project. Jev reports its distribution;
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

# The three items Frederick (2005) published, the only ones his benchmark covers.
FREDERICK_CRT = frozenset({"crt_bat_ball", "crt_widgets", "crt_lilypads"})


def latest_run(raw_dir: Path, model: str | None = None) -> Path | None:
    """The newest run file, optionally only those whose name carries `model`.

    Names are run_<live|simulated>_<timestamp>_<models>.jsonl, so files are
    ordered by their timestamp rather than by name, which would put every
    simulated run after every live one.
    """
    runs = [p for p in raw_dir.glob("run_*.jsonl") if model is None or model in p.name]
    return max(runs, key=lambda p: (p.name.split("_")[2:3], p.name)) if runs else None


def _has_jev(run: Path) -> bool:
    """Whether a run file holds Jev, under either backend's model slug.

    Names are run_<tag>_<timestamp>_<slug>[+<slug>].jsonl: the OpenRouter slug
    is `typesafe--jev-...`, the native TypeSafe one `jev-...`.
    """
    parts = run.stem.split("_", 3)
    slugs = parts[3].split("+") if len(parts) == 4 else []
    return any(s.startswith(("typesafe--jev", "jev-")) for s in slugs)


def primary_run(raw_dir: Path, live_only: bool = False) -> Path | None:
    """The run the write-up is about: the newest one that includes Jev.

    Anything that writes committed files (the editorial diagrams, RESULTS.md)
    passes `live_only`, so a simulated run left in data/raw/ can never stand in
    for the live one there, and nor can another model's run.
    """
    pattern = "run_live_*.jsonl" if live_only else "run_*.jsonl"
    jev = [p for p in raw_dir.glob(pattern) if _has_jev(p)]
    if jev:
        return max(jev, key=lambda p: (p.name.split("_")[2:3], p.name))
    return None if live_only else latest_run(raw_dir)


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
    return _reread_chat_replies(df)


def _reread_chat_replies(df: pd.DataFrame) -> pd.DataFrame:
    """Re-derive each chat reply's answer from its raw text with the current parser.

    The run file keeps the raw reply, so a parser fix reaches committed runs
    without editing them. Chat records for items that ask for a proportion
    get no answer and are flagged `not_measurable` (see `noul_probe`), so
    health.csv can count them apart from replies that failed to parse.
    """
    from .client import parse_option
    from .instruments import PERSONAS, all_probes, apply_persona
    from .runner import render_prompt

    df["not_measurable"] = False
    if "arm" not in df.columns or not (df["arm"] == "baseline").any():
        return df
    probes = {p.probe_id: p for p in all_probes(None)}
    proportion = {pid for pid, p in probes.items() if p.meta.get("asks_for") == "proportion"}
    flagged = (df["arm"] == "baseline") & df["probe_id"].isin(proportion)
    df["not_measurable"] = flagged
    df.loc[flagged, "value"] = None

    options: dict[str, list[str]] = {}
    for idx in df.index[(df["arm"] == "baseline") & ~flagged]:
        row = df.loc[idx]
        if isinstance(row.get("error"), str) or row["probe_id"] not in probes:
            continue
        meta = row["meta"] if isinstance(row["meta"], dict) else {}
        if "raw_text" not in meta:
            continue
        pid = str(row["probe_id"])
        if pid not in options:
            prepared = apply_persona(probes[pid], PERSONAS[str(row["persona"])])
            options[pid] = render_prompt(prepared)[1]
        df.at[idx, "value"] = parse_option(meta["raw_text"], options[pid])
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
        out[(str(pid), str(persona), "jev")] = {k: v / total for k, v in dist.items()}

    base = ok[ok["arm"] == "baseline"]
    for (pid, persona), grp in base.groupby(["probe_id", "persona"]):
        vals = [v for v in grp["value"].tolist() if v is not None and v == v]
        if not vals:
            continue
        counts: dict[str, float] = defaultdict(float)
        for v in vals:
            counts[str(v)] += 1.0
        n = float(len(vals))
        out[(str(pid), str(persona), "baseline")] = {k: c / n for k, c in counts.items()}
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
            # Frederick's (2005) benchmark is for his three items only; the other
            # three come from Toplak et al. (2014) and are reported apart, so the
            # human comparison is like for like.
            crt = [p for p in meta if p.startswith("crt_")]
            corr, lure, corr3 = [], [], []
            for pid in crt:
                d = g(pid)
                if not d:
                    continue
                c = prob_of(d, str(meta[pid].get("correct")))
                corr.append(c)
                lure.append(prob_of(d, str(meta[pid].get("lure"))))
                if pid in FREDERICK_CRT:
                    corr3.append(c)
            if corr3:
                add(
                    "crt",
                    "proportion_correct",
                    persona,
                    arm,
                    float(np.mean(corr3)),
                    ci=bootstrap_ci(corr3),
                    bench="crt_proportion_correct",
                    note="Frederick's three items (bat and ball, widgets, lily pads)",
                )
            if corr:
                add(
                    "crt",
                    "proportion_correct_all6",
                    persona,
                    arm,
                    float(np.mean(corr)),
                    ci=bootstrap_ci(corr),
                    note="all six items; no single human benchmark covers these",
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
                # Only the $1 offer (10% of the pie) is compared with Camerer's
                # low-offer figure; $0 leaves nothing to reject in favour of.
                if offer == 1:
                    low_rej.append(rej)
            if low_rej:
                add(
                    "ultimatum_responder",
                    "prob_reject_low_offer",
                    persona,
                    arm,
                    float(np.mean(low_rej)),
                    bench="ultimatum_rejection_low_offer",
                    note="offer of $1 out of $10",
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
                    note=(
                        "product of the two marginal probabilities (A in pair 1, D in "
                        "pair 2); the items are asked separately, so this assumes the two "
                        "choices are independent"
                    ),
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
                        note=(
                            "human gap is about 20 points (Tversky & Kahneman 1974); "
                            "compare the gap, not the levels"
                        ),
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
                    note=(
                        "positive means more patient when both options are delayed; "
                        "no human level is compared, only the direction"
                    ),
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
                    note="the model's mean request against the human mode",
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

            # --- follow-up: moral typecasting (Gray & Wegner) -------
            for suffix, bench_suffix in (
                ("", "moral_typecasting"),
                ("_estimate", "moral_typecasting"),
            ):
                inst = f"moral_typecasting{suffix}"
                man = g(f"moral_typecasting_man_commits{suffix}")
                baby = g(f"moral_typecasting_baby_commits{suffix}")
                man_lvl = expected_level(man, 7) if man else None
                baby_lvl = expected_level(baby, 7) if baby else None
                if man_lvl is not None:
                    add(
                        inst,
                        "responsibility_man",
                        persona,
                        arm,
                        man_lvl,
                        bench=f"{bench_suffix}_responsibility_man",
                    )
                if baby_lvl is not None:
                    add(
                        inst,
                        "responsibility_baby",
                        persona,
                        arm,
                        baby_lvl,
                        bench=f"{bench_suffix}_responsibility_baby",
                    )
                if man_lvl is not None and baby_lvl is not None:
                    add(
                        inst,
                        "agency_responsibility_gap",
                        persona,
                        arm,
                        man_lvl - baby_lvl,
                        note="the higher-agency actor (man) is rated more responsible; "
                        "original gap is 5.29 - 3.86 = 1.43",
                    )

            # --- follow-up: position and power (Giessner & Schubert) -
            for suffix, bench_suffix in (("", "position_power"), ("_estimate", "position_power")):
                inst = f"position_power{suffix}"
                long_l = g(f"position_power_long_line{suffix}")
                short_l = g(f"position_power_short_line{suffix}")
                long_lvl = expected_level(long_l, 7) if long_l else None
                short_lvl = expected_level(short_l, 7) if short_l else None
                if long_lvl is not None:
                    add(
                        inst,
                        "power_long_line",
                        persona,
                        arm,
                        long_lvl,
                        bench=f"{bench_suffix}_long_line",
                    )
                if short_lvl is not None:
                    add(
                        inst,
                        "power_short_line",
                        persona,
                        arm,
                        short_lvl,
                        bench=f"{bench_suffix}_short_line",
                    )
                if long_lvl is not None and short_lvl is not None:
                    add(
                        inst,
                        "position_power_gap",
                        persona,
                        arm,
                        long_lvl - short_lvl,
                        note="a longer vertical line reads as more powerful; "
                        "original gap is 5.01 - 4.62 = 0.39",
                    )

            # --- follow-up: choosing vs rejecting (Shafir) -----------
            award = g("shafir_award")
            deny = g("shafir_deny")
            award_p = prob_of(award, "parent_b") if award else None
            deny_p = prob_of(deny, "parent_b") if deny else None
            if award_p is not None:
                add(
                    "choosing_rejecting",
                    "prob_award_extreme",
                    persona,
                    arm,
                    award_p,
                    bench="shafir_award_extreme",
                )
            if deny_p is not None:
                add(
                    "choosing_rejecting",
                    "prob_deny_extreme",
                    persona,
                    arm,
                    deny_p,
                    bench="shafir_deny_extreme",
                )
            if award_p is not None and deny_p is not None:
                add(
                    "choosing_rejecting",
                    "choose_reject_sum",
                    persona,
                    arm,
                    award_p + deny_p,
                    note="Shafir's diagnostic: the extreme parent is both chosen and rejected "
                    "more than the average parent, so this sums to more than 1.0; "
                    "original sum is 0.64 + 0.55 = 1.19",
                )
            award_est = g("shafir_award_estimate")
            deny_est = g("shafir_deny_estimate")
            if award_est:
                add(
                    "choosing_rejecting_estimate",
                    "prob_award_extreme",
                    persona,
                    arm,
                    prob_of(award_est, "true"),
                    bench="shafir_award_extreme",
                )
            if deny_est:
                add(
                    "choosing_rejecting_estimate",
                    "prob_deny_extreme",
                    persona,
                    arm,
                    prob_of(deny_est, "true"),
                    bench="shafir_deny_extreme",
                )

            # --- follow-up: categorization (Norenzayan et al.) -------
            cat = g("norenzayan_belongs_to")
            if cat:
                add(
                    "categorization",
                    "prob_rule_based",
                    persona,
                    arm,
                    prob_of(cat, "group_1"),
                    bench="norenzayan_rule_based",
                )
            cat_est = g("norenzayan_belongs_to_estimate")
            if cat_est:
                add(
                    "categorization_estimate",
                    "prob_rule_based",
                    persona,
                    arm,
                    prob_of(cat_est, "true"),
                    bench="norenzayan_rule_based",
                )

            # --- follow-up: incidental anchors (Critcher & Gilovich) -
            anchor_bands = {
                "0-35%": 17.5,
                "35-45%": 40.0,
                "45-55%": 50.0,
                "55-65%": 60.0,
                "65-80%": 72.5,
                "80-100%": 90.0,
            }
            for suffix, bench_suffix in (
                ("", "incidental_anchor"),
                ("_estimate", "incidental_anchor"),
            ):
                inst = f"incidental_anchors{suffix}"
                p97 = g(f"incidental_anchor_p97{suffix}")
                p17 = g(f"incidental_anchor_p17{suffix}")
                p97_v = expected_numeric(p97, anchor_bands.get) if p97 else None
                p17_v = expected_numeric(p17, anchor_bands.get) if p17 else None
                if p97_v is not None:
                    add(inst, "estimate_p97", persona, arm, p97_v, bench=f"{bench_suffix}_p97")
                if p17_v is not None:
                    add(inst, "estimate_p17", persona, arm, p17_v, bench=f"{bench_suffix}_p17")
                if p97_v is not None and p17_v is not None:
                    add(
                        inst,
                        "anchor_gap",
                        persona,
                        arm,
                        p97_v - p17_v,
                        note="H3 (currency): original gap is 58.1 - 51.9 = 6.2 points; ML2's "
                        "own replication of this effect found d=0.04, essentially zero — "
                        "does a simulated or estimated gap track the original number or "
                        "the near-zero one ML2 actually found?",
                    )

            # --- follow-up: intentional side effects (Knobe) ---------
            harm = g("knobe_harm")
            helped = g("knobe_help")
            harm_p = prob_of(harm, "intentional") if harm else None
            help_p = prob_of(helped, "intentional") if helped else None
            if harm_p is not None:
                add(
                    "knobe",
                    "prob_harm_intentional",
                    persona,
                    arm,
                    harm_p,
                    bench="knobe_harm_intentional",
                )
            if help_p is not None:
                add(
                    "knobe",
                    "prob_help_intentional",
                    persona,
                    arm,
                    help_p,
                    bench="knobe_help_intentional",
                )
            if harm_p is not None and help_p is not None:
                add(
                    "knobe",
                    "harm_help_asymmetry",
                    persona,
                    arm,
                    harm_p - help_p,
                    note="a harmful side effect is judged far more intentional than an "
                    "equally unintended helpful one (the Knobe effect); original gap is "
                    "0.82 - 0.23 = 0.59",
                )
            harm_est = g("knobe_harm_estimate")
            help_est = g("knobe_help_estimate")
            if harm_est:
                add(
                    "knobe_estimate",
                    "prob_harm_intentional",
                    persona,
                    arm,
                    prob_of(harm_est, "true"),
                    bench="knobe_harm_intentional",
                )
            if help_est:
                add(
                    "knobe_estimate",
                    "prob_help_intentional",
                    persona,
                    arm,
                    prob_of(help_est, "true"),
                    bench="knobe_help_intentional",
                )

            # --- follow-up: trolley switch vs. push (Hauser et al.) --
            switch = g("trolley_switch")
            push = g("trolley_push")
            switch_p = prob_of(switch, "permissible") if switch else None
            push_p = prob_of(push, "permissible") if push else None
            if switch_p is not None:
                add(
                    "trolley",
                    "prob_switch_permissible",
                    persona,
                    arm,
                    switch_p,
                    bench="trolley_switch_permissible",
                )
            if push_p is not None:
                add(
                    "trolley",
                    "prob_push_permissible",
                    persona,
                    arm,
                    push_p,
                    bench="trolley_push_permissible",
                )
            if switch_p is not None and push_p is not None:
                add(
                    "trolley",
                    "switch_push_asymmetry",
                    persona,
                    arm,
                    switch_p - push_p,
                    note="diverting the trolley by switch is judged far more permissible "
                    "than pushing a person to achieve the same outcome; original gap is "
                    "0.89 - 0.11 = 0.78",
                )
            switch_est = g("trolley_switch_estimate")
            push_est = g("trolley_push_estimate")
            if switch_est:
                add(
                    "trolley_estimate",
                    "prob_switch_permissible",
                    persona,
                    arm,
                    prob_of(switch_est, "true"),
                    bench="trolley_switch_permissible",
                )
            if push_est:
                add(
                    "trolley_estimate",
                    "prob_push_permissible",
                    persona,
                    arm,
                    prob_of(push_est, "true"),
                    bench="trolley_push_permissible",
                )

            # --- follow-up: false consensus (Ross, Greene & House) ---
            for suffix, bench_suffix in (("", "false_consensus"), ("_estimate", "false_consensus")):
                inst = f"false_consensus{suffix}"
                wearer = g(f"false_consensus_wearer{suffix}")
                nonwearer = g(f"false_consensus_nonwearer{suffix}")
                wearer_p = prob_of(wearer, "true") if wearer else None
                nonwearer_p = prob_of(nonwearer, "true") if nonwearer else None
                if wearer_p is not None:
                    add(
                        inst,
                        "wearer_predicts_wear",
                        persona,
                        arm,
                        wearer_p,
                        bench=f"{bench_suffix}_wearer_predicts_wear",
                    )
                if nonwearer_p is not None:
                    add(
                        inst,
                        "nonwearer_predicts_wear",
                        persona,
                        arm,
                        nonwearer_p,
                        bench=f"{bench_suffix}_nonwearer_predicts_wear",
                    )
                if wearer_p is not None and nonwearer_p is not None:
                    add(
                        inst,
                        "false_consensus_gap",
                        persona,
                        arm,
                        wearer_p - nonwearer_p,
                        note="each group predicts more of its own choice than the other "
                        "group does; original gap is 0.614 - 0.304 = 0.31",
                    )

            # --- follow-up: estimates for the reused items -----------
            # Each is P(true) for "what proportion chose this option?", named
            # after the statistic its item reports so H4 can pair the two.
            crt_est = [
                prob_of(d, "true") for pid in sorted(FREDERICK_CRT) if (d := g(f"{pid}_estimate"))
            ]
            if crt_est:
                add(
                    "crt_estimate",
                    "proportion_correct",
                    persona,
                    arm,
                    float(np.mean(crt_est)),
                    bench="crt_proportion_correct",
                    note="Frederick's three items (bat and ball, widgets, lily pads)",
                )
            for pid, inst, stat, bench in (
                ("framing_gain", "framing", "prob_certain_gain_frame", "framing_gain_certain"),
                ("framing_loss", "framing", "prob_certain_loss_frame", "framing_loss_certain"),
                ("allais_problem1", "allais", "prob_certain_pair1", "allais_p1_certain"),
                ("allais_problem2", "allais", "prob_safer_pair2", "allais_p2_certain"),
                (
                    "conjunction_forced_choice",
                    "conjunction",
                    "prob_fallacy_forced_choice",
                    "conjunction_fallacy_rate",
                ),
                ("base_rate_mammogram", "base_rate", "prob_correct_band", "base_rate_correct_band"),
                ("sunk_cost", "sunk_cost", "prob_continue", "sunk_cost_continue"),
            ):
                d = g(f"{pid}_estimate")
                if d:
                    add(f"{inst}_estimate", stat, persona, arm, prob_of(d, "true"), bench=bench)

    return stats


def order_effects(df: pd.DataFrame) -> pd.DataFrame:
    """H6: how much does permuting option order move the distribution?

    Only Choice items have their options shuffled (`permute_options` leaves
    Score and Noul items alone), so only those cells measure an order effect;
    `shuffled` marks them. The unshuffled cells are kept because they measure
    something else worth having: how much the distribution moves between
    replicates when nothing changes at all, the floor any order effect sits on.
    An earlier version averaged both together, which understated H6.

    `followup` marks the follow-up study's items, which H6 was not written
    for; its preregistered figure is the core battery alone.
    """
    from .instruments import MODULES

    followup_ids = {p.probe_id for p in MODULES["followup"].probes()}
    rows = []
    jev = df[(df["arm"] == "jev") & (df["error"].isna())] if "error" in df.columns else df
    for (pid, persona), grp in jev.groupby(["probe_id", "persona"]):
        ds = [p for p in grp["probabilities"].tolist() if p]
        if len(ds) < 2:
            continue
        pair_tv = [tv_distance(ds[i], ds[j]) for i in range(len(ds)) for j in range(i + 1, len(ds))]
        orders = grp["option_order"] if "option_order" in grp.columns else pd.Series(dtype=object)
        shuffled = bool(orders.notna().any() and any(o for o in orders if isinstance(o, list)))
        rows.append(
            {
                "probe_id": pid,
                "persona": persona,
                "shuffled": shuffled,
                "followup": pid in followup_ids,
                "n_replicates": len(ds),
                "mean_tv_distance": float(np.mean(pair_tv)),
                "max_tv_distance": float(np.max(pair_tv)),
            }
        )
    return pd.DataFrame(rows)


# Follow-up H4 (FOLLOWUP_PREREGISTRATION.md, section 5): each statistic is
# measured twice, from the item itself and from its `_estimate` twin, so the
# two elicitations can be compared item by item. The last field is the scale's
# range, used to put proportions, 1-7 ratings and percentage bands on one footing.
FOLLOWUP_H4_PAIRS: list[tuple[str, str, float]] = [
    ("categorization", "prob_rule_based", 1.0),
    ("choosing_rejecting", "prob_award_extreme", 1.0),
    ("choosing_rejecting", "prob_deny_extreme", 1.0),
    ("false_consensus", "nonwearer_predicts_wear", 1.0),
    ("false_consensus", "wearer_predicts_wear", 1.0),
    ("incidental_anchors", "estimate_p17", 100.0),
    ("incidental_anchors", "estimate_p97", 100.0),
    ("knobe", "prob_harm_intentional", 1.0),
    ("knobe", "prob_help_intentional", 1.0),
    ("moral_typecasting", "responsibility_baby", 6.0),
    ("moral_typecasting", "responsibility_man", 6.0),
    ("position_power", "power_long_line", 6.0),
    ("position_power", "power_short_line", 6.0),
    ("trolley", "prob_push_permissible", 1.0),
    ("trolley", "prob_switch_permissible", 1.0),
    # The six items reused from the first project (section 4.1).
    ("allais", "prob_certain_pair1", 1.0),
    ("allais", "prob_safer_pair2", 1.0),
    ("base_rate", "prob_correct_band", 1.0),
    ("conjunction", "prob_fallacy_forced_choice", 1.0),
    ("crt", "proportion_correct", 1.0),
    ("framing", "prob_certain_gain_frame", 1.0),
    ("framing", "prob_certain_loss_frame", 1.0),
    ("sunk_cost", "prob_continue", 1.0),
]


def simulate_vs_estimate(
    sdf: pd.DataFrame,
    simulate: str = "typical_human",
    estimate: str = "neutral",
    arm: str = "jev",
) -> pd.DataFrame:
    """Follow-up H4: is estimating the population more accurate than simulating a participant?

    As preregistered, "simulate" is the item asked with the typical-person
    prompt and "estimate" is its population question ("what proportion of
    participants...") with no persona. As preregistered, errors are absolute
    distances from the item's benchmark, in the item's own units. The
    ``scaled_error_*`` columns divide them by the scale's range so that the
    three scales weigh alike; that is a post-hoc check, not the registered
    test. The benchmarks are the original studies' published values, as Many
    Labs 2's protocol quotes them; Many Labs 2 reports only replicated effect
    sizes, not the per-condition values this needs (see benchmarks.py). Rows
    with either value missing (a refusal) are dropped.
    """
    rows: list[dict[str, Any]] = []
    if not len(sdf) or "instrument" not in sdf.columns:
        return pd.DataFrame(rows)
    sel = sdf[sdf["arm"] == arm] if "arm" in sdf.columns else sdf

    def value(inst: str, stat: str, persona: str) -> float:
        r = sel[(sel.instrument == inst) & (sel.statistic == stat) & (sel.persona == persona)]
        v = r["value"].iloc[0] if len(r) else None
        return float(v) if v is not None and pd.notna(v) else float("nan")

    for inst, stat, scale in FOLLOWUP_H4_PAIRS:
        keys = sel[(sel.instrument == inst) & (sel.statistic == stat)]["benchmark_key"].dropna()
        if not len(keys) or keys.iloc[0] not in BENCHMARKS:
            continue
        human = BENCHMARKS[keys.iloc[0]].value
        sim = value(inst, stat, simulate)
        est = value(f"{inst}_estimate", stat, estimate)
        if np.isnan(sim) or np.isnan(est):
            continue
        rows.append(
            {
                "instrument": inst,
                "statistic": stat,
                "human": human,
                "simulate": sim,
                "estimate": est,
                "error_simulate": abs(sim - human),
                "error_estimate": abs(est - human),
                "scaled_error_simulate": abs(sim - human) / scale,
                "scaled_error_estimate": abs(est - human) / scale,
            }
        )
    return pd.DataFrame(rows)


def h4_summary(table: pd.DataFrame) -> dict[str, float | int | None]:
    """Counts, mean errors and the preregistered one-sided Wilcoxon signed-rank test.

    The registered test is on the raw absolute errors; ``wilcoxon_p_scaled``
    repeats it on the range-scaled errors as a post-hoc check.
    """
    if len(table) < 2:
        return {"n": len(table)}
    from scipy.stats import wilcoxon

    def one_sided(diff: pd.Series) -> float | None:
        return float(wilcoxon(diff, alternative="less").pvalue) if (diff != 0).any() else None

    diff = table["error_estimate"] - table["error_simulate"]
    scaled = table["scaled_error_estimate"] - table["scaled_error_simulate"]
    return {
        "n": len(table),
        "estimate_closer": int((diff < 0).sum()),
        "mean_error_simulate": float(table["error_simulate"].mean()),
        "mean_error_estimate": float(table["error_estimate"].mean()),
        "wilcoxon_p_one_sided": one_sided(diff),
        "mean_scaled_error_simulate": float(table["scaled_error_simulate"].mean()),
        "mean_scaled_error_estimate": float(table["scaled_error_estimate"].mean()),
        "wilcoxon_p_scaled": one_sided(scaled),
    }


def core_order_cells(odf: pd.DataFrame) -> pd.DataFrame:
    """The order-effect cells H6 is about: the core battery, without the follow-up items."""
    return odf[~odf["followup"].astype(bool)] if "followup" in odf.columns else odf


def _order_split(odf: pd.DataFrame) -> dict[str, float | None]:
    """Mean order effect and noise floor for the core battery and the follow-up items."""
    out: dict[str, float | None] = {}
    for part, sel in (("core", False), ("followup", True)):
        for name, shuffled in (("order_tv", True), ("unshuffled_tv", False)):
            cells = (
                odf[(odf["followup"] == sel) & (odf["shuffled"] == shuffled)] if len(odf) else odf
            )
            out[f"mean_{name}_{part}"] = (
                float(cells["mean_tv_distance"].mean()) if len(cells) else None
            )
    return out


def analyse_run(path: Path, out_dir: Path) -> dict[str, Any]:
    df = load_records(path)
    out_dir.mkdir(parents=True, exist_ok=True)

    stats = compute_stats(df)
    sdf = pd.DataFrame([asdict(s) for s in stats])
    sdf.to_csv(out_dir / "statistics.csv", index=False)

    odf = order_effects(df)
    odf.to_csv(out_dir / "order_effects.csv", index=False)

    h4 = simulate_vs_estimate(sdf)
    h4_path = out_dir / "followup_h4.csv"
    if len(h4):
        h4.to_csv(h4_path, index=False)
    else:
        # No follow-up data in this run: never leave another run's table behind.
        h4_path.unlink(missing_ok=True)

    n_err = int(df["error"].notna().sum()) if "error" in df.columns else 0
    cost = float(sum(float((u or {}).get("cost") or 0.0) for u in df["usage"]))

    # A reply that arrives but cannot be resolved to an option is a silent hole:
    # it is not a transport error, so counting only errors hides it entirely. An
    # earlier run lost 4.8% of the baseline arm that way, concentrated on the
    # items the model reasoned longest about — a systematic gap, not noise.
    # Proportion items asked of a chat model are left unscored on purpose (see
    # `_reread_chat_replies`); they are counted apart, not as parse failures.
    base = df[df["arm"] == "baseline"]
    not_measurable = int(base["not_measurable"].sum()) if "not_measurable" in base else 0
    if "not_measurable" in base:
        base = base[~base["not_measurable"].astype(bool)]
    unparsed = int((base["error"].isna() & base["value"].isna()).sum()) if len(base) else 0
    coverage: dict[str, int] = {}
    if len(base):
        cells = base.groupby(["probe_id", "persona"]).size()
        good = base[base["value"].notna()].groupby(["probe_id", "persona"]).size()
        good = good.reindex(cells.index, fill_value=0)
        coverage = {
            "baseline_cells": len(cells),
            "baseline_cells_below_full_samples": int((good < cells).sum()),
            "baseline_cells_with_no_usable_sample": int((good == 0).sum()),
            "baseline_min_usable_samples": int(good.min()),
        }

    summary = {
        "run_file": path.name,
        "backend": sorted(df["backend"].unique()),
        "models": sorted(df["model"].unique()),
        "n_records": len(df),
        "n_errors": n_err,
        "n_baseline_unparsed": unparsed,
        "baseline_unparsed_rate": round(unparsed / len(base), 4) if len(base) else 0.0,
        "n_baseline_not_measurable": not_measurable,
        **coverage,
        "total_cost_usd": round(cost, 4),
        "personas": sorted(df["persona"].unique()),
        "arms": sorted(df["arm"].unique()),
        "n_statistics": len(sdf),
        "mean_order_tv": float(odf[odf["shuffled"]]["mean_tv_distance"].mean())
        if len(odf)
        else None,
        "mean_unshuffled_tv": float(odf[~odf["shuffled"]]["mean_tv_distance"].mean())
        if len(odf) and (~odf["shuffled"]).any()
        else None,
        # H6 as preregistered: the core battery, without the follow-up items.
        **_order_split(odf),
        "followup_h4": h4_summary(h4) if len(h4) else None,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))

    print(json.dumps(summary, indent=2))
    print(f"\nwrote {out_dir / 'statistics.csv'} ({len(sdf)} rows)")
    print(f"wrote {out_dir / 'order_effects.csv'} ({len(odf)} rows)")
    return summary


# -- how closely does a condition reproduce the human values? -----------


@dataclass(slots=True)
class Fidelity:
    """How well one condition's answers track the published human values.

    `mae` is the average absolute distance from the human value, `bias` the
    signed average (positive means the model's values sit above people's on
    average, which is not the same as being more extreme), and
    `r` / `rho` say whether it gets the *ordering* right — whether it knows
    which effects are strong, not merely how strong effects are on average. A
    condition can have low error and no correlation, which would mean it lands
    near the human average without knowing anything about individual items.
    """

    arm: str
    persona: str
    n_measures: int
    mae: float
    bias: float
    r: float
    rho: float


def human_fidelity(
    sdf: pd.DataFrame, measures: list[tuple[str, str, str, str]]
) -> tuple[list[Fidelity], dict[tuple[str, str], list[tuple[str, float, float]]]]:
    """Compare each (arm, persona) against the human reference values.

    Only measures on a shared 0-1 probability scale are used, so the error is
    an average of comparable quantities rather than a mix of scales.
    """
    from scipy import stats as _stats

    out: list[Fidelity] = []
    points: dict[tuple[str, str], list[tuple[str, float, float]]] = {}
    for arm in sorted(sdf["arm"].unique()):
        for persona in sorted(sdf["persona"].unique()):
            pairs: list[tuple[str, float, float]] = []
            for inst, stat, bench, label in measures:
                sel = sdf[
                    (sdf.instrument == inst)
                    & (sdf.statistic == stat)
                    & (sdf.persona == persona)
                    & (sdf.arm == arm)
                ]
                b = BENCHMARKS.get(bench)
                if not len(sel) or b is None:
                    continue
                pairs.append((label, float(b.value), float(sel.value.iloc[0])))
            if len(pairs) < 3:
                continue
            h = np.array([p[1] for p in pairs])
            m = np.array([p[2] for p in pairs])
            points[(arm, persona)] = pairs
            out.append(
                Fidelity(
                    arm=arm,
                    persona=persona,
                    n_measures=len(pairs),
                    mae=float(np.abs(m - h).mean()),
                    bias=float((m - h).mean()),
                    r=float(_stats.pearsonr(h, m)[0]),
                    rho=float(_stats.spearmanr(h, m)[0]),
                )
            )
    return out, points
