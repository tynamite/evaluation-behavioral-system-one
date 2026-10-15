"""The pick-a-number comparison: Jev read two ways, a chat model, and people."""

from __future__ import annotations

import pandas as pd
import pytest

from jevbench.pick_number import NUMBERS, YOUGOV_PERCENT, human, summarise


def _jev(probs: dict[str, float], value: str) -> dict:
    return {"arm": "jev", "model": "jev-1.13.0", "persona": "neutral", "error": None,
            "probabilities": probs, "value": value}  # fmt: skip


def test_jev_is_read_two_ways_and_the_chat_model_once() -> None:
    a = {"7": 0.6, "5": 0.4}
    b = {"7": 0.2, "3": 0.8}
    chat = [{"arm": "baseline", "model": "haiku", "persona": "neutral", "error": None,
             "probabilities": {}, "value": v} for v in ("7", "7", "3", None)]  # fmt: skip
    rows = {r["source"]: r for r in summarise(pd.DataFrame([_jev(a, "7"), _jev(b, "3"), *chat]))}
    dist = rows["Jev, its distribution"]
    assert dist["7"] == pytest.approx(0.4) and dist["3"] == pytest.approx(0.4)
    picks = rows["Jev, one pick per call"]
    assert picks["7"] == pytest.approx(0.5) and picks["n"] == 2
    # An unread chat reply is left out, not counted as a number.
    chat_row = rows["Haiku, one pick per call"]
    assert chat_row["n"] == 3 and chat_row["7"] == pytest.approx(2 / 3)


def test_human_reference_is_yougov_normalised() -> None:
    h = human()
    assert list(h) == NUMBERS
    assert sum(h.values()) == pytest.approx(1.0)
    assert sum(YOUGOV_PERCENT.values()) == 101  # published, rounded
    assert max(h, key=h.get) == "7"
