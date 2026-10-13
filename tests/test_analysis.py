"""Statistical primitives, and the guard against pooling simulated with live data."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from jevbench.analysis import (
    bootstrap_ci,
    distributions,
    expected_level,
    expected_numeric,
    load_records,
    prob_of,
    tv_distance,
)


def test_expected_numeric_parses_currency_keys() -> None:
    assert expected_numeric({"$0": 0.5, "$10": 0.5}) == pytest.approx(5.0)
    assert expected_numeric({"$2": 1.0}) == pytest.approx(2.0)


def test_expected_numeric_ignores_non_numeric_keys() -> None:
    assert expected_numeric({"accept": 0.5, "$4": 0.5}) == pytest.approx(4.0)
    assert expected_numeric({"accept": 1.0}) is None


def test_expected_level_is_one_based() -> None:
    assert expected_level({"0": 1.0}, 5) == pytest.approx(1.0)
    assert expected_level({"4": 1.0}, 5) == pytest.approx(5.0)
    assert expected_level({"0": 0.5, "4": 0.5}, 5) == pytest.approx(3.0)


def test_expected_level_reverse_keying_mirrors_the_scale() -> None:
    assert expected_level({"0": 1.0}, 5, reverse=True) == pytest.approx(5.0)
    assert expected_level({"4": 1.0}, 5, reverse=True) == pytest.approx(1.0)
    assert expected_level({"2": 1.0}, 5, reverse=True) == pytest.approx(3.0), "midpoint is fixed"


def test_tv_distance_bounds() -> None:
    assert tv_distance({"a": 1.0}, {"a": 1.0}) == pytest.approx(0.0)
    assert tv_distance({"a": 1.0}, {"b": 1.0}) == pytest.approx(1.0)
    assert tv_distance({"a": 0.5, "b": 0.5}, {"a": 1.0}) == pytest.approx(0.5)


def test_prob_of_sums_and_tolerates_missing_keys() -> None:
    assert prob_of({"a": 0.3, "b": 0.2}, "a", "b") == pytest.approx(0.5)
    assert prob_of({"a": 0.3}, "zzz") == pytest.approx(0.0)


def test_bootstrap_ci_brackets_the_mean() -> None:
    lo, hi = bootstrap_ci([0.2, 0.4, 0.6, 0.8], n=2000)
    assert lo <= 0.5 <= hi


def test_bootstrap_ci_handles_degenerate_input() -> None:
    import math

    lo, hi = bootstrap_ci([])
    assert math.isnan(lo) and math.isnan(hi), "empty input yields nan rather than raising"
    lo, hi = bootstrap_ci([0.5])
    assert lo == hi == pytest.approx(0.5), "a single value has a degenerate interval"


def test_distributions_average_jev_replicates() -> None:
    df = pd.DataFrame(
        [
            {
                "probe_id": "p",
                "persona": "neutral",
                "arm": "jev",
                "error": None,
                "probabilities": {"a": 1.0, "b": 0.0},
                "value": "a",
            },
            {
                "probe_id": "p",
                "persona": "neutral",
                "arm": "jev",
                "error": None,
                "probabilities": {"a": 0.0, "b": 1.0},
                "value": "b",
            },
        ]
    )
    d = distributions(df)[("p", "neutral", "jev")]
    assert d["a"] == pytest.approx(0.5)
    assert d["b"] == pytest.approx(0.5)


def test_distributions_turn_baseline_samples_into_frequencies() -> None:
    df = pd.DataFrame(
        [
            {
                "probe_id": "p",
                "persona": "neutral",
                "arm": "baseline",
                "error": None,
                "probabilities": {},
                "value": v,
            }
            for v in ["a", "a", "a", "b"]
        ]
    )
    d = distributions(df)[("p", "neutral", "baseline")]
    assert d["a"] == pytest.approx(0.75)
    assert d["b"] == pytest.approx(0.25)


def test_baseline_ignores_unparsed_replies() -> None:
    df = pd.DataFrame(
        [
            {
                "probe_id": "p",
                "persona": "neutral",
                "arm": "baseline",
                "error": None,
                "probabilities": {},
                "value": v,
            }
            for v in ["a", None, "b"]
        ]
    )
    d = distributions(df)[("p", "neutral", "baseline")]
    assert d["a"] == pytest.approx(0.5)


def test_refuses_to_pool_simulated_with_live_records(tmp_path: Path) -> None:
    path = tmp_path / "run_mixed.jsonl"
    rows = [
        {
            "probe_id": "p",
            "persona": "neutral",
            "arm": "jev",
            "backend": "simulator",
            "probabilities": {"a": 1.0},
            "error": None,
            "value": "a",
            "usage": {},
        },
        {
            "probe_id": "p",
            "persona": "neutral",
            "arm": "jev",
            "backend": "openrouter",
            "probabilities": {"a": 1.0},
            "error": None,
            "value": "a",
            "usage": {},
        },
    ]
    path.write_text("\n".join(json.dumps(r) for r in rows))
    with pytest.raises(ValueError, match="simulated and live"):
        load_records(path)


def test_simulate_vs_estimate_scales_errors_and_pairs_the_right_cells() -> None:
    from jevbench.analysis import h4_summary, simulate_vs_estimate

    rows = [
        # categorization: human 0.67. Simulate 0.07 (error 0.60), estimate 0.57 (0.10).
        ("categorization", "prob_rule_based", "typical_human", 0.07, "norenzayan_rule_based"),
        ("categorization_estimate", "prob_rule_based", "neutral", 0.57, "norenzayan_rule_based"),
        # An estimate under a persona must be ignored by the preregistered pairing.
        (
            "categorization_estimate",
            "prob_rule_based",
            "typical_human",
            0.99,
            "norenzayan_rule_based",
        ),
        # incidental anchor on a 0-100 scale: human 58.1; errors divided by 100.
        ("incidental_anchors", "estimate_p97", "typical_human", 48.1, "incidental_anchor_p97"),
        ("incidental_anchors_estimate", "estimate_p97", "neutral", 63.1, "incidental_anchor_p97"),
    ]
    sdf = pd.DataFrame(
        [
            {
                "instrument": i,
                "statistic": s,
                "persona": p,
                "arm": "jev",
                "value": v,
                "benchmark_key": b,
            }
            for i, s, p, v, b in rows
        ]
    )
    table = simulate_vs_estimate(sdf).set_index("instrument")
    assert table.loc["categorization", "error_simulate"] == pytest.approx(0.60)
    assert table.loc["categorization", "error_estimate"] == pytest.approx(0.10)
    assert table.loc["incidental_anchors", "error_simulate"] == pytest.approx(0.10)
    assert table.loc["incidental_anchors", "error_estimate"] == pytest.approx(0.05)
    summary = h4_summary(table.reset_index())
    assert summary["n"] == 2 and summary["estimate_closer"] == 2
