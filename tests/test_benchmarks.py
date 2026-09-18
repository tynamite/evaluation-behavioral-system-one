"""Every benchmark must be attributable, and every reference must resolve."""

from __future__ import annotations

from jevbench.benchmarks import BENCHMARKS


def test_every_benchmark_cites_a_source_and_declares_reliability() -> None:
    for key, b in BENCHMARKS.items():
        assert b.source.strip(), f"{key} has no source"
        assert any(ch.isdigit() for ch in b.source), f"{key}'s source has no year"
        assert b.reliability in {"high", "medium", "approximate"}, key
        assert b.units.strip(), f"{key} has no units"


def test_proportion_benchmarks_are_in_range() -> None:
    for key, b in BENCHMARKS.items():
        if b.units == "proportion" or "share" in b.units:
            assert 0.0 <= b.value <= 1.0, f"{key} = {b.value} is not a proportion"


def test_keys_match_their_dict_entries() -> None:
    for key, b in BENCHMARKS.items():
        assert key == b.key
