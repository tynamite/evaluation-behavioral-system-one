"""Put several models side by side, one run file each.

The single-run analysis answers "how does Jev behave?" with one System One
model and one chat baseline. Comparing models reuses it unchanged: every run
file is reduced by `compute_stats` exactly as before, and only then are the
results joined, keyed by the model that actually served each arm.

Within a run file `arm="jev"` means "the System One arm", whichever model that
was; the label used here always comes from the `model` field of the records,
so it names the served version (e.g. `typesafe/jev-1.13-20260917`) rather than
the alias that was requested.

Three tables come out, plus one figure:

  health.csv    errors, unresolved replies and cell coverage per model — read
                this first, because a model that silently rejects one
                primitive (say, every Score item) would otherwise just look
                like a model with fewer measures
  fidelity.csv  mean distance from the human values, and whether the model gets
                their ordering right, per model and persona
  measures.csv  every 0-1 headline measure, one column per model
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd

from .analysis import (
    compute_stats,
    h4_summary,
    human_fidelity,
    load_records,
    simulate_vs_estimate,
)
from .benchmarks import BENCHMARKS

SYSTEM_ONE = "System One"
CHAT = "chat, resampled"


def _arm_label(df: pd.DataFrame, arm: str) -> str:
    """The served model for an arm: its most frequent `model` among good records."""
    sel = df[df["arm"] == arm]
    ok = sel[sel["error"].isna()] if "error" in sel.columns else sel
    models = (ok if len(ok) else sel)["model"].value_counts()
    label = str(models.index[0])
    # TypeSafe's direct API names its models without the provider prefix that
    # OpenRouter adds (jev-1.14.0, not typesafe/jev-1.14.0); add it, so every
    # label says who makes the model whichever route served it.
    if "/" not in label and set(sel["backend"]) == {"typesafe"}:
        label = f"typesafe/{label}"
    return label


def _run_name(path: Path) -> str:
    """A run file's name as health.csv records it: relative to the raw-data
    directory when it is inside it (the Jev 1.14 run lives in order_study/r1/),
    otherwise its full path, so the figures can find it wherever it is."""
    from .config import RAW_DIR

    try:
        return path.resolve().relative_to(RAW_DIR.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _health(df: pd.DataFrame, arm: str, label: str, run_file: str) -> dict[str, Any]:
    sel = df[df["arm"] == arm]
    err = sel["error"].notna() if "error" in sel.columns else pd.Series(False, index=sel.index)
    good = sel[~err & sel["value"].notna()]
    unmeasured = (
        sel["not_measurable"].astype(bool)
        if "not_measurable" in sel.columns
        else pd.Series(False, index=sel.index)
    )
    cells = sel[~unmeasured].groupby(["probe_id", "persona"]).size()
    good_cells = good.groupby(["probe_id", "persona"]).size().reindex(cells.index, fill_value=0)
    # Errors by primitive: a model that does not implement one of Choice, Score
    # or Noul fails on every item of that kind, which shows up here as a kind
    # with an error rate of 1.0 rather than as a quietly shorter results table.
    by_kind = {
        str(kind): round(float(grp["error"].notna().mean()), 4) if "error" in grp else 0.0
        for kind, grp in sel.groupby("kind")
    }
    # A route that reports no cost (TypeSafe's direct API gives tokens only)
    # leaves the cost unknown, not zero.
    reported = [
        u["cost"] for u in sel["usage"] if isinstance(u, dict) and u.get("cost") is not None
    ]
    cost = round(float(sum(reported)), 4) if reported else None
    return {
        "model": label,
        "type": SYSTEM_ONE if arm == "jev" else CHAT,
        "run_file": run_file,
        "n_records": len(sel),
        "n_errors": int(err.sum()),
        "n_refused": int(sel["error"].fillna("").str.startswith("refused").sum())
        if "error" in sel.columns
        else 0,
        "n_unresolved": int((~err & ~unmeasured & sel["value"].isna()).sum()),
        # Proportion items asked of a chat model as true/false have no answer
        # to score (see `_reread_chat_replies`), which is not a parse failure.
        "n_not_measurable": int(unmeasured.sum()),
        "cells": len(cells),
        "cells_with_no_usable_answer": int((good_cells == 0).sum()),
        "error_rate_by_kind": json.dumps(by_kind, sort_keys=True),
        "cost_usd": cost,
    }


def compare_runs(paths: list[Path], out_dir: Path) -> dict[str, pd.DataFrame]:
    """Reduce each run with the single-run analysis, then join on served model."""
    from .plots import PROBABILITY_MEASURES

    if not paths:
        raise ValueError("compare needs at least one run file")

    frames: list[pd.DataFrame] = []
    health: list[dict[str, Any]] = []
    backends: set[str] = set()
    seen: dict[str, str] = {}
    for path in paths:
        df = load_records(path)
        backends |= set(df["backend"].unique())
        sdf = pd.DataFrame([asdict(s) for s in compute_stats(df)])
        for arm in sorted(df["arm"].unique()):
            label = _arm_label(df, arm)
            if label in seen:
                # The same model in two files (e.g. the chat baseline re-run
                # alongside each new System One model) would otherwise be
                # silently pooled under one name.
                raise ValueError(
                    f"{label} appears in both {seen[label]} and {_run_name(path)}; "
                    "pass only one run file per model"
                )
            seen[label] = _run_name(path)
            health.append(_health(df, arm, label, _run_name(path)))
            part = sdf[sdf["arm"] == arm].copy()
            part["arm"] = label
            part["type"] = SYSTEM_ONE if arm == "jev" else CHAT
            frames.append(part)

    if "simulator" in backends and len(backends) > 1:
        raise ValueError(
            "Comparison mixes simulated and live runs. Simulated output is "
            "structurally valid nonsense and must never be pooled with live data."
        )

    sdf = pd.concat(frames, ignore_index=True)
    types = dict(zip(sdf["arm"], sdf["type"], strict=False))

    fid, _ = human_fidelity(sdf, PROBABILITY_MEASURES)
    fdf = pd.DataFrame([asdict(f) for f in fid]).rename(columns={"arm": "model"})
    if len(fdf):
        fdf.insert(1, "type", fdf["model"].map(types))
        fdf = fdf.sort_values(["persona", "mae"]).reset_index(drop=True)

    rows: list[dict[str, Any]] = []
    for inst, stat, bench, label in PROBABILITY_MEASURES:
        for persona in ("neutral", "typical_human", "typical_human_plain"):
            sel = sdf[(sdf.instrument == inst) & (sdf.statistic == stat) & (sdf.persona == persona)]
            if not len(sel):
                continue
            row: dict[str, Any] = {
                "measure": label,
                "persona": persona,
                "human": BENCHMARKS[bench].value if bench in BENCHMARKS else float("nan"),
            }
            row.update({str(m): float(v) for m, v in zip(sel["arm"], sel["value"], strict=True)})
            rows.append(row)
    mdf = pd.DataFrame(rows)
    hdf = pd.DataFrame(health)

    # Follow-up H4 per System One model: estimate vs simulate. A chat model's
    # estimate items are not measurable (a true/false reply is not a proportion).
    h4_rows = []
    for model in sorted(m for m, t in types.items() if t == SYSTEM_ONE):
        for simulate in ("typical_human", "typical_human_plain"):
            table = simulate_vs_estimate(sdf, simulate=simulate, estimate="neutral", arm=model)
            if len(table):
                h4_rows.append({"model": model, "simulate": simulate, **h4_summary(table)})
    h4df = pd.DataFrame(h4_rows)

    out_dir.mkdir(parents=True, exist_ok=True)
    hdf.to_csv(out_dir / "health.csv", index=False)
    fdf.to_csv(out_dir / "fidelity.csv", index=False)
    mdf.to_csv(out_dir / "measures.csv", index=False)
    sdf.rename(columns={"arm": "model"}).to_csv(out_dir / "statistics.csv", index=False)
    h4df.to_csv(out_dir / "followup_h4.csv", index=False)

    with pd.option_context("display.width", 160, "display.max_columns", 20):
        print(hdf.drop(columns=["run_file"]).to_string(index=False))
        print()
        if len(fdf):
            print(fdf.round(3).to_string(index=False))
    for name in ("health.csv", "fidelity.csv", "measures.csv", "statistics.csv", "followup_h4.csv"):
        print(f"wrote {out_dir / name}")
    return {
        "health": hdf,
        "fidelity": fdf,
        "measures": mdf,
        "statistics": sdf,
        "followup_h4": h4df,
    }
