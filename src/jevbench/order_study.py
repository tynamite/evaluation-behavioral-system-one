"""The option-order addendum (ORDER_PREREGISTRATION.md).

Five preregistered tests over the core battery's multiple-choice items, with
instruments as the unit:

- O1 (per version): shuffling the options moves Jev's answers more than
  repeating the same request does (R2 spread > R3 spread, one-sided).
- O2: 1.14's order excess (R2 spread minus R3 spread) differs from 1.13's
  (two-sided), with R2 computed on the repeats usable on both versions.
- O3 (per version): a slot-position lean, the within-option slope of
  probability on slot position (two-sided).

The five are Holm-corrected as one family. Everything else here is
descriptive: the route check, the slot profile, the per-persona spreads, the
time matching of the concurrent runs, and 1.14's statistics beside 1.13's.

Runs live in `data/raw/order_study/{r1,r2,r3}/`, one file per model and route,
outside the `run_live_*.jsonl` set the README's analyses read.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass, field
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats as sps

from .analysis import compute_stats, load_records, tv_distance
from .config import RAW_DIR, REPO_ROOT
from .runner import UNUSABLE, model_slug, resume_order_mismatch

ORDER_STUDY_DIR = RAW_DIR / "order_study"
ORDER_RESULTS_DIR = REPO_ROOT / "results" / "order_study"

MIN_REPEATS = 8  # usable repeats a cell needs (section 6)
MIN_CELLS = 3  # qualifying persona cells an item needs (section 6)
ALPHA = 0.05
BOOTSTRAP_DRAWS = 10_000
BOOTSTRAP_SEED = 20261014

# Served model IDs, as each response's `model` field reports them.
DIRECT_MODELS = {"jev-1.13.0": "1.13", "jev-1.14.0": "1.14"}
OPENROUTER_PREFIXES = {"typesafe/jev-1.13-": "1.13", "typesafe/jev-1.14-": "1.14"}

# How each condition presents the options (section 2), checked against every
# record before anything is analysed: (seed, shuffled).
CONDITION_ORDER = {"r1": (20260918, True), "r2": (20261014, True), "r3": (20260918, False)}

Cell = tuple[str, str]  # (probe_id, persona)


@dataclass(frozen=True, slots=True)
class Answer:
    probs: dict[str, float]
    order: tuple[str, ...] | None


@dataclass(slots=True)
class Arm:
    """One run file: a version on a route, under one condition."""

    version: str
    route: str  # "direct" | "openrouter"
    path: Path
    df: pd.DataFrame
    unusable: int = 0
    failed: int = 0

    @property
    def label(self) -> str:
        return f"{self.version} ({self.route})"


# -- Loading -------------------------------------------------------------


def identify(served: Iterable[str]) -> tuple[str, str]:
    """The version and route a run file holds, from the model IDs that answered.

    A file must hold exactly one served model. Any other model in it means
    TypeSafe changed what the ID serves partway through, and the preregistered
    response is to redo the run (section 6), so this refuses rather than guess.
    """
    models = sorted(set(served))
    if len(models) != 1:
        raise ValueError(f"expected one served model per run file, found {models}")
    model = models[0]
    if model in DIRECT_MODELS:
        return DIRECT_MODELS[model], "direct"
    for prefix, version in OPENROUTER_PREFIXES.items():
        if model.startswith(prefix):
            return version, "openrouter"
    raise ValueError(f"unexpected served model {model!r}")


def requested_slug(path: Path) -> str:
    """The requested model, as the runner wrote it into the file name."""
    parts = path.stem.split("_", 3)
    if len(parts) != 4 or parts[0] != "run":
        raise ValueError(f"{path.name} is not a runner-written run file")
    return parts[3]


def load_arm(path: Path) -> Arm:
    df = load_records(path)
    df = df[df["arm"] == "jev"].copy()
    err = df["error"] if "error" in df.columns else pd.Series(None, index=df.index)
    unusable = err.fillna("").astype(str).str.startswith(UNUSABLE)
    failed = err.notna() & ~unusable
    # A failed call's record carries the requested ID, not a served one.
    served = df.loc[~failed, "model"].astype(str)
    version, route = identify(served)
    # The served model must be the one requested: the same versioned ID on
    # the direct route, its dated build on OpenRouter (section 6).
    want, got = requested_slug(path), model_slug(served.iloc[0])
    if not (got == want or (route == "openrouter" and got.startswith(want + "-"))):
        raise ValueError(f"{path.name}: requested {want} but {served.iloc[0]} answered")
    return Arm(version, route, path, df, unusable=int(unusable.sum()), failed=int(failed.sum()))


def check_condition(arm: Arm, condition: str) -> None:
    """Refuse a file whose option orders are not its condition's (section 2).

    A run made without `--seed 20261014` (R2) or `--fixed-order` (R3) would
    otherwise be analysed as the preregistered treatment.
    """
    from .instruments import all_probes

    seed, shuffled = CONDITION_ORDER[condition]
    rows: list[dict[str, Any]] = [
        {
            "probe_id": str(r.probe_id),
            "persona": str(r.persona),
            "replicate": r.replicate,
            "option_order": r.option_order if isinstance(r.option_order, list) else None,
        }
        for r in arm.df.itertuples(index=False)
    ]
    problem = resume_order_mismatch(rows, all_probes(), seed=seed, randomise_options=shuffled)
    if problem:
        raise ValueError(f"{arm.path.name} does not match {condition}'s option order: {problem}")


def core_choice_items() -> dict[str, str]:
    """probe_id -> instrument for the core battery's multiple-choice items."""
    from .instruments import MODULES
    from .schema import Choice

    return {
        p.probe_id: p.instrument
        for name, mod in MODULES.items()
        if name != "followup"
        for p in mod.probes()
        if isinstance(p.question, Choice)
    }


