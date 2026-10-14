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


MIN_REPEATS_FOR_FILE = 10


def _record_file(tmp_path: Path, name: str, served: str, *, seed: int, shuffled: bool) -> Path:
    """A small runner-shaped run file of one real multiple-choice item."""
    import json
    from dataclasses import asdict

    from jevbench.runner import Record

    probe = next(p for p in all_probes() if p.probe_id == "holt_laury_04")
    path = tmp_path / name
    with path.open("w") as fh:
        for persona in list(PERSONAS)[:3]:
            for rep in range(MIN_REPEATS_FOR_FILE):
                prepared = prepare_probe(probe, persona, rep, seed=seed, randomise_options=shuffled)
                keys = list(prepared.question.criteria)
                rec = Record(
                    probe_id=probe.probe_id,
                    instrument=probe.instrument,
                    persona=persona,
                    arm="jev",
                    replicate=rep,
                    backend="typesafe",
                    model=served,
                    kind="choice",
                    value=keys[0],
                    probabilities={keys[0]: 0.7, keys[1]: 0.3},
                    option_order=prepared.meta.get("option_order"),
                    meta=probe.meta,
                )
                fh.write(json.dumps(asdict(rec)) + "\n")
    return path


def test_load_arm_refuses_a_version_other_than_requested(tmp_path: Path) -> None:
    from jevbench.order_study import load_arm

    ok = _record_file(
        tmp_path, "run_live_20261014T000000Z_jev-1.14.0.jsonl", "jev-1.14.0", seed=1, shuffled=True
    )
    assert load_arm(ok).version == "1.14"
    wrong = _record_file(
        tmp_path, "run_live_20261014T000001Z_jev-1.14.0.jsonl", "jev-1.13.0", seed=1, shuffled=True
    )
    with pytest.raises(ValueError, match=r"requested jev-1\.14\.0"):
        load_arm(wrong)
    routed = _record_file(
        tmp_path,
        "run_live_20261014T000002Z_typesafe--jev-1.13.jsonl",
        "typesafe/jev-1.13-20260917",
        seed=1,
        shuffled=True,
    )
    assert (load_arm(routed).version, load_arm(routed).route) == ("1.13", "openrouter")


def test_condition_check_catches_a_run_made_with_the_wrong_order(tmp_path: Path) -> None:
    from jevbench.order_study import check_condition, load_arm

    r2 = _record_file(
        tmp_path,
        "run_live_20261014T000000Z_jev-1.13.0.jsonl",
        "jev-1.13.0",
        seed=20261014,
        shuffled=True,
    )
    check_condition(load_arm(r2), "r2")
    # Run as R2 but without --seed 20261014, or as R3 without --fixed-order.
    with pytest.raises(ValueError, match="r1's option order"):
        check_condition(load_arm(r2), "r1")
    with pytest.raises(ValueError, match="r3's option order"):
        check_condition(load_arm(r2), "r3")
    r3 = _record_file(
        tmp_path,
        "run_live_20261014T000001Z_jev-1.13.0.jsonl",
        "jev-1.13.0",
        seed=20261014,
        shuffled=False,
    )
    check_condition(load_arm(r3), "r3")


def test_tests_refuse_an_incomplete_family() -> None:
    one = Conditions(
        r2={"1.13": _arm("1.13", _rows(ITEMS, shuffle=True, pull=0.1))},
        r3={"1.13": _arm("1.13", _rows(ITEMS, shuffle=False, pull=0.1))},
    )
    with pytest.raises(ValueError, match=r"1\.13 and of 1\.14"):
        run_tests(one, ITEMS)


def test_requested_slug_reads_the_jev_arm_of_a_two_model_run() -> None:
    from jevbench.order_study import requested_slug

    two = Path("run_live_20261012T225915Z_typesafe--jev-1.13+anthropic--claude-sonnet-5.5.jsonl")
    assert requested_slug(two) == "typesafe--jev-1.13"
    assert requested_slug(Path("run_live_20261014T000000Z_jev-1.14.0.jsonl")) == "jev-1.14.0"


def test_completeness_refuses_a_run_that_is_not_the_designed_one(tmp_path: Path) -> None:
    from jevbench.order_study import check_complete, load_arm

    # One item under three personas: the per-cell thresholds would pass it,
    # but it is nowhere near the designed core run.
    partial = _record_file(
        tmp_path,
        "run_live_20261014T000000Z_jev-1.13.0.jsonl",
        "jev-1.13.0",
        seed=20261014,
        shuffled=True,
    )
    with pytest.raises(ValueError, match="not the designed r2 run"):
        check_complete(load_arm(partial), "r2")


def test_failed_calls_must_be_rerun_first(tmp_path: Path) -> None:
    import json

    from jevbench.order_study import check_complete, load_arm

    path = _record_file(
        tmp_path,
        "run_live_20261014T000000Z_jev-1.13.0.jsonl",
        "jev-1.13.0",
        seed=20261014,
        shuffled=True,
    )
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    rows[0].update(error="HTTP 500", probabilities={}, value=None)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    with pytest.raises(ValueError, match="failed calls; rerun them with --resume"):
        check_complete(load_arm(path), "r2")


def test_resume_checks_kept_records_outside_the_selected_modules(tmp_path: Path) -> None:
    import json

    from jevbench.config import Config
    from jevbench.runner import run_battery

    path = _record_file(
        tmp_path,
        "run_simulated_20261014T000000Z_jev-1.13.0.jsonl",
        "jev-1.13.0",
        seed=20261014,
        shuffled=True,
    )
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    path.write_text("".join(json.dumps({**r, "backend": "simulator"}) + "\n" for r in rows))
    # The kept Holt-Laury records are in risk_time; resuming only crt with the
    # default seed must still be refused.
    with pytest.raises(RuntimeError, match="cannot resume"):
        run_battery(
            Config(backend="simulator", model="jev-1.13.0"),
            modules=["crt"],
            replicates=1,
            resume=path,
        )


def test_study_must_be_the_designed_set_of_runs() -> None:
    from jevbench.order_study import check_design

    def arms(*pairs: tuple[str, str]) -> list[Arm]:
        return [
            Arm(v, r, Path(f"{v}-{r}-{i}.jsonl"), pd.DataFrame()) for i, (v, r) in enumerate(pairs)
        ]

    both = [("1.13", "direct"), ("1.14", "direct")]
    full = {"r1": arms(*both, ("1.13", "openrouter")), "r2": arms(*both), "r3": arms(*both)}
    check_design(full, has_fallback=False)
    # No fresh OpenRouter run: only with the committed fallback.
    no_or = {**full, "r1": arms(*both)}
    with pytest.raises(ValueError, match="openrouter-fallback"):
        check_design(no_or, has_fallback=False)
    check_design(no_or, has_fallback=True)
    # A fresh OpenRouter run and a fallback together is ambiguous.
    with pytest.raises(ValueError, match="not used then"):
        check_design(full, has_fallback=True)
    # One direct R1 version missing, or a duplicate OpenRouter run.
    with pytest.raises(ValueError, match="r1 is not the designed set"):
        check_design({**full, "r1": arms(("1.13", "direct"), ("1.13", "openrouter"))}, False)
    with pytest.raises(ValueError, match="more than one run"):
        check_design({**full, "r1": full["r1"] + arms(("1.13", "openrouter"))}, False)
