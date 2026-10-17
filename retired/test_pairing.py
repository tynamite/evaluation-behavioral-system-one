"""ml2_effects.py and pairing.py: the Section 3 pairing rule.

The real result on real data is a well-defined negative: every item with a
valid ML2-replicated magnitude that also survives the fame drop rule happens
to land in the fame index's `low` tier, so the pairing rule -- applied
exactly as preregistered -- forms zero pairs. That's tested directly below,
alongside a synthetic fixture proving the matching algorithm itself is
correct (nearest-neighbour, opposite tercile, without replacement) rather
than vacuously empty by construction.
"""

from __future__ import annotations

import math

from jevbench import fame, pairing
from jevbench.ml2_effects import ML2_EFFECTS
from jevbench.pairing import EligibleItem, Pair


def test_every_fame_item_has_an_ml2_effects_entry() -> None:
    assert set(ML2_EFFECTS) == set(fame.ITEMS)


def test_non_matching_effects_carry_an_explanatory_note() -> None:
    for effect in ML2_EFFECTS.values():
        if not effect.matches_probe:
            assert effect.match_note, f"{effect.item_key} has no match_note explaining why not"


def test_framing_and_false_consensus_are_flagged_as_non_matching() -> None:
    """The two cases where ML2 replicated a *different* study from the same source
    paper -- a real finding from reading the full ML2 results, not an oversight."""
    assert ML2_EFFECTS["framing"].matches_probe is False
    assert ML2_EFFECTS["false_consensus"].matches_probe is False
    assert "different" in ML2_EFFECTS["framing"].match_note.lower()
    assert "sandwich-board" in ML2_EFFECTS["false_consensus"].match_note.lower()


def test_items_absent_from_ml2s_28_have_no_effect_number() -> None:
    for key in ("crt", "conjunction", "sunk_cost", "allais", "base_rate"):
        effect = ML2_EFFECTS[key]
        assert effect.matches_probe is False
        assert effect.ml2_effect_number is None


def test_cohens_h_matches_a_hand_worked_case() -> None:
    # h(0.5, 0.5) = 0 (identical proportions); h is antisymmetric.
    assert pairing.cohens_h(0.5, 0.5) == 0.0
    assert math.isclose(pairing.cohens_h(0.8, 0.2), -pairing.cohens_h(0.2, 0.8))
    # A textbook value: h(0.6, 0.4) is a "small-to-medium" effect, positive.
    assert 0.35 < pairing.cohens_h(0.6, 0.4) < 0.45


def test_magnitude_uses_h_for_choice_and_d_for_score() -> None:
    trolley_mag = pairing.magnitude(ML2_EFFECTS["trolley"])
    assert trolley_mag is not None
    expected_h = abs(pairing.cohens_h(0.71, 0.17))
    assert math.isclose(trolley_mag, expected_h)

    anchors_mag = pairing.magnitude(ML2_EFFECTS["incidental_anchors"])
    assert anchors_mag == 0.04  # ML2's own replicated d, used directly


def test_magnitude_falls_back_to_d_when_no_replicated_proportions_exist() -> None:
    """knobe's replication changed measurement scale (dichotomous -> 7-point), so
    there's no replicated proportion pair to compute h from."""
    assert ML2_EFFECTS["knobe"].replicated_proportions is None
    assert pairing.magnitude(ML2_EFFECTS["knobe"]) == 1.75


def test_magnitude_none_for_effects_with_no_replicated_number_at_all() -> None:
    for key in ("crt", "conjunction", "sunk_cost", "allais", "base_rate"):
        assert pairing.magnitude(ML2_EFFECTS[key]) is None


def test_eligible_items_on_real_data() -> None:
    """The two filters -- fame drop rule, and matches_probe -- together leave
    exactly five items, and by construction of the real fame/ML2 data (not by
    any rule in the pairing code itself) all five land in the 'low' tier."""
    elig = pairing.eligible_items()
    assert {e.key for e in elig} == {
        "knobe",
        "moral_typecasting",
        "choosing_rejecting",
        "categorization",
        "incidental_anchors",
    }
    assert {e.fame_tier for e in elig} == {"low"}


