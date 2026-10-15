"""Pick a number between 1 and 10: Jev, a chat model and people (exploratory).

A chat model answers one number per call, so its "distribution" is a count
over many calls at temperature 1. Jev returns the whole distribution in each
call. The same Jev calls also return a single chosen number, so counting those
picks shows what Jev looks like when read the way a chat model is read.

The human reference is YouGov's survey of 2,241 British adults (12-13 Sep
2024), an open text box: "Think of a random number from 1-10. What number did
you think of?" The items here use that wording. This is exploratory, not
preregistered.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .analysis import load_records, tv_distance
from .config import RAW_DIR, REPO_ROOT
from .instruments.base import Probe
from .schema import Choice

PICK_DIR = RAW_DIR / "pick_number"
PICK_RESULTS_DIR = REPO_ROOT / "results" / "pick_number"
NUMBERS = [str(i) for i in range(1, 11)]
PERSONAS = ["neutral", "typical_human"]

QUESTION = "Think of a random number from 1-10. What number did you think of?"
PROBE = Probe(
    probe_id="pick_number_1_10",
    instrument="pick_number",
    question=Choice(instructions=QUESTION, criteria={n: n for n in NUMBERS}),
    state={"task": QUESTION},
)

# YouGov, "Britons most likely to pick 7 as 'random' number", 2,241 GB adults,
# fieldwork 12-13 Sep 2024, open question. Published percentages, rounded, so
# they sum to 101; they are normalised before use.
YOUGOV_SOURCE = "https://yougov.com/en-gb/articles/51866-seven-is-the-most-random-number"
YOUGOV_PERCENT = {
    "1": 2, "2": 4, "3": 7, "4": 9, "5": 8, "6": 14, "7": 33, "8": 14, "9": 6, "10": 4,
}  # fmt: skip


def human() -> dict[str, float]:
    total = sum(YOUGOV_PERCENT.values())
    return {n: YOUGOV_PERCENT[n] / total for n in NUMBERS}


def _shares(counts: Counter[str]) -> dict[str, float]:
    n = sum(counts.values())
    return {k: (counts.get(k, 0) / n if n else 0.0) for k in NUMBERS}


def summarise(df: pd.DataFrame) -> list[dict[str, Any]]:
    """One distribution per source and prompt.

    For Jev: the mean of its returned distributions, and the share of calls
    whose single chosen number was each value. For the chat model: the share
    of samples naming each value. Unusable and unread replies are left out
    and counted.
    """
    rows: list[dict[str, Any]] = []
    ok = df[df["error"].isna()] if "error" in df.columns else df
    for key, g in ok.groupby(["arm", "model", "persona"]):
        arm, model, persona = (str(k) for k in key)
        picks = Counter(str(v) for v in g["value"] if v is not None and str(v) in NUMBERS)
        if arm == "jev":
            dists = [p for p in g["probabilities"] if isinstance(p, dict) and p]
            mean = {n: float(np.mean([d.get(n, 0.0) for d in dists])) for n in NUMBERS}
            rows.append(_row("Jev, its distribution", model, persona, mean, len(dists)))
            rows.append(
                _row("Jev, one pick per call", model, persona, _shares(picks), sum(picks.values()))
            )
        else:
            rows.append(
                _row("Haiku, one pick per call", model, persona, _shares(picks),
                     sum(picks.values()))
            )  # fmt: skip
    return rows


def _row(source: str, model: str, persona: str, dist: dict[str, float], n: int) -> dict[str, Any]:
    h = human()
    probs = np.array([dist[k] for k in NUMBERS])
    nz = probs[probs > 0]
    return {
        "source": source,
        "model": model,
        "persona": persona,
        "n": n,
        **{k: dist[k] for k in NUMBERS},
        "share_7": dist["7"],
        "top": max(NUMBERS, key=lambda k: dist[k]),
        "entropy_bits": float(-(nz * np.log2(nz)).sum()),
        "tv_from_people": tv_distance(dist, h),
    }


def analyse(root: Path = PICK_DIR, out_dir: Path = PICK_RESULTS_DIR) -> pd.DataFrame:
    files = sorted(root.glob("run_live_*.jsonl"))
    if not files:
        raise ValueError(f"no run files in {root}")
    df = pd.concat([load_records(f) for f in files], ignore_index=True)
    table = pd.DataFrame(summarise(df))
    h = human()
    people = {
        "source": "People (YouGov)",
        "model": "2,241 GB adults, Sep 2024",
        "persona": "",
        "n": 2241,
        **h,
        "share_7": h["7"],
        "top": "7",
        "entropy_bits": float(-sum(v * np.log2(v) for v in h.values() if v)),
        "tv_from_people": 0.0,
    }
    table = pd.concat([table, pd.DataFrame([people])], ignore_index=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    table.to_csv(out_dir / "distributions.csv", index=False)
    health = {
        f.name: {
            "records": len(d := load_records(f)),
            "errors": int(d["error"].notna().sum()) if "error" in d.columns else 0,
        }
        for f in files
    }
    (out_dir / "summary.json").write_text(
        json.dumps({"files": health, "human_source": YOUGOV_SOURCE}, indent=2) + "\n"
    )
    return table
