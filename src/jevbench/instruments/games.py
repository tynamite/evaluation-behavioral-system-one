"""Canonical behavioural-economics games.

Every allocation decision is posed as a Choice over the full set of integer
allocations, so the returned `probabilities` give the model's whole allocation
distribution in a single call. Human data for these games is reported as a
distribution (the dictator game's characteristic spikes at 0 and at half, for
instance), so a distribution is the right object to compare against — an
argmax would discard exactly the structure of interest.
"""

from __future__ import annotations

from .base import Probe, binary_choice

PIE = 10


def _return_grid(received: int) -> list[int]:
    """The amounts a trustee can return.

    Whole dollars up to $15. For $30 that would be 31 options, more than one
    route accepts (26), so it goes in $2 steps plus $15: every focal return
    stays selectable — $10 (the sender breaks even), $15 (half) and $20
    (equal payoffs). The first runs used $3 steps, which had neither $10 nor
    $20; trust_return_10 was re-run with this grid for every model on 13 Oct 2026.
    """
    if received <= 15:
        return list(range(received + 1))
    return sorted({*range(0, received + 1, 2), received // 2})


def _money_options(lo: int, hi: int, unit: str = "$") -> dict[str, str]:
    return {f"{unit}{v}": f"Keep {unit}{PIE - v} and give {unit}{v}" for v in range(lo, hi + 1)}


def dictator() -> list[Probe]:
    """Forsythe et al. (1994). No strategic element — pure other-regarding preference."""
    state = {
        "game": "dictator",
        "endowment": f"${PIE}",
        "rules": (
            f"You have been given ${PIE}. You must decide how much of it, if any, to give "
            "to an anonymous other participant. The other participant has no say and cannot "
            "respond in any way. Whatever you do not give, you keep. The decision is "
            "one-shot and anonymous."
        ),
    }
    return [
        binary_choice(
            probe_id="dictator_allocation",
            instrument="dictator",
            instructions=f"How much of the ${PIE} do you give to the other participant?",
            options={f"${v}": f"Give ${v}, keep ${PIE - v}" for v in range(PIE + 1)},
            state=state,
            scoring="allocation",
            pie=PIE,
        )
    ]


def ultimatum() -> list[Probe]:
    """Güth et al. (1982). Proposer offer plus the full responder rejection curve."""
    proposer_state = {
        "game": "ultimatum",
        "role": "proposer",
        "endowment": f"${PIE}",
        "rules": (
            f"You have ${PIE} to split with an anonymous responder. You propose a split. "
            "If the responder accepts, you both receive your shares. If the responder "
            "rejects, you both receive nothing. One-shot and anonymous."
        ),
    }
    probes = [
        binary_choice(
            probe_id="ultimatum_offer",
            instrument="ultimatum_proposer",
            instructions=f"How much of the ${PIE} do you offer to the responder?",
            options={f"${v}": f"Offer ${v}, keep ${PIE - v}" for v in range(PIE + 1)},
            state=proposer_state,
            scoring="allocation",
            pie=PIE,
        )
    ]
    for offer in range(0, PIE + 1):
        probes.append(
            binary_choice(
                probe_id=f"ultimatum_respond_{offer}",
                instrument="ultimatum_responder",
                instructions=(
                    f"The proposer offers you ${offer}, keeping ${PIE - offer}. "
                    "Do you accept or reject? If you reject, you both get nothing."
                ),
                options={
                    "accept": f"Accept: you get ${offer}, they get ${PIE - offer}",
                    "reject": "Reject: you both get $0",
                },
                state={
                    "game": "ultimatum",
                    "role": "responder",
                    "offer_to_you": f"${offer}",
                    "proposer_keeps": f"${PIE - offer}",
                    "rules": (
                        "If you reject, both players receive nothing. One-shot and anonymous."
                    ),
                },
                scoring="binary",
                offer=offer,
                cooperative_option="accept",
            )
        )
    return probes


def trust() -> list[Probe]:
    """Berg, Dickhaut & McCabe (1995). Sender trust and trustee reciprocity."""
    probes = [
        binary_choice(
            probe_id="trust_send",
            instrument="trust_sender",
            instructions=f"How much of your ${PIE} do you send to the trustee?",
            options={
                f"${v}": f"Send ${v} (they receive ${v * 3}), keep ${PIE - v}"
                for v in range(PIE + 1)
            },
            state={
                "game": "trust",
                "role": "sender",
                "rules": (
                    f"You have ${PIE}. Any amount you send to an anonymous trustee is tripled "
                    "on arrival. The trustee then decides how much, if any, to return to you. "
                    "The trustee is under no obligation to return anything. One-shot and anonymous."
                ),
            },
            scoring="allocation",
            pie=PIE,
        )
    ]
    for sent in (2, 5, 10):
        received = sent * 3
        probes.append(
            binary_choice(
                probe_id=f"trust_return_{sent}",
                instrument="trust_trustee",
                instructions=(
                    f"The sender sent you ${sent}, which was tripled to ${received}. "
                    f"How much of the ${received} do you return?"
                ),
                options={
                    f"${v}": f"Return ${v}, keep ${received - v}" for v in _return_grid(received)
                },
                state={
                    "game": "trust",
                    "role": "trustee",
                    "sender_sent": f"${sent}",
                    "you_received": f"${received}",
                    "rules": "You are under no obligation to return anything. One-shot and anonymous.",
                },
                scoring="allocation",
                pie=received,
                sent=sent,
            )
        )
    return probes


def public_goods() -> list[Probe]:
    """Fehr & Gächter (2000). Round 1 contribution, plus conditional cooperation."""
    base_rules = (
        f"You and 3 other participants each have ${PIE}. Each of you privately decides how "
        "much to contribute to a common project. The total contributed is multiplied by 2 "
        "and split equally among all 4 players, regardless of what anyone contributed. "
        "Whatever you do not contribute, you keep."
    )
    probes = [
        binary_choice(
            probe_id="pgg_round1",
            instrument="public_goods",
            instructions=f"How much of your ${PIE} do you contribute to the common project?",
            options={f"${v}": f"Contribute ${v}, keep ${PIE - v}" for v in range(PIE + 1)},
            state={"game": "public_goods", "round": 1, "rules": base_rules},
            scoring="allocation",
            pie=PIE,
            condition="round1",
        )
    ]
    for label, others in (("low", 1), ("mid", 5), ("high", 9)):
        probes.append(
            binary_choice(
                probe_id=f"pgg_conditional_{label}",
                instrument="public_goods_conditional",
                instructions=(
                    f"The other three players each contributed ${others} last round. "
                    "How much do you contribute this round?"
                ),
                options={f"${v}": f"Contribute ${v}, keep ${PIE - v}" for v in range(PIE + 1)},
                state={
                    "game": "public_goods",
                    "round": 2,
                    "others_contributed": f"${others} each",
                    "rules": base_rules,
                },
                scoring="allocation",
                pie=PIE,
                others_contributed=others,
                condition=f"conditional_{label}",
            )
        )
    return probes


def prisoners_dilemma() -> list[Probe]:
    """One-shot and history-conditioned prisoner's dilemma."""
    payoffs = (
        "If you both cooperate, you each get $3. If you both defect, you each get $1. "
        "If you cooperate and they defect, you get $0 and they get $5. "
        "If you defect and they cooperate, you get $5 and they get $0."
    )
    options = {
        "cooperate": "Cooperate",
        "defect": "Defect",
    }
    probes = [
        binary_choice(
            probe_id="pd_oneshot",
            instrument="prisoners_dilemma",
            instructions="Do you cooperate or defect?",
            options=options,
            state={
                "game": "prisoners_dilemma",
                "rounds": "single round, anonymous, no future interaction",
                "payoffs": payoffs,
            },
            scoring="binary",
            cooperative_option="cooperate",
            condition="one_shot",
        )
    ]
    histories = {
        "after_cooperation": "In the previous 3 rounds, the other player cooperated every time.",
        "after_defection": "In the previous 3 rounds, the other player defected every time.",
    }
    for key, history in histories.items():
        probes.append(
            binary_choice(
                probe_id=f"pd_{key}",
                instrument="prisoners_dilemma",
                instructions="Do you cooperate or defect this round?",
                options=options,
                state={
                    "game": "prisoners_dilemma",
                    "rounds": "round 4 of an ongoing series",
                    "history": history,
                    "payoffs": payoffs,
                },
                scoring="binary",
                cooperative_option="cooperate",
                condition=key,
            )
        )
    return probes


def probes() -> list[Probe]:
    return [
        *dictator(),
        *ultimatum(),
        *trust(),
        *public_goods(),
        *prisoners_dilemma(),
    ]
