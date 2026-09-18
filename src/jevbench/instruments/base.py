"""Probes, personas and the randomisation controls shared by every instrument."""

from __future__ import annotations

import random
from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from typing import Any

from ..schema import Choice, Noul, Question, Score


@dataclass(frozen=True, slots=True)
class Probe:
    """One unit of measurement: a scenario (`state`) plus one typed question."""

    probe_id: str
    instrument: str
    question: Question
    state: Any = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Persona:
    """The experimental manipulation.

    `neutral` is the control: the model is asked the item with no framing at
    all. `typical_human` is the condition of interest — it asks for the modal
    human response. `rational_agent` is the opposing anchor, asking for the
    game-theoretic or normatively correct answer. Contrasting all three
    separates 'what the model does by default' from 'what the model can
    represent about humans when asked', which a single condition cannot.
    """

    key: str
    label: str
    preamble: str


PERSONAS: dict[str, Persona] = {
    "neutral": Persona(
        key="neutral",
        label="Neutral (no framing)",
        preamble="",
    ),
    "typical_human": Persona(
        key="typical_human",
        label="As a typical human",
        preamble=(
            "Answer the way a typical human participant in a psychology or economics "
            "experiment would actually answer — not the textbook-correct answer, and "
            "not an idealised one. Give the response the average person would give."
        ),
    ),
    "antisocial": Persona(
        key="antisocial",
        label="Antisocial persona",
        preamble=(
            "Answer as someone high in the dark triad traits would answer: manipulative, "
            "callous, lacking remorse or empathy, cynical about other people's motives, "
            "and focused on their own advantage above others'. Respond the way that person "
            "would genuinely respond."
        ),
    ),
    "rational_agent": Persona(
        key="rational_agent",
        label="As a rational agent",
        preamble=(
            "Answer the way a perfectly rational, self-interested, payoff-maximising "
            "agent would answer, following normative decision theory and game-theoretic "
            "equilibrium reasoning."
        ),
    ),
}


def apply_persona(probe: Probe, persona: Persona) -> Probe:
    """Prepend the persona framing to the question's instructions.

    The framing goes in `instructions` rather than `state` so that the scenario
    itself is byte-identical across conditions; only the task framing varies.
    """
    if not persona.preamble:
        return probe
    q = probe.question
    new_instructions = f"{persona.preamble}\n\n{q.instructions}"
    # All three primitives carry `instructions`, so one replace covers every case.
    new_q: Question = replace(q, instructions=new_instructions)
    return replace(probe, question=new_q)


def permute_options(probe: Probe, rng: random.Random) -> Probe:
    """Shuffle the presentation order of a Choice's options.

    Humans show strong primacy/recency effects in forced-choice items. The docs
    state Jev evaluates each question in parallel and in isolation, which
    predicts *no* order effect; this control is what makes that prediction
    testable rather than assumed.
    """
    q = probe.question
    if not isinstance(q, Choice):
        return probe
    keys = list(q.criteria)
    rng.shuffle(keys)
    shuffled = {k: q.criteria[k] for k in keys}
    meta = {**probe.meta, "option_order": keys}
    return replace(probe, question=replace(q, criteria=shuffled), meta=meta)


LIKERT_5 = [
    "Very inaccurate",
    "Moderately inaccurate",
    "Neither accurate nor inaccurate",
    "Moderately accurate",
    "Very accurate",
]


def likert_item(
    probe_id: str,
    instrument: str,
    statement: str,
    *,
    trait: str,
    reverse: bool = False,
    levels: list[str] | None = None,
) -> Probe:
    """A standard self-report item rendered as a Score primitive."""
    return Probe(
        probe_id=probe_id,
        instrument=instrument,
        question=Score(
            instructions=(
                f"Describe how accurately this statement describes you: {statement!r} "
                f"Choose the level that fits best."
            ),
            criteria=list(levels or LIKERT_5),
        ),
        state={"statement": statement},
        meta={"trait": trait, "reverse": reverse, "n_levels": len(levels or LIKERT_5)},
    )


def binary_choice(
    probe_id: str,
    instrument: str,
    instructions: str,
    options: dict[str, str],
    *,
    state: Any = None,
    **meta: Any,
) -> Probe:
    return Probe(
        probe_id=probe_id,
        instrument=instrument,
        question=Choice(instructions=instructions, criteria=options),
        state=state,
        meta=meta,
    )


def noul_probe(
    probe_id: str, instrument: str, instructions: str, *, state: Any = None, **meta: Any
) -> Probe:
    return Probe(
        probe_id=probe_id,
        instrument=instrument,
        question=Noul(instructions=instructions),
        state=state,
        meta=meta,
    )


def collect(*groups: Iterable[Probe]) -> list[Probe]:
    out: list[Probe] = []
    for g in groups:
        out.extend(g)
    return out
