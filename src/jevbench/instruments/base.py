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
    game-theoretic or normatively correct answer, and `antisocial` asks for a
    dark-triad persona. Contrasting them separates 'what the model does by
    default' from 'what the model can represent about humans when asked',
    which a single condition cannot.

    `typical_human` also says "not the textbook-correct answer", which steers
    away from the normative answer on items that have one, so part of any move
    toward people under it may be compliance rather than knowledge of human
    error. `typical_human_plain` asks the same thing without that clause, so the
    two can be told apart. It was added after the committed runs (18 Sep
    and 12 Oct 2026), which do not include it.
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
    "typical_human_plain": Persona(
        key="typical_human_plain",
        label="As a typical human (no steer)",
        preamble=(
            "Answer the way a typical human participant in a psychology or economics "
            "experiment would actually answer. Give the response the average person "
            "would give."
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


def score_probe(
    probe_id: str,
    instrument: str,
    instructions: str,
    criteria: list[str],
    *,
    state: Any = None,
    **meta: Any,
) -> Probe:
    """A rating-scale item about a scenario, as opposed to a self-report trait.

    `likert_item` above is specifically the "describe how accurately this
    statement describes you" wording used by the personality inventories; this
    is the general case, used where the instructions are scenario-specific
    (rate how responsible someone is, how powerful someone appears, ...).
    """
    return Probe(
        probe_id=probe_id,
        instrument=instrument,
        question=Score(instructions=instructions, criteria=list(criteria)),
        state=state,
        meta=meta,
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
    # A System One model's P(true) can stand for "what proportion of people
    # said yes?", but a chat model asked that and told to reply true or false
    # has no way to give a number; analysis leaves those items out of the chat
    # arm rather than read a majority vote as an estimate.
    meta.setdefault("asks_for", "proportion" if "proportion" in instructions.lower() else "truth")
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
