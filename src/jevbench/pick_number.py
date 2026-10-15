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
            # Jev rounds its probabilities, so a reply may sum to 0.99; renormalise.
            total = sum(mean.values())
            mean = {n: v / total for n, v in mean.items()} if total else mean
            rows.append(_row("Jev, its distribution", "jev", model, persona, mean, len(dists)))
            rows.append(
                _row(
                    "Jev, one pick per call",
                    "jev",
                    model,
                    persona,
                    _shares(picks),
                    sum(picks.values()),
                )
            )
        else:
            rows.append(
                _row(f"{chat_name(model)}, one pick per call", "baseline", model, persona, _shares(picks),
                     sum(picks.values()))
            )  # fmt: skip
    return rows


CHAT_SUFFIX = ", one pick per call"


def chat_name(model: str) -> str:
    """A readable name for the chat model that answered: `anthropic/claude-haiku-5.5` -> `Claude Haiku 5.5`."""
    words = model.split("/")[-1].split("-")
    return " ".join(w if any(c.isdigit() for c in w) else w.capitalize() for w in words)


def _row(
    source: str, arm: str, model: str, persona: str, dist: dict[str, float], n: int
) -> dict[str, Any]:
    h = human()
    probs = np.array([dist[k] for k in NUMBERS])
    nz = probs[probs > 0]
    return {
        "source": source,
        "arm": arm,
        "model": model,
        "persona": persona,
        "n": n,
        **{k: dist[k] for k in NUMBERS},
        "share_7": dist["7"],
        "top": max(NUMBERS, key=lambda k: dist[k]),
        "entropy_bits": float(-(nz * np.log2(nz)).sum()),
        "tv_from_people": tv_distance(dist, h),
    }


def check_complete(name: str, arm: str, g: pd.DataFrame) -> None:
    """Refuse an interrupted run: both prompts, the same repeats 0..n-1, no failed calls.

    The runner writes each call as it finishes, so a partial file looks like a
    smaller run; averaging it would quietly change the result.
    """
    if "error" in g.columns:
        unread = g["error"].notna() & ~g["error"].astype(str).str.startswith("unusable answer")
        if unread.any():
            raise ValueError(f"{name}: {int(unread.sum())} failed calls; rerun them with --resume")
    reps = {str(p): sorted(int(r) for r in grp["replicate"]) for p, grp in g.groupby("persona")}
    n = len(next(iter(reps.values()), []))
    if (
        sorted(reps) != sorted(PERSONAS)
        or n == 0
        or any(r != list(range(n)) for r in reps.values())
    ):
        sizes = {p: len(r) for p, r in reps.items()}
        raise ValueError(f"{name}: the {arm} arm is incomplete or uneven: {sizes}")


def analyse(root: Path = PICK_DIR, out_dir: Path = PICK_RESULTS_DIR) -> pd.DataFrame:
    files = sorted(root.glob("run_live_*.jsonl"))
    if not files:
        raise ValueError(f"no run files in {root}")
    frames = {f: load_records(f) for f in files}
    # Exactly one Jev run and one chat run: a rerun or another model left in
    # the folder would otherwise be pooled with these, or plotted in their place.
    by_arm: dict[str, list[str]] = {}
    for f, d in frames.items():
        for arm in d["arm"].unique():
            by_arm.setdefault(str(arm), []).append(f.name)
    if sorted(by_arm) != ["baseline", "jev"] or any(len(v) != 1 for v in by_arm.values()):
        raise ValueError(f"{root} needs exactly one Jev run and one chat run, found {by_arm}")
    # And one model per arm, so a run resumed with another model is refused.
    for f, d in frames.items():
        for arm, g in d.groupby("arm"):
            # Every record, unusable ones included: they carry the model that
            # answered (failed calls, which carry only the requested one, are
            # refused by check_complete).
            models = sorted(set(g["model"].astype(str)))
            if len(models) != 1:
                raise ValueError(f"{f.name}: the {arm!s} arm holds {models}, not one model")
            check_complete(f.name, str(arm), g)
    df = pd.concat(frames.values(), ignore_index=True)
    table = pd.DataFrame(summarise(df))
    # Every source needs usable answers under both prompts, or the figure
    # and table would silently lose a cell.
    for source in sorted(set(table["source"])):
        for persona in PERSONAS:
            cell = table[(table["source"] == source) & (table["persona"] == persona)]
            if cell.empty or int(cell["n"].iloc[0]) == 0:
                raise ValueError(f"no usable answers for {source} under {persona}")
    h = human()
    people = {
        "source": "People (YouGov)",
        "arm": "people",
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
            "records": len(d),
            "errors": int(d["error"].notna().sum()) if "error" in d.columns else 0,
            # A reply that arrived without a single pick from 1 to 10 (a chat
            # reply naming no number, or a Jev choice outside the options) is
            # left out of the one-pick counts, so it is reported here.
            "picks_left_out": int(
                (d["error"].isna() & ~d["value"].astype(str).isin(NUMBERS)).sum()
            ),
        }
        for f, d in frames.items()
    }
    (out_dir / "summary.json").write_text(
        json.dumps({"files": health, "human_source": YOUGOV_SOURCE}, indent=2) + "\n"
    )
    return table