def usable_answers(df: pd.DataFrame) -> dict[Cell, dict[int, Answer]]:
    """Each cell's usable answers, by repeat ID."""
    out: dict[Cell, dict[int, Answer]] = {}
    ok = df[df["error"].isna()] if "error" in df.columns else df
    for row in ok.itertuples(index=False):
        probs = row.probabilities
        if not isinstance(probs, dict) or not probs:
            continue
        order = row.option_order if isinstance(row.option_order, list) else None
        cell = (str(row.probe_id), str(row.persona))
        out.setdefault(cell, {})[int(row.replicate)] = Answer(
            {str(k): float(v) for k, v in probs.items()}, tuple(order) if order else None
        )
    return out


# -- Measures (section 3) -------------------------------------------------


def spread(dists: list[dict[str, float]]) -> float:
    """Mean TV distance over all pairs of a cell's answers."""
    return float(np.mean([tv_distance(a, b) for a, b in combinations(dists, 2)]))


def cell_spreads(
    answers: dict[Cell, dict[int, Answer]],
    items: dict[str, str] | None,
    repeats: dict[Cell, set[int]] | None = None,
) -> dict[Cell, float]:
    """Spread of every qualifying cell, optionally on a given set of repeats per cell.

    `items` limits it to those items; None takes every item in the run.
    """
    out: dict[Cell, float] = {}
    for cell, by_rep in answers.items():
        if items is not None and cell[0] not in items:
            continue
        reps = set(by_rep) if repeats is None else repeats.get(cell, set()) & set(by_rep)
        if len(reps) >= MIN_REPEATS:
            out[cell] = spread([by_rep[r].probs for r in sorted(reps)])
    return out


