"""The option-order addendum's analysis (ORDER_PREREGISTRATION.md)."""

from __future__ import annotations

import random
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from jevbench.instruments import PERSONAS, all_probes
from jevbench.order_study import (
    Answer,
    Arm,
    Conditions,
    cell_spreads,
    holm,
    identify,
    paired_units,
    run_tests,
    slot_slope,
    usable_answers,
)
from jevbench.runner import UNUSABLE, prepare_probe, resume_order_mismatch

PERSONA_KEYS = ["p1", "p2", "p3", "p4", "p5"]


def _arm(version: str, rows: list[dict]) -> Arm:
    return Arm(version, "direct", Path(f"{version}.jsonl"), pd.DataFrame(rows))


def _rows(
    items: dict[str, str],
    *,
    shuffle: bool,
    pull: float,
    seed: int = 1,
    repeats: int = 10,
    noise: float = 0.0,
) -> list[dict]:
    """Two-option answers whose probability on the option in slot 2 rises by `pull`."""
    rows = []
    for pid in items:
        for persona in PERSONA_KEYS:
            for r in range(repeats):
                rng = random.Random(f"{seed}|{pid}|{persona}|{r}")
                order = ["a", "b"]
                if shuffle:
                    rng.shuffle(order)
                p_b = 0.5 + (pull if order[1] == "b" else -pull) + rng.uniform(-noise, noise)
                rows.append(
                    {
                        "probe_id": pid,
                        "persona": persona,
                        "replicate": r,
                        "probabilities": {"a": 1 - p_b, "b": p_b},
                        "option_order": order if shuffle else None,
                        "error": None,
                    }
                )
    return rows


ITEMS = {f"item{i}_{j}": f"inst{i}" for i in range(8) for j in range(2)}


def test_slot_slope_sign_and_undefined_case() -> None:
    later = [
        Answer({"a": 0.4, "b": 0.6}, ("a", "b")),
        Answer({"a": 0.6, "b": 0.4}, ("b", "a")),
    ]
    assert slot_slope(later) == pytest.approx(0.2)
    first = [
        Answer({"a": 0.6, "b": 0.4}, ("a", "b")),
        Answer({"a": 0.4, "b": 0.6}, ("b", "a")),
    ]
    assert slot_slope(first) == pytest.approx(-0.2)
    # The same order on every repeat leaves the slope undefined, not zero.
    assert slot_slope([Answer({"a": 0.6, "b": 0.4}, ("a", "b"))] * 10) is None


def test_paired_units_use_common_cells_and_drop_thin_items() -> None:
    items = {"x": "I", "y": "I"}
    left = {("x", p): 1.0 for p in PERSONA_KEYS} | {("y", "p1"): 1.0, ("y", "p2"): 1.0}
    right = {("x", p): 0.0 for p in PERSONA_KEYS[:3]} | {("y", p): 0.0 for p in PERSONA_KEYS}
    u = paired_units([left, right], items)
    # x keeps its three common cells; y has only two in common, so it drops out.
    assert u.items == ["x"]
    assert u.dropped_items == ["y"]
    assert u.instruments == ["I"]
    assert u.instrument_values == [[1.0, 0.0]]


def test_spreads_on_matched_repeats() -> None:
    rows = _rows({"x": "I"}, shuffle=False, pull=0.0, noise=0.2)
    rows += [{**r, "replicate": r["replicate"] + 10} for r in rows if r["persona"] == "p1"]
    ans = usable_answers(pd.DataFrame(rows))
    # Seven repeats is below the threshold of eight, so the cell is left out.
    seven = {("x", "p1"): set(range(7))}
    assert ("x", "p1") not in cell_spreads(ans, {"x": "I"}, seven)
    assert ("x", "p1") in cell_spreads(ans, {"x": "I"}, {("x", "p1"): set(range(12))})


def test_unusable_answers_do_not_count() -> None:
    rows = _rows({"x": "I"}, shuffle=False, pull=0.0)
    for r in rows[:3]:
        r["error"] = f"{UNUSABLE}bad"
    ans = usable_answers(pd.DataFrame(rows))
    assert len(ans[("x", "p1")]) == 7


def test_holm() -> None:
    adj = holm({"a": 0.01, "b": 0.04, "c": 0.03})
    assert adj["a"] == pytest.approx(0.03)
    assert adj["c"] == pytest.approx(0.06)
    assert adj["b"] == pytest.approx(0.06)  # monotone: never below an earlier step


def test_identify() -> None:
    assert identify(["jev-1.14.0"] * 3) == ("1.14", "direct")
    assert identify(["typesafe/jev-1.13-20260917"]) == ("1.13", "openrouter")
    with pytest.raises(ValueError, match="one served model"):
        identify(["jev-1.13.0", "jev-1.14.0"])
    with pytest.raises(ValueError, match="unexpected"):
        identify(["jev-1.15.0"])


def test_tests_detect_an_order_effect_and_its_direction() -> None:
    cond = Conditions(
        r2={
            "1.13": _arm("1.13", _rows(ITEMS, shuffle=True, pull=0.1)),
            "1.14": _arm("1.14", _rows(ITEMS, shuffle=True, pull=0.0, noise=0.01)),
        },
        r3={
            "1.13": _arm("1.13", _rows(ITEMS, shuffle=False, pull=0.1)),
            "1.14": _arm("1.14", _rows(ITEMS, shuffle=False, pull=0.0, noise=0.01)),
        },
    )
    table, _ = run_tests(cond, ITEMS)
    inst = table[table["unit"] == "instrument"].set_index("test")
    assert set(inst.index) == {"O1 1.13", "O1 1.14", "O2", "O3 1.13", "O3 1.14"}
    assert (inst["n_units"] == 8).all()
    # 1.13 moves with the slot; fixed order does not move it at all.
    assert inst.loc["O1 1.13", "p"] < 0.01
    assert inst.loc["O3 1.13", "median"] == pytest.approx(0.2)
    assert inst.loc["O3 1.13", "p"] < 0.01
    # 1.14 has no pull, so its order excess is lower than 1.13's.
    assert inst.loc["O2", "median"] < 0
    assert inst.loc["O2", "p"] < 0.01
    # Holm is applied across the five instrument-level tests only.
    assert table.loc[table["unit"] == "item", "p_holm"].isna().all()
    assert np.all(inst["p_holm"] >= inst["p"])


def test_resume_refuses_other_order_settings() -> None:
    probe = next(p for p in all_probes() if p.probe_id == "holt_laury_04")
    persona = next(iter(PERSONAS))

    def order(rep: int, seed: int) -> list[str] | None:
        prepared = prepare_probe(probe, persona, rep, seed=seed, randomise_options=True)
        return prepared.meta.get("option_order")

    # A repeat on which the two seeds present the options differently.
    rep = next(r for r in range(10) if order(r, 20261014) != order(r, 20260918))
    kept = [
        {
            "probe_id": probe.probe_id,
            "persona": persona,
            "replicate": rep,
            "option_order": order(rep, 20261014),
        }
    ]
    probes = [probe]
    assert resume_order_mismatch(kept, probes, seed=20261014, randomise_options=True) is None
    assert resume_order_mismatch(kept, probes, seed=20260918, randomise_options=True)
    assert resume_order_mismatch(kept, probes, seed=20261014, randomise_options=False)
