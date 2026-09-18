"""Iterated-reasoning games, where the depth of strategic thinking is the measure."""

from __future__ import annotations

from .base import Probe, binary_choice


def beauty_contest() -> list[Probe]:
    """Keynesian p-beauty contest (Nagel 1995).

    The unique Nash equilibrium is 0, reached only by iterating best responses
    to convergence. Humans stop after one or two steps, producing the famous
    spikes at 33 (one step from a uniform prior) and 22 (two steps). Because
    Choice returns the whole distribution over 0..100, the model's own spikes
    are directly comparable to the human histogram.
    """
    options = {str(n): f"Choose {n}" for n in range(101)}
    return [
        binary_choice(
            probe_id="beauty_contest_2_3",
            instrument="beauty_contest",
            instructions="Which number do you choose?",
            options=options,
            state={
                "game": "guessing game",
                "rules": (
                    "You and many other players each simultaneously choose a number between "
                    "0 and 100. The winner is whoever is closest to two-thirds of the average "
                    "of all numbers chosen. You do not know the other players."
                ),
            },
            scoring="numeric_choice",
            equilibrium=0,
            level1=33,
            level2=22,
        )
    ]


def money_request() -> list[Probe]:
    """11-20 money request game (Arad & Rubinstein 2012). A clean level-k ladder."""
    options = {
        str(n): (
            f"Request {n}" + (" (the largest amount, but never earns the bonus)" if n == 20 else "")
        )
        for n in range(11, 21)
    }
    return [
        binary_choice(
            probe_id="money_request_11_20",
            instrument="money_request",
            instructions="How much do you request?",
            options=options,
            state={
                "game": "11-20 money request",
                "rules": (
                    "You and another player each request an amount of money between 11 and 20 "
                    "shekels. You receive the amount you request. You receive an additional "
                    "20 shekels if you request exactly one shekel less than the other player."
                ),
            },
            scoring="numeric_choice",
            level0=20,
            level1=19,
            level2=18,
            level3=17,
        )
    ]


def probes() -> list[Probe]:
    return [*beauty_contest(), *money_request()]