def slot_slope(answers: list[Answer]) -> float | None:
    """Change in an option's probability from first slot to last, its own pull removed.

    Each option's probability and its slot position (0 first, 1 last) are
    centred on that option's own means over the repeats; the slope is the
    pooled least-squares fit of one on the other. None when no option's slot
    varies, since the slope is then undefined (section 6).
    """
    xs: list[float] = []
    ys: list[float] = []
    options = sorted({o for a in answers if a.order for o in a.order})
    for opt in options:
        x, y = [], []
        for a in answers:
            if not a.order or opt not in a.order or len(a.order) < 2:
                continue
            x.append(a.order.index(opt) / (len(a.order) - 1))
            y.append(a.probs.get(opt, 0.0))
        if len(x) < 2:
            continue
        xa, ya = np.asarray(x), np.asarray(y)
        xs.extend(xa - xa.mean())
        ys.extend(ya - ya.mean())
    xv, yv = np.asarray(xs), np.asarray(ys)
    denom = float((xv**2).sum())
    if denom <= 1e-12:
        return None
    return float((xv * yv).sum() / denom)


def cell_slopes(answers: dict[Cell, dict[int, Answer]], items: dict[str, str]) -> dict[Cell, float]:
    out: dict[Cell, float] = {}
    for cell, by_rep in answers.items():
        if cell[0] not in items or len(by_rep) < MIN_REPEATS:
            continue
        slope = slot_slope(list(by_rep.values()))
        if slope is not None:
            out[cell] = slope
    return out


@dataclass(slots=True)
class Units:
    """Paired values per item and per instrument, one array per side."""

    items: list[str] = field(default_factory=list)
    item_values: list[list[float]] = field(default_factory=list)
    instruments: list[str] = field(default_factory=list)
    instrument_values: list[list[float]] = field(default_factory=list)
    dropped_items: list[str] = field(default_factory=list)


def paired_units(sides: list[dict[Cell, float]], items: dict[str, str]) -> Units:
    """Average cells up to items and items up to instruments, on common cells only.

    For each item, only the persona cells that qualify on every side are used,
    and the item enters only if at least MIN_CELLS of them remain (section 6).
    """
    by_item: dict[str, list[str]] = {}
    for side in sides:
        for pid, persona in side:
            by_item.setdefault(pid, [])
            if persona not in by_item[pid]:
                by_item[pid].append(persona)
    units = Units()
    inst_acc: dict[str, list[list[float]]] = {}
    for pid in sorted(items):
        common = [p for p in by_item.get(pid, []) if all((pid, p) in s for s in sides)]
        if len(common) < MIN_CELLS:
            units.dropped_items.append(pid)
            continue
        vals = [float(np.mean([s[(pid, p)] for p in common])) for s in sides]
        units.items.append(pid)
        units.item_values.append(vals)
        inst_acc.setdefault(items[pid], []).append(vals)
    for inst in sorted(inst_acc):
        units.instruments.append(inst)
        units.instrument_values.append(list(np.mean(np.asarray(inst_acc[inst]), axis=0)))
    return units


# -- Inference (section 4) -----------------------------------------------


def wilcoxon(x: np.ndarray, alternative: str) -> tuple[float, int]:
    """Wilcoxon signed-rank p-value and the number of non-zero values it used."""
    x = np.asarray(x, dtype=float)
    nz = int(np.count_nonzero(np.abs(x) > 1e-12))
    if nz == 0:
        return 1.0, 0
    res = sps.wilcoxon(x, alternative=alternative, zero_method="wilcox")
    return float(res.pvalue), nz


def bootstrap_median_ci(x: np.ndarray) -> tuple[float, float]:
    """Percentile 95% interval for the median, resampling the units."""
    x = np.asarray(x, dtype=float)
    if x.size == 0:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    draws = np.median(rng.choice(x, size=(BOOTSTRAP_DRAWS, x.size), replace=True), axis=1)
    lo, hi = np.percentile(draws, [2.5, 97.5])
    return (float(lo), float(hi))


def holm(pvalues: dict[str, float]) -> dict[str, float]:
    """Holm-adjusted p-values (step-down, monotone, capped at 1)."""
    ordered = sorted(pvalues.items(), key=lambda kv: kv[1])
    m = len(ordered)
    out: dict[str, float] = {}
    running = 0.0
    for i, (name, p) in enumerate(ordered):
        running = max(running, min(1.0, (m - i) * p))
        out[name] = running
    return out