def test_build_pairs_on_real_data_is_empty() -> None:
    """With every eligible item in the same tercile, there is no opposite-tercile
    partner for any of them -- the honest result of applying Section 3's rule to
    the actual gathered data, not a bug in the matching logic (see the synthetic
    fixture tests below for proof the algorithm itself works)."""
    assert pairing.build_pairs() == []


# -- synthetic fixture: proves the matching algorithm itself is correct ----


def test_synthetic_nearest_neighbour_matches_the_closest_opposite_tier_item() -> None:
    items = [
        EligibleItem("a_low", "low", "choice", 0.10),
        EligibleItem("b_low", "low", "choice", 0.90),
        EligibleItem("c_high", "high", "choice", 0.15),
        EligibleItem("d_high", "high", "choice", 1.20),
    ]
    pairs = pairing.build_pairs(items)
    by_pair = {frozenset((p.lower_fame_key, p.higher_fame_key)) for p in pairs}
    # a_low (0.10) is closest to c_high (0.15); b_low (0.90) is closest to d_high (1.20).
    assert frozenset({"a_low", "c_high"}) in by_pair
    assert frozenset({"b_low", "d_high"}) in by_pair
    assert len(pairs) == 2


def test_synthetic_matching_is_without_replacement() -> None:
    """Two low items both nearest to the same single high item: only one gets it."""
    items = [
        EligibleItem("close_1", "low", "score", 0.50),
        EligibleItem("close_2", "low", "score", 0.52),
        EligibleItem("only_high", "high", "score", 0.51),
    ]
    pairs = pairing.build_pairs(items)
    assert len(pairs) == 1
    used = {pairs[0].lower_fame_key, pairs[0].higher_fame_key}
    assert "only_high" in used
    assert len(used & {"close_1", "close_2"}) == 1


def test_synthetic_single_tercile_forms_no_pairs() -> None:
    items = [
        EligibleItem("x", "low", "choice", 0.3),
        EligibleItem("y", "low", "choice", 0.6),
    ]
    assert pairing.build_pairs(items) == []


def test_synthetic_medium_pairs_with_high_when_no_low_competes() -> None:
    """Isolated from any low-tier item, so this tests medium's own preference order
    rather than the (separate, and intentionally higher-priority) low-high rule --
    see test_synthetic_true_opposite_pairs_take_priority_over_medium below."""
    items = [
        EligibleItem("mid", "medium", "score", 0.50),
        EligibleItem("hi", "high", "score", 0.55),
    ]
    pairs = pairing.build_pairs(items)
    assert len(pairs) == 1
    assert {pairs[0].lower_fame_key, pairs[0].higher_fame_key} == {"mid", "hi"}


def test_synthetic_true_opposite_pairs_take_priority_over_medium() -> None:
    """When a low and a high item are both available, they pair with each other --
    the strongest, most informative contrast -- even if a medium item's magnitude
    would otherwise make it the nearer match to the high item. The medium item is
    left unpaired rather than displacing the true low-high opposite pair."""
    items = [
        EligibleItem("mid", "medium", "score", 0.50),
        EligibleItem("hi", "high", "score", 0.52),
        EligibleItem("lo", "low", "score", 2.0),
    ]
    pairs = pairing.build_pairs(items)
    assert len(pairs) == 1
    assert {pairs[0].lower_fame_key, pairs[0].higher_fame_key} == {"lo", "hi"}


def test_synthetic_medium_falls_back_to_low_when_no_high_present() -> None:
    items = [
        EligibleItem("mid", "medium", "score", 0.50),
        EligibleItem("lo", "low", "score", 0.48),
    ]
    pairs = pairing.build_pairs(items)
    assert len(pairs) == 1
    assert {pairs[0].lower_fame_key, pairs[0].higher_fame_key} == {"mid", "lo"}


def test_format_groups_never_mix_in_a_pair() -> None:
    items = [
        EligibleItem("choice_low", "low", "choice", 0.5),
        EligibleItem("score_high", "high", "score", 0.5),
    ]
    assert pairing.build_pairs(items) == []


def test_pair_orders_lower_and_higher_fame_correctly() -> None:
    items = [
        EligibleItem("famous", "high", "choice", 1.0),
        EligibleItem("obscure", "low", "choice", 1.0),
    ]
    pairs = pairing.build_pairs(items)
    assert len(pairs) == 1
    p: Pair = pairs[0]
    assert p.lower_fame_key == "obscure"
    assert p.higher_fame_key == "famous"
