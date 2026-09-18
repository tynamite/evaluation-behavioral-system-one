"""Risk and time preference elicitation via multiple price lists."""

from __future__ import annotations

from .base import Probe, binary_choice


def holt_laury() -> list[Probe]:
    """Holt & Laury (2002) 10-row lottery menu.

    A risk-neutral agent switches from the safe to the risky lottery at row 5.
    Switching later implies risk aversion; earlier implies risk seeking. The
    number of safe choices is a standard, directly comparable statistic.
    """
    probes: list[Probe] = []
    for row in range(1, 11):
        p = row / 10.0
        probes.append(
            binary_choice(
                probe_id=f"holt_laury_{row:02d}",
                instrument="holt_laury",
                instructions="Which lottery do you choose?",
                options={
                    "option_a": (
                        f"{p:.0%} chance of $2.00, {1 - p:.0%} chance of $1.60"
                        if p < 1
                        else "$2.00 for certain"
                    ),
                    "option_b": (
                        f"{p:.0%} chance of $3.85, {1 - p:.0%} chance of $0.10"
                        if p < 1
                        else "$3.85 for certain"
                    ),
                },
                state={
                    "task": "lottery choice",
                    "row": row,
                    "probability_of_high_payoff": p,
                },
                scoring="binary",
                row=row,
                p_high=p,
                safe_option="option_a",
            )
        )
    return probes


def discounting() -> list[Probe]:
    """Delay-discounting multiple price list, plus a present-bias pair.

    The two `present_bias` probes share an identical 30-day delay and identical
    amounts; only the front-end delay differs. An exponential discounter must
    answer them the same way. A hyperbolic discounter — which is what humans
    reliably are — flips.
    """
    probes: list[Probe] = []
    for delay_days in (7, 30, 180):
        for later in (52, 60, 75, 100):
            probes.append(
                binary_choice(
                    probe_id=f"discount_{delay_days}d_{later}",
                    instrument="discounting",
                    instructions="Which payment do you choose?",
                    options={
                        "sooner": "$50 today",
                        "later": f"${later} in {delay_days} days",
                    },
                    state={"task": "intertemporal choice", "delay_days": delay_days},
                    scoring="binary",
                    delay_days=delay_days,
                    later_amount=later,
                    sooner_amount=50,
                    patient_option="later",
                )
            )
    probes.append(
        binary_choice(
            probe_id="present_bias_now",
            instrument="present_bias",
            instructions="Which payment do you choose?",
            options={"sooner": "$100 today", "later": "$110 in 30 days"},
            state={"task": "intertemporal choice", "front_end_delay_days": 0},
            scoring="binary",
            front_end_delay=0,
            patient_option="later",
        )
    )
    probes.append(
        binary_choice(
            probe_id="present_bias_delayed",
            instrument="present_bias",
            instructions="Which payment do you choose?",
            options={"sooner": "$100 in 12 months", "later": "$110 in 12 months and 30 days"},
            state={"task": "intertemporal choice", "front_end_delay_days": 365},
            scoring="binary",
            front_end_delay=365,
            patient_option="later",
        )
    )
    return probes


def probes() -> list[Probe]:
    return [*holt_laury(), *discounting()]