def _test(
    name: str, diffs: np.ndarray, alternative: str, unit: str, n_items: int
) -> dict[str, Any]:
    p, nz = wilcoxon(diffs, alternative)
    lo, hi = bootstrap_median_ci(diffs)
    return {
        "test": name,
        "unit": unit,
        "n_units": len(diffs),
        "n_nonzero": nz,
        "n_items": n_items,
        "alternative": alternative,
        "median": float(np.median(diffs)) if len(diffs) else float("nan"),
        "mean": float(np.mean(diffs)) if len(diffs) else float("nan"),
        "ci_low": lo,
        "ci_high": hi,
        "p": p,
    }


@dataclass(slots=True)
class Conditions:
    """The four concurrent runs behind the tests: R2 and R3 for each version."""

    r2: dict[str, Arm]
    r3: dict[str, Arm]


def run_tests(cond: Conditions, items: dict[str, str]) -> tuple[pd.DataFrame, dict[str, Any]]:
    """The five preregistered tests, at instrument level, plus the item-level sensitivity check.

    Holm's correction is for the family of five, so all four runs must be
    present; a partial set is refused rather than corrected over fewer tests.
    """
    for name, runs in (("r2", cond.r2), ("r3", cond.r3)):
        if set(runs) != {"1.13", "1.14"}:
            raise ValueError(f"{name} needs a direct run of 1.13 and of 1.14, found {sorted(runs)}")
    rows: list[dict[str, Any]] = []
    dropped: dict[str, list[str]] = {}
    ans2 = {v: usable_answers(a.df) for v, a in cond.r2.items()}
    ans3 = {v: usable_answers(a.df) for v, a in cond.r3.items()}

    def add(
        name: str, units: Units, diff_of: Callable[[list[float]], float], alternative: str
    ) -> None:
        dropped[name] = units.dropped_items
        for unit, vals in (
            ("instrument", units.instrument_values),
            ("item", units.item_values),
        ):
            diffs = np.asarray([diff_of(v) for v in vals], dtype=float)
            rows.append(_test(name, diffs, alternative, unit, len(units.items)))

    for v in sorted(cond.r2):
        u = paired_units([cell_spreads(ans2[v], items), cell_spreads(ans3[v], items)], items)
        add(f"O1 {v}", u, lambda s: s[0] - s[1], "greater")

    # Permutation is the treatment, so R2 is compared on the repeats usable
    # on both versions (section 6).
    shared = {
        cell: set(ans2["1.13"][cell]) & set(ans2["1.14"].get(cell, {})) for cell in ans2["1.13"]
    }
    sides = [
        cell_spreads(ans2["1.13"], items, shared),
        cell_spreads(ans3["1.13"], items),
        cell_spreads(ans2["1.14"], items, shared),
        cell_spreads(ans3["1.14"], items),
    ]
    u = paired_units(sides, items)
    add("O2", u, lambda s: (s[2] - s[3]) - (s[0] - s[1]), "two-sided")

    for v in sorted(cond.r2):
        u = paired_units([cell_slopes(ans2[v], items)], items)
        add(f"O3 {v}", u, lambda s: s[0], "two-sided")

    table = pd.DataFrame(rows)
    primary = table["unit"] == "instrument"
    adj = holm(dict(zip(table.loc[primary, "test"], table.loc[primary, "p"], strict=True)))
    table["p_holm"] = [
        adj.get(t) if u == "instrument" else np.nan
        for t, u in zip(table["test"], table["unit"], strict=True)
    ]
    table["significant"] = [
        bool(ph < ALPHA) if u == "instrument" else None
        for ph, u in zip(table["p_holm"], table["unit"], strict=True)
    ]
    return table, {"dropped_items": dropped}


# -- Descriptive (section 5) ---------------------------------------------


