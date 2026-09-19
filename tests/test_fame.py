"""The fame index (`FOLLOWUP_PREREGISTRATION.md` Section 8.2, Amendment 1)."""

from __future__ import annotations

from jevbench import fame
from jevbench.benchmarks import BENCHMARKS


def test_fourteen_items_matching_the_preregistration_pool() -> None:
    assert len(fame.ITEMS) == 14
    assert set(fame.ITEMS) == {
        "crt",
        "framing",
        "conjunction",
        "sunk_cost",
        "allais",
        "base_rate",
        "knobe",
        "trolley",
        "false_consensus",
        "moral_typecasting",
        "position_power",
        "choosing_rejecting",
        "categorization",
        "incidental_anchors",
    }


def test_every_referenced_benchmark_exists() -> None:
    for item in fame.ITEMS.values():
        for key in item.benchmarks:
            assert key in BENCHMARKS, f"{item.key} references missing benchmark {key!r}"


def test_missing_citation_counts_are_documented_not_guessed() -> None:
    """A None citation_count must carry an explanatory note, never a silent gap."""
    for item in fame.ITEMS.values():
        if item.citation_count is None:
            assert item.citation_note, f"{item.key} has no citation_count and no explanation"
        else:
            assert item.citation_count > 0
            assert item.citation_note


def test_wikipedia_words_nonnegative_and_article_name_consistent() -> None:
    for item in fame.ITEMS.values():
        assert item.wikipedia_words >= 0
        if item.wikipedia_words > 0:
            assert item.wikipedia_article, f"{item.key} has words but no article name"
        if item.wikipedia_article is None:
            assert item.wikipedia_words == 0


def test_citation_tier_terciles_known_items() -> None:
    """The ten items with a known citation count split into three roughly even tiers."""
    known = {k: i for k, i in fame.ITEMS.items() if i.citation_count is not None}
    assert len(known) == 10
    tiers = {k: fame.citation_tier(i) for k, i in known.items()}
    assert set(tiers.values()) == {"low", "medium", "high"}
    # Highest and lowest citation counts must land at the tier extremes.
    ranked = sorted(known.values(), key=lambda i: i.citation_count or 0)
    assert tiers[ranked[0].key] == "low"
    assert tiers[ranked[-1].key] == "high"


def test_citation_tier_none_for_unknown_counts() -> None:
    for key in ("crt", "trolley", "position_power", "base_rate"):
        assert fame.ITEMS[key].citation_count is None
        assert fame.citation_tier(fame.ITEMS[key]) is None


def test_wikipedia_tier_zero_words_is_always_low() -> None:
    for item in fame.ITEMS.values():
        if item.wikipedia_words == 0:
            assert fame.wikipedia_tier(item) == "low"


def test_wikipedia_tier_spans_all_three_tiers_among_items_with_an_article() -> None:
    with_article = [i for i in fame.ITEMS.values() if i.wikipedia_words > 0]
    tiers = {fame.wikipedia_tier(i) for i in with_article}
    assert tiers == {"low", "medium", "high"}


def test_drop_rule_fires_when_citation_leg_is_missing() -> None:
    for key in ("crt", "trolley", "position_power", "base_rate"):
        verdict = fame.evaluate(fame.ITEMS[key], ratings={})
        assert verdict.dropped
        assert verdict.fame_tier is None
        assert "citation count unavailable" in verdict.reason


def test_drop_rule_fires_when_legs_disagree_by_more_than_one_tier() -> None:
    """knobe: high wikipedia depth borrowed via a synthetic item shouldn't be needed —
    construct a direct FameItem whose two legs are engineered to disagree by 2 tiers."""
    lo_citations = fame.FameItem(
        "synthetic_low_high",
        "synthetic",
        "n/a",
        1,
        "synthetic test fixture",
        "Some article",
        999_999,
        (),
        "synthetic",
    )
    # citation_tier() needs the item present in ITEMS to compute terciles against
    # the real distribution; a citation_count of 1 is below every real item's count,
    # so it lands in the low tier, while its absurd word count lands in the high tier.
    fame.ITEMS["synthetic_low_high"] = lo_citations
    try:
        verdict = fame.evaluate(lo_citations, ratings={})
        assert fame.citation_tier(lo_citations) == "low"
        assert fame.wikipedia_tier(lo_citations) == "high"
        assert verdict.dropped
        assert "disagree" in verdict.reason
    finally:
        del fame.ITEMS["synthetic_low_high"]


def test_evaluate_keeps_items_whose_legs_agree() -> None:
    kept = [v for v in fame.all_verdicts(ratings={}) if not v.dropped]
    assert kept, "expected at least one item to survive the drop rule"
    for v in kept:
        assert v.fame_tier in {"low", "medium", "high"}


def test_load_familiarity_empty_when_file_absent(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(fame, "FAMILIARITY_PATH", tmp_path / "does_not_exist.json")
    assert fame.load_familiarity() == {}
    assert fame.familiarity_mean("crt", {}) is None


def test_familiarity_mean_averages_replicates() -> None:
    ratings = {"crt": [1.0, 2.0, 3.0]}
    assert fame.familiarity_mean("crt", ratings) == 2.0


def test_all_verdicts_covers_every_item() -> None:
    verdicts = fame.all_verdicts(ratings={})
    assert {v.key for v in verdicts} == set(fame.ITEMS)
