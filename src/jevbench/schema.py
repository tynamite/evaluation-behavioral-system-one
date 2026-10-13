"""Typed request/response objects for the System One decision API.

Jev exposes exactly three question primitives. Every probe in this project is
expressed as one of them:

    Choice — pick one of N labelled options (one-of-N, N <= 255)
    Score  — place the state on an ordered rubric of 2..10 levels
    Noul   — the calibrated probability that a single statement is true

The important property for this project is that all three return a *probability
distribution*, not just a point answer. Conventional LLM-psychology work has to
approximate a response distribution by resampling the same prompt many times at
temperature > 0, which conflates decoding noise with genuine response
uncertainty. Here the distribution is read directly, in one call.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Literal

QuestionKind = Literal["choice", "score", "noul"]


@dataclass(frozen=True, slots=True)
class Choice:
    """One-of-N selection. `criteria` maps option key -> description of that option."""

    instructions: str
    criteria: dict[str, str]

    kind: QuestionKind = "choice"

    def to_payload(self) -> dict[str, Any]:
        return {
            "type": "choice",
            "instructions": self.instructions,
            "criteria": dict(self.criteria),
        }


@dataclass(frozen=True, slots=True)
class Score:
    """Ordered rubric. `criteria` is an ordered list of 2..10 level descriptions."""

    instructions: str
    criteria: list[str]

    kind: QuestionKind = "score"

    def __post_init__(self) -> None:
        if not 2 <= len(self.criteria) <= 10:
            raise ValueError(f"Score needs 2..10 levels, got {len(self.criteria)}")

    def to_payload(self) -> dict[str, Any]:
        return {"type": "score", "instructions": self.instructions, "criteria": list(self.criteria)}


@dataclass(frozen=True, slots=True)
class Noul:
    """Probability that a statement is true. Returns a bare float in [0, 1]."""

    instructions: str
    criteria: dict[str, str] | None = None

    kind: QuestionKind = "noul"

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"type": "noul", "instructions": self.instructions}
        if self.criteria:
            payload["criteria"] = dict(self.criteria)
        return payload


Question = Choice | Score | Noul


@dataclass(slots=True)
class Answer:
    """A single answer, normalised across backends.

    `probabilities` is the object of interest throughout this project; `value` is
    retained only for reporting and is never used as the unit of analysis.
    """

    qid: str
    kind: QuestionKind
    value: str | float
    probabilities: dict[str, float] = field(default_factory=dict)
    confidence: float | None = None
    legend: dict[str, Any] | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def parse(cls, qid: str, obj: dict[str, Any]) -> Answer:
        kind = obj.get("type")
        if kind == "noul":
            p = float(obj["noul"])
            if not (math.isfinite(p) and 0.0 <= p <= 1.0):
                raise ValueError(f"Answer to {qid!r} has a Noul probability outside [0, 1]: {p}")
            # Express a Noul as an explicit two-point distribution so that every
            # answer in the project has the same shape downstream.
            return cls(
                qid=qid,
                kind="noul",
                value=p,
                probabilities={"true": p, "false": 1.0 - p},
                confidence=abs(p - 0.5) * 2.0,
                raw=obj,
            )
        if kind == "choice":
            return cls(
                qid=qid,
                kind="choice",
                value=str(obj["choice"]),
                probabilities=_checked(
                    qid, {str(k): float(v) for k, v in (obj.get("probabilities") or {}).items()}
                ),
                confidence=_opt_float(obj.get("confidence")),
                raw=obj,
            )
        if kind == "score":
            return cls(
                qid=qid,
                kind="score",
                value=float(obj["score"]),
                probabilities=_checked(
                    qid, {str(k): float(v) for k, v in (obj.get("probabilities") or {}).items()}
                ),
                confidence=_opt_float(obj.get("confidence")),
                legend=obj.get("legend"),
                raw=obj,
            )
        raise ValueError(f"Unrecognised answer type {kind!r} for question {qid!r}")


def distribution_problem(
    probs: dict[str, float], allowed: set[str] | frozenset[str] | None = None
) -> str | None:
    """Why `probs` is not a usable answer distribution, or None if it is.

    A reply can arrive without error and still carry nothing to analyse: no
    probabilities, negative or non-finite ones, no mass at all, or keys that
    are not the question's options. Averaging such a reply in would corrupt
    the distribution it joins, so it is rejected rather than normalised.
    """
    if not probs:
        return "no probabilities"
    values = list(probs.values())
    if not all(isinstance(v, (int, float)) and math.isfinite(v) and v >= 0 for v in values):
        return "a probability that is negative or not a finite number"
    if sum(values) <= 0:
        return "probabilities that sum to zero"
    if allowed is not None and (unknown := set(probs) - set(allowed)):
        return f"keys that are not options: {sorted(unknown)[:3]}"
    return None


def allowed_keys(question: Choice | Score | Noul) -> frozenset[str]:
    """The keys an answer to `question` may put probability on."""
    if isinstance(question, Choice):
        return frozenset(question.criteria)
    if isinstance(question, Score):
        return frozenset(str(i) for i in range(len(question.criteria)))
    return frozenset({"true", "false"})


def _checked(qid: str, probs: dict[str, float]) -> dict[str, float]:
    if problem := distribution_problem(probs):
        raise ValueError(f"Answer to {qid!r} has {problem}")
    return probs


def _opt_float(v: Any) -> float | None:
    return None if v is None else float(v)


@dataclass(slots=True)
class DecisionResponse:
    """A whole `/systemone` response."""

    model: str
    answers: dict[str, Answer]
    usage: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def parse(cls, obj: dict[str, Any]) -> DecisionResponse:
        answers = {qid: Answer.parse(qid, a) for qid, a in (obj.get("answers") or {}).items()}
        return cls(
            model=str(obj.get("model", "")),
            answers=answers,
            usage=dict(obj.get("usage") or {}),
            raw=obj,
        )