def route_check(direct: Arm, other: Arm, r3_spreads: dict[Cell, float]) -> dict[str, Any]:
    """Per-repeat distance between the two routes' answers to the identical request.

    Compared with R3's cell spread, which is also a distance between single
    answers to identical requests.
    """
    a, b = usable_answers(direct.df), usable_answers(other.df)
    per_cell: dict[Cell, float] = {}
    for cell, reps in a.items():
        shared = sorted(set(reps) & set(b.get(cell, {})))
        if len(shared) >= MIN_REPEATS:
            per_cell[cell] = float(
                np.mean([tv_distance(reps[r].probs, b[cell][r].probs) for r in shared])
            )
    common = [c for c in per_cell if c in r3_spreads]
    route_vals = np.asarray(list(per_cell.values()), dtype=float)
    return {
        "compared": [direct.path.name, other.path.name],
        "n_cells": len(per_cell),
        "mean_route_tv": float(route_vals.mean()) if route_vals.size else None,
        "median_route_tv": float(np.median(route_vals)) if route_vals.size else None,
        "n_cells_with_r3": len(common),
        "mean_route_tv_on_r3_cells": (
            float(np.mean([per_cell[c] for c in common])) if common else None
        ),
        "mean_r3_spread_on_same_cells": (
            float(np.mean([r3_spreads[c] for c in common])) if common else None
        ),
        "share_route_above_r3": (
            float(np.mean([per_cell[c] > r3_spreads[c] for c in common])) if common else None
        ),
    }


def slot_profile(answers: dict[Cell, dict[int, Answer]], items: dict[str, str]) -> pd.DataFrame:
    """Mean probability by presented slot, for each number of options."""
    acc: dict[int, list[np.ndarray]] = {}
    for (pid, _), by_rep in answers.items():
        if pid not in items:
            continue
        for a in by_rep.values():
            if not a.order:
                continue
            acc.setdefault(len(a.order), []).append(
                np.asarray([a.probs.get(o, 0.0) for o in a.order])
            )
    rows = []
    for k in sorted(acc):
        mean = np.mean(np.vstack(acc[k]), axis=0)
        for slot, m in enumerate(mean, start=1):
            rows.append({"n_options": k, "slot": slot, "mean_prob": float(m), "n": len(acc[k])})
    return pd.DataFrame(rows)


def persona_spreads(spreads: dict[Cell, float]) -> dict[str, float]:
    by: dict[str, list[float]] = {}
    for (_, persona), v in spreads.items():
        by.setdefault(persona, []).append(v)
    return {p: float(np.mean(v)) for p, v in sorted(by.items())}


def time_matching(arms: list[Arm], items: dict[str, str]) -> dict[str, Any]:
    """How far apart the concurrent runs reached each cell (section 2).

    Uses when the kept answer arrived, not when the call was first sent.
    """
    medians: list[dict[Cell, float]] = []
    lengths: list[float] = []
    epoch = pd.Timestamp("1970-01-01", tz="UTC")
    for arm in arms:
        df = arm.df[arm.df["probe_id"].isin(items)]
        if "answered_at" not in df.columns:
            return {"available": False}
        secs = (
            pd.to_datetime(df["answered_at"], utc=True, errors="coerce") - epoch
        ).dt.total_seconds()
        df = df.assign(secs=secs).dropna(subset=["secs"])
        if df.empty:
            return {"available": False}
        lengths.append(float(df["secs"].max() - df["secs"].min()))
        med: dict[Cell, float] = {}
        for row in (
            df.groupby(["probe_id", "persona"], as_index=False)["secs"].median().itertuples()
        ):
            med[(str(row.probe_id), str(row.persona))] = float(row.secs)
        medians.append(med)
    common = set.intersection(*(set(m) for m in medians))
    gaps = [max(m[c] for m in medians) - min(m[c] for m in medians) for c in common]
    return {
        "available": True,
        "n_cells": len(gaps),
        "median_gap_s": float(np.median(gaps)) if gaps else None,
        "max_gap_s": float(np.max(gaps)) if gaps else None,
        "run_length_s": {
            arm.label + f" {arm.path.parent.name}": s for arm, s in zip(arms, lengths, strict=True)
        },
    }


