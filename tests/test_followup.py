"""The follow-up battery (`FOLLOWUP_PREREGISTRATION.md`).

Most integrity checks are already generic and run in `test_instruments.py`
against the whole battery — no leaked answer keys, unique probe ids, Score
levels within 2-10, and so on cover this module for free. What's tested here
is specific to this module: the hand-built categorization stimulus actually
has the logical structure its docstring claims, every `_estimate` probe has
a same-named non-estimate counterpart, and every benchmark the module's
docstrings point to actually exists.
"""

from __future__ import annotations

import re

from jevbench.benchmarks import BENCHMARKS
from jevbench.instruments.followup import categorization, probes
from jevbench.schema import Choice

PROBES = probes()
BY_ID = {p.probe_id: p for p in PROBES}


def _features(description: str) -> tuple[str, ...]:
    return tuple(
        part.split(": ")[1].rstrip(".") for part in description.split(". ") if ": " in part
    )


def test_probe_count_and_instruments() -> None:
    assert len(PROBES) == 18
    instruments = {p.instrument for p in PROBES}
    assert instruments == {
        "moral_typecasting",
        "moral_typecasting_estimate",
        "position_power",
        "position_power_estimate",
        "choosing_rejecting",
        "choosing_rejecting_estimate",
        "categorization",
        "categorization_estimate",
        "incidental_anchors",
        "incidental_anchors_estimate",
    }


def test_every_estimate_probe_has_a_response_counterpart() -> None:
    estimate_ids = [p.probe_id for p in PROBES if p.probe_id.endswith("_estimate")]
    assert estimate_ids, "expected at least one estimate probe"
    for eid in estimate_ids:
        base = eid[: -len("_estimate")]
        assert base in BY_ID, f"{eid} has no response-condition counterpart {base!r}"
        assert BY_ID[base].instrument != BY_ID[eid].instrument, (
            f"{base} and {eid} must be distinct instruments so they can be told apart in results"
        )


def test_score_estimate_probes_reuse_the_same_criteria_as_the_response_probe() -> None:
    """Amendment 2: mean-type items keep one primitive/criteria across elicitations."""
    for base_id in ("moral_typecasting_man_commits", "position_power_long_line"):
        base = BY_ID[base_id]
        est = BY_ID[f"{base_id}_estimate"]
        assert base.question.criteria == est.question.criteria


def test_choice_estimate_probes_reuse_the_same_options_as_the_response_probe() -> None:
    """Incidental anchors is a mean-type Choice item, not a Noul: same fix applies."""
    for base_id in ("incidental_anchor_p97", "incidental_anchor_p17"):
        base = BY_ID[base_id]
        est = BY_ID[f"{base_id}_estimate"]
        assert isinstance(base.question, Choice)
        assert isinstance(est.question, Choice)
        assert base.question.criteria == est.question.criteria


def test_proportion_type_estimates_are_noul_not_choice() -> None:
    """Shafir and Norenzayan are proportion-type: estimate targets one named option."""
    for eid in ("shafir_award_estimate", "shafir_deny_estimate", "norenzayan_belongs_to_estimate"):
        assert BY_ID[eid].question.kind == "noul"


def test_every_referenced_benchmark_exists() -> None:
    """Every benchmark key named in the module's docstrings must resolve."""
    import jevbench.instruments.followup as mod

    text = "\n".join(
        fn.__doc__ or ""
        for fn in (
            mod.moral_typecasting,
            mod.position_and_power,
            mod.choosing_vs_rejecting,
            mod.categorization,
            mod.incidental_anchors,
        )
    )
    # Docstrings write these as e.g. `moral_typecasting_responsibility_{man,baby}`.
    keys: set[str] = set()
    for m in re.finditer(r"`([a-z0-9_]+)\{([a-z0-9,]+)\}([a-z0-9_]*)`", text):
        prefix, alts, suffix = m.groups()
        keys.update(f"{prefix}{alt}{suffix}" for alt in alts.split(","))
    for m in re.finditer(r"`([a-z][a-z0-9_]{5,})`", text):
        key = m.group(1)
        if key in BENCHMARKS:
            keys.add(key)
    assert keys, "expected at least one benchmark reference to check"
    missing = keys - set(BENCHMARKS)
    assert not missing, f"docstrings reference benchmarks that don't exist: {sorted(missing)}"


def test_shafir_options_match_the_ml2_protocol_wording() -> None:
    award = BY_ID["shafir_award"]
    deny = BY_ID["shafir_deny"]
    assert award.question.criteria == deny.question.criteria
    extreme = award.question.criteria["parent_b"]
    for trait in (
        "above-average income",
        "close relationship",
        "active social life",
        "work-related travel",
        "health problems",
    ):
        assert trait in extreme, f"{trait!r} missing from the extreme-parent description"
    average = award.question.criteria["parent_a"]
    for trait in ("average income", "average health", "average working hours", "rapport"):
        assert trait in average, f"{trait!r} missing from the average-parent description"


def test_categorization_stimulus_matches_its_documented_structure() -> None:
    """The docstring claims: Group 1 shares exactly one feature with the target and
    each other; Group 2 shares no feature with all five, but overlaps the target by
    3/2/2/2 features. Both are load-bearing claims about a hand-built stimulus, so
    they're checked directly rather than trusted."""
    probe = categorization()[0]
    target = _features(probe.state["target"])
    group1 = [_features(m) for m in probe.state["group_1"]]
    group2 = [_features(m) for m in probe.state["group_2"]]

    assert len(group1) == len(group2) == 4
    assert len(set(group1)) == 4, "Group 1 members must be pairwise distinct"
    assert len(set(group2)) == 4, "Group 2 members must be pairwise distinct"

    # Group 1: exactly one dimension is uniform across target + all four members.
    uniform_dims = [i for i in range(4) if len({target[i], *[m[i] for m in group1]}) == 1]
    assert uniform_dims == [0], "Group 1's rule must be exactly one feature (colour)"

    # Group 2: no dimension is uniform across target + all four members.
    uniform_dims_g2 = [i for i in range(4) if len({target[i], *[m[i] for m in group2]}) == 1]
    assert uniform_dims_g2 == [], "Group 2 must have no usable classification rule"

    # Group 2's overlap with the target is 3, 2, 2, 2 — family resemblance, not a rule.
    overlaps = sorted(
        (sum(1 for a, b in zip(target, m, strict=True) if a == b) for m in group2), reverse=True
    )
    assert overlaps == [3, 2, 2, 2]


def test_categorization_options_name_the_two_groups() -> None:
    probe = BY_ID["norenzayan_belongs_to"]
    assert set(probe.question.criteria) == {"group_1", "group_2"}
    assert probe.meta["rule_based_option"] == "group_1"
