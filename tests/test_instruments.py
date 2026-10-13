"""Integrity checks on the battery itself.

A leaked answer key or a wrong `correct` field would quietly invalidate the
study while every other test still passed, so these assertions guard the
scientific content rather than the code paths.
"""

from __future__ import annotations

import random

from jevbench.instruments import PERSONAS, all_probes, apply_persona, permute_options
from jevbench.schema import Choice, Score

PROBES = all_probes()


def test_probe_ids_are_unique() -> None:
    ids = [p.probe_id for p in PROBES]
    assert len(ids) == len(set(ids))


def test_scored_items_name_an_option_that_exists() -> None:
    for p in PROBES:
        for field in ("correct", "lure"):
            expected = p.meta.get(field)
            if expected is None:
                continue
            assert isinstance(p.question, Choice)
            assert expected in p.question.criteria, f"{p.probe_id}: {field}={expected!r} missing"


def test_option_keys_never_leak_the_answer() -> None:
    """Keys must carry literal content, never an evaluative label."""
    banned = {"correct", "incorrect", "right", "wrong", "answer", "lure", "best", "true_answer"}
    for p in PROBES:
        if not isinstance(p.question, Choice):
            continue
        for key in p.question.criteria:
            assert key.strip().lower() not in banned, f"{p.probe_id} leaks via key {key!r}"


def test_score_items_are_within_the_primitive_limits() -> None:
    for p in PROBES:
        if isinstance(p.question, Score):
            assert 2 <= len(p.question.criteria) <= 10


def test_choice_items_are_within_the_primitive_limits() -> None:
    for p in PROBES:
        if isinstance(p.question, Choice):
            assert 2 <= len(p.question.criteria) <= 255, p.probe_id


def test_reverse_keyed_items_exist_for_every_big_five_trait() -> None:
    traits: dict[str, list[bool]] = {}
    for p in PROBES:
        if p.instrument == "mini_ipip":
            traits.setdefault(str(p.meta["trait"]), []).append(bool(p.meta["reverse"]))
    assert set(traits) == {
        "extraversion",
        "agreeableness",
        "conscientiousness",
        "neuroticism",
        "openness",
    }
    for trait, flags in traits.items():
        assert any(flags), f"{trait} has no reverse-keyed item"
        assert not all(flags), f"{trait} is entirely reverse-keyed"


def test_persona_changes_only_the_instructions() -> None:
    probe = next(p for p in PROBES if isinstance(p.question, Choice))
    out = apply_persona(probe, PERSONAS["typical_human"])
    assert out.state == probe.state, "the scenario must be byte-identical across conditions"
    assert out.question.criteria == probe.question.criteria
    assert probe.question.instructions in out.question.instructions
    assert out.question.instructions != probe.question.instructions


def test_neutral_persona_is_a_true_no_op() -> None:
    probe = PROBES[0]
    assert apply_persona(probe, PERSONAS["neutral"]) == probe


def test_permutation_preserves_the_option_set() -> None:
    probe = next(
        p for p in PROBES if isinstance(p.question, Choice) and len(p.question.criteria) > 3
    )
    out = permute_options(probe, random.Random(1))
    assert isinstance(out.question, Choice)
    assert out.question.criteria == probe.question.criteria, "same mapping"
    assert set(out.meta["option_order"]) == set(probe.question.criteria)


def test_permutation_is_seed_deterministic() -> None:
    probe = next(
        p for p in PROBES if isinstance(p.question, Choice) and len(p.question.criteria) > 3
    )
    a = permute_options(probe, random.Random(42)).meta["option_order"]
    b = permute_options(probe, random.Random(42)).meta["option_order"]
    assert a == b


def test_reasoning_items_declare_a_step_count() -> None:
    items = [p for p in PROBES if p.instrument == "fluid_reasoning"]
    assert items
    for p in items:
        assert isinstance(p.meta.get("steps"), int) and p.meta["steps"] >= 1


def test_module_filter_rejects_unknown_names() -> None:
    import pytest

    with pytest.raises(ValueError, match="Unknown module"):
        all_probes(["not_a_module"])


def test_trust_returns_keep_every_focal_amount() -> None:
    # With $10 sent and $30 received: $10 lets the sender break even, $15 is
    # half, $20 equalises payoffs. An earlier $3 grid had none of $10 or $20.
    probes = {p.probe_id: p for p in all_probes(["games"])}
    for sent in (2, 5, 10):
        q = probes[f"trust_return_{sent}"].question
        assert isinstance(q, Choice)
        received = sent * 3
        keys = set(q.criteria)
        assert {f"${sent}", f"${received // 2}", f"${received}", "$0"} <= keys
        assert len(keys) <= 26  # the decisions route's cap on Choice options
    assert {"$10", "$15", "$20"} <= set(probes["trust_return_10"].question.criteria)


def test_estimate_items_are_asked_without_a_persona() -> None:
    from jevbench.instruments import asked_under

    estimates = [p for p in all_probes(["followup"]) if p.probe_id.endswith("_estimate")]
    assert len(estimates) == 25
    for p in estimates:
        assert asked_under(p, "neutral")
        assert not any(asked_under(p, k) for k in PERSONAS if k != "neutral")
    own = next(p for p in all_probes(["followup"]) if not p.probe_id.endswith("_estimate"))
    assert all(asked_under(own, k) for k in PERSONAS)