def version_statistics(r1: dict[str, Arm]) -> pd.DataFrame:
    """The battery's statistics for each version, side by side (descriptive only)."""
    frames = []
    for version, arm in sorted(r1.items()):
        s = pd.DataFrame([asdict(x) for x in compute_stats(arm.df)])
        s = s[s["arm"] == "jev"]
        s = s[["instrument", "statistic", "persona", "value", "human_value"]].rename(
            columns={"value": f"jev_{version}"}
        )
        frames.append(s)
    if not frames:
        return pd.DataFrame()
    out = frames[0]
    for f in frames[1:]:
        out = out.merge(f, on=["instrument", "statistic", "persona", "human_value"], how="outer")
    return out.sort_values(["instrument", "statistic", "persona"]).reset_index(drop=True)


# -- Driver ----------------------------------------------------------------


def load_study(root: Path = ORDER_STUDY_DIR) -> dict[str, list[Arm]]:
    """Every run file under r1/, r2/ and r3/, identified by the model that answered."""
    out: dict[str, list[Arm]] = {}
    for cond in ("r1", "r2", "r3"):
        out[cond] = [load_arm(p) for p in sorted((root / cond).glob("run_live_*.jsonl"))]
        for arm in out[cond]:
            check_condition(arm, cond)
    return out


def _direct(arms: list[Arm]) -> dict[str, Arm]:
    found: dict[str, Arm] = {}
    for a in arms:
        if a.route == "direct":
            if a.version in found:
                raise ValueError(f"two direct {a.version} runs: {found[a.version].path}, {a.path}")
            found[a.version] = a
    return found


def analyse_study(
    root: Path = ORDER_STUDY_DIR,
    out_dir: Path = ORDER_RESULTS_DIR,
    openrouter_fallback: Path | None = None,
) -> dict[str, Any]:
    study = load_study(root)
    items = core_choice_items()
    cond = Conditions(r2=_direct(study["r2"]), r3=_direct(study["r3"]))
    out_dir.mkdir(parents=True, exist_ok=True)

    tests, extra = run_tests(cond, items)
    tests.to_csv(out_dir / "tests.csv", index=False)

    summary: dict[str, Any] = {
        "files": {
            c: [{"file": a.path.name, "version": a.version, "route": a.route} for a in arms]
            for c, arms in study.items()
        },
        "health": {
            f"{c} {a.label}": {"records": len(a.df), "unusable": a.unusable, "failed": a.failed}
            for c, arms in study.items()
            for a in arms
        },
        "n_items": len(items),
        "n_instruments": len(set(items.values())),
        **extra,
    }

    # The route check spans the whole battery, so its reference is every R3
    # cell, not only the multiple-choice ones.
    r3_all = {v: cell_spreads(usable_answers(a.df), None) for v, a in cond.r3.items()}
    r1_direct = _direct(study["r1"])
    openrouter = [a for a in study["r1"] if a.route == "openrouter" and a.version == "1.13"]
    if "1.13" in r1_direct and "1.13" in r3_all:
        if openrouter:
            summary["route_check"] = {
                "kind": "route",
                **route_check(r1_direct["1.13"], openrouter[0], r3_all["1.13"]),
            }
        elif openrouter_fallback is not None:
            summary["route_check"] = {
                "kind": "route and date",
                **route_check(r1_direct["1.13"], load_arm(openrouter_fallback), r3_all["1.13"]),
            }

    profiles = []
    for v, a in cond.r2.items():
        prof = slot_profile(usable_answers(a.df), items)
        prof.insert(0, "version", v)
        profiles.append(prof)
    if profiles:
        pd.concat(profiles).to_csv(out_dir / "slot_profile.csv", index=False)

    summary["persona_spread"] = {
        f"{c} {v}": persona_spreads(cell_spreads(usable_answers(a.df), items))
        for c, arms in (("r2", cond.r2), ("r3", cond.r3))
        for v, a in arms.items()
    }
    summary["time_matching"] = time_matching(
        [cond.r2[v] for v in sorted(cond.r2)] + [cond.r3[v] for v in sorted(cond.r3)], items
    )

    if r1_direct:
        version_statistics(r1_direct).to_csv(out_dir / "version_statistics.csv", index=False)

    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    return {"tests": tests, "summary": summary}
