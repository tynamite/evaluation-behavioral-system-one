"""The parsing layer is where a silent scientific error would hide, so it is tested hard."""

from __future__ import annotations

import pytest

from jevbench.schema import Answer, Choice, DecisionResponse, Noul, Score


def test_choice_roundtrip() -> None:
    q = Choice(instructions="Pick.", criteria={"a": "A", "b": "B"})
    assert q.to_payload() == {
        "type": "choice",
        "instructions": "Pick.",
        "criteria": {"a": "A", "b": "B"},
    }


def test_score_rejects_out_of_range_levels() -> None:
    with pytest.raises(ValueError, match=r"2\.\.10 levels"):
        Score(instructions="x", criteria=["only one"])
    with pytest.raises(ValueError, match=r"2\.\.10 levels"):
        Score(instructions="x", criteria=[str(i) for i in range(11)])
    Score(instructions="x", criteria=["lo", "hi"])
    Score(instructions="x", criteria=[str(i) for i in range(10)])


def test_noul_omits_absent_criteria() -> None:
    assert "criteria" not in Noul(instructions="x").to_payload()
    assert Noul(instructions="x", criteria={"true": "t"}).to_payload()["criteria"] == {"true": "t"}


def test_noul_becomes_a_two_point_distribution() -> None:
    """Every answer must expose a distribution so downstream code has one shape."""
    a = Answer.parse("q", {"type": "noul", "noul": 0.75})
    assert a.probabilities == {"true": 0.75, "false": 0.25}
    assert a.value == 0.75
    assert a.confidence == pytest.approx(0.5)


def test_score_answer_keeps_legend_and_index_keys() -> None:
    a = Answer.parse(
        "q",
        {
            "type": "score",
            "score": 1.12,
            "legend": {"0": "Trivial", "1": "Easy", "2": "Moderate"},
            "probabilities": {"0": 0.17, "1": 0.59, "2": 0.24},
            "confidence": 0.62,
        },
    )
    assert a.kind == "score"
    assert a.legend is not None and a.legend["1"] == "Easy"
    assert sum(a.probabilities.values()) == pytest.approx(1.0)


def test_unknown_answer_type_raises() -> None:
    with pytest.raises(ValueError, match="Unrecognised answer type"):
        Answer.parse("q", {"type": "vibes", "value": 1})


def test_parses_a_real_api_response() -> None:
    """Captured verbatim from the live endpoint."""
    payload = {
        "model": "typesafe/jev-1.13-20260917",
        "answers": {
            "ball_cost": {
                "type": "choice",
                "choice": "$0.05",
                "probabilities": {"$0.10": 0.02, "$0.01": 0, "$0.05": 0.98},
                "confidence": 0.97,
            },
            "is_tricky": {"type": "noul", "noul": 0.93},
            "difficulty": {
                "type": "score",
                "score": 1.12,
                "legend": {
                    "0": "Trivial",
                    "1": "Easy",
                    "2": "Moderate",
                    "3": "Hard",
                    "4": "Very hard",
                },
                "probabilities": {"0": 0.17, "1": 0.59, "2": 0.2, "3": 0.04, "4": 0},
                "confidence": 0.62,
            },
        },
        "usage": {"input_tokens": 436, "output_tokens": 88, "cost": 0.000018312},
    }
    resp = DecisionResponse.parse(payload)
    assert resp.model == "typesafe/jev-1.13-20260917"
    assert resp.answers["ball_cost"].value == "$0.05"
    assert resp.answers["ball_cost"].probabilities["$0.05"] == 0.98
    assert resp.answers["is_tricky"].probabilities["true"] == 0.93
    assert resp.usage["cost"] == pytest.approx(1.8312e-05)
