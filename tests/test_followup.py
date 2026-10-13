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
from jevbench.instruments import all_probes
from jevbench.instruments.followup import categorization, probes, reused_estimates
from jevbench.schema import Choice, Noul

PROBES = probes()
BY_ID = {p.probe_id: p for p in PROBES}
ALL_BY_ID = {p.probe_id: p for p in all_probes(None)}


def _features(description: str) -> tuple[str, ...]:
    return tuple(
        part.split(": ")[1].rstrip(".") for part in description.split(". ") if ": " in part
    )


def test_probe_count_and_instruments() -> None:
    assert len(PROBES) == 40
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
        "knobe",
        "knobe_estimate",
        "trolley",
        "trolley_estimate",
        "false_consensus",
        "false_consensus_estimate",
        # Estimates for the items reused from the first project; the items
        # themselves are asked in their own modules.
        "allais_estimate",
        "base_rate_estimate",
        "conjunction_estimate",
        "crt_estimate",
        "framing_estimate",
        "sunk_cost_estimate",
    }


def test_every_estimate_probe_has_a_response_counterpart() -> None:
    estimate_ids = [p.probe_id for p in PROBES if p.probe_id.endswith("_estimate")]
    assert estimate_ids, "expected at least one estimate probe"
    for eid in estimate_ids:
        base = eid[: -len("_estimate")]
        assert base in ALL_BY_ID, f"{eid} has no response-condition counterpart {base!r}"
        assert ALL_BY_ID[base].instrument != BY_ID[eid].instrument, (
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
    """Proportion-type items (a Choice whose human number is 'what fraction chose X')
    get a Noul estimate targeting one named option, not a reworded Choice."""
    for eid in (
        "shafir_award_estimate",
        "shafir_deny_estimate",
        "norenzayan_belongs_to_estimate",
        "knobe_harm_estimate",
        "knobe_help_estimate",
        "trolley_switch_estimate",
        "trolley_push_estimate",
    ):
        assert BY_ID[eid].question.kind == "noul"


def test_knobe_and_trolley_estimates_target_the_named_option() -> None:
    for eid in ("knobe_harm_estimate", "knobe_help_estimate"):
        assert BY_ID[eid].meta["target"] == "intentional"
    for eid in ("trolley_switch_estimate", "trolley_push_estimate"):
        assert BY_ID[eid].meta["target"] == "permissible"


def test_false_consensus_own_and_simulate_are_already_noul() -> None:
    """Unlike this module's other items, false_consensus's published DV is itself a
    percentage estimate, so own/simulate need no Choice-to-Noul conversion at all."""
    for pid in ("false_consensus_wearer", "false_consensus_nonwearer"):
        assert isinstance(BY_ID[pid].question, Noul)
        assert isinstance(BY_ID[f"{pid}_estimate"].question, Noul)


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
            mod.intentional_side_effects,
            mod.trolley_dilemma,
            mod.false_consensus,
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
    """The docstring claims: one feature is common to Group 1 and the target; no
    feature is common to Group 2 and the target, which overlap it by 3/2/2/2; and
    all eight exemplars are distinct, with no hint in the prompt. These are
    load-bearing claims about a hand-built stimulus, so they're checked directly."""
    probe = categorization()[0]
    target = _features(probe.state["target"])
    group1 = [_features(m) for m in probe.state["group_1"]]
    group2 = [_features(m) for m in probe.state["group_2"]]

    assert len(group1) == len(group2) == 4
    assert len(set(group1)) == 4, "Group 1 members must be pairwise distinct"
    assert len(set(group2)) == 4, "Group 2 members must be pairwise distinct"
    assert not set(group1) & set(group2), "no exemplar may appear in both groups"
    assert set(probe.state) == {"task", "target", "group_1", "group_2"}, "no cue in the prompt"

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


def test_knobe_vignette_wording_matches_the_original() -> None:
    """Checked against secondary sources reproducing Knobe (2003)'s exact text."""
    harm = BY_ID["knobe_harm"].state["scenario"]
    helped = BY_ID["knobe_help"].state["scenario"]
    for scenario in (harm, helped):
        assert "vice-president" in scenario
        assert "as much profit as I can" in scenario
    assert "harm the environment" in harm and "was harmed" in harm
    assert "help the environment" in helped and "was helped" in helped


def test_trolley_switch_and_push_differ_only_in_the_mechanism() -> None:
    """The switch/push asymmetry is the whole point of the item: both vignettes must
    describe the same five-vs-one trade-off, differing only in how the one dies."""
    switch = BY_ID["trolley_switch"].state["scenario"]
    push = BY_ID["trolley_push"].state["scenario"]
    for scenario in (switch, push):
        assert "five people" in scenario
    assert "switch" in switch and "footbridge" not in switch
    assert "footbridge" in push and "push the stranger" in push


def test_false_consensus_frames_predict_more_of_own_choice() -> None:
    """Sanity check against the benchmark values themselves: wearers should predict a
    higher wear-rate than non-wearers (0.614 vs 0.304) -- the false consensus effect."""
    wearer_bench = BENCHMARKS["false_consensus_wearer_predicts_wear"]
    nonwearer_bench = BENCHMARKS["false_consensus_nonwearer_predicts_wear"]
    assert wearer_bench.value > nonwearer_bench.value
    assert BY_ID["false_consensus_wearer"].state["frame"] == "Suppose you agree to wear the sign."
    assert (
        BY_ID["false_consensus_nonwearer"].state["frame"] == "Suppose you refuse to wear the sign."
    )


def test_reused_estimates_name_the_option_the_benchmark_counts() -> None:
    """Section 8.1: the population question asks for the share choosing one named option."""
    for est in reused_estimates():
        item = ALL_BY_ID[est.probe_id.removesuffix("_estimate")]
        assert isinstance(item.question, Choice) and isinstance(est.question, Noul)
        target = est.meta["target"]
        criteria = item.question.criteria
        assert isinstance(criteria, dict) and target in criteria
        assert f'"{criteria[target]}"' in est.question.instructions
        assert est.state["options"] == criteria
        assert est.meta["asks_for"] == "proportion"
