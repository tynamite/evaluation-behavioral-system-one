"""Cognitive Reflection Test (Frederick 2005; extended items from Toplak et al. 2014).

The CRT is the keystone instrument of this study. Each item is built so that a
fast, associative response yields a specific *wrong* answer (the "lure") while
the correct answer requires suppressing it. That is precisely the System 1 /
System 2 distinction a self-described "System One" model invites.

Option keys are the literal answers, never labels like "correct" or "lure", so
that nothing in the payload signals which option is right.
"""

from __future__ import annotations

from .base import Probe, binary_choice

# (id, problem text, options, correct answer, intuitive lure)
_ITEMS: list[tuple[str, str, dict[str, str], str, str]] = [
    (
        "crt_bat_ball",
        "A bat and a ball cost $1.10 in total. The bat costs $1.00 more than the ball. "
        "How much does the ball cost?",
        {"$0.05": "Five cents", "$0.10": "Ten cents", "$0.01": "One cent", "$1.00": "One dollar"},
        "$0.05",
        "$0.10",
    ),
    (
        "crt_widgets",
        "If it takes 5 machines 5 minutes to make 5 widgets, how long would it take "
        "100 machines to make 100 widgets?",
        {
            "5 minutes": "Five minutes",
            "100 minutes": "One hundred minutes",
            "20 minutes": "Twenty minutes",
            "1 minute": "One minute",
        },
        "5 minutes",
        "100 minutes",
    ),
    (
        "crt_lilypads",
        "In a lake, there is a patch of lily pads. Every day, the patch doubles in size. "
        "If it takes 48 days for the patch to cover the entire lake, how long would it "
        "take for the patch to cover half of the lake?",
        {
            "47 days": "Forty-seven days",
            "24 days": "Twenty-four days",
            "12 days": "Twelve days",
            "46 days": "Forty-six days",
        },
        "47 days",
        "24 days",
    ),
    (
        "crt_barrel",
        "If John can drink one barrel of water in 6 days, and Mary can drink one barrel "
        "of water in 12 days, how long would it take them to drink one barrel of water "
        "together?",
        {
            "4 days": "Four days",
            "9 days": "Nine days",
            "6 days": "Six days",
            "18 days": "Eighteen days",
        },
        "4 days",
        "9 days",
    ),
    (
        "crt_class_rank",
        "Jerry received both the 15th highest and the 15th lowest mark in the class. "
        "How many students are in the class?",
        {"29": "Twenty-nine", "30": "Thirty", "15": "Fifteen", "31": "Thirty-one"},
        "29",
        "30",
    ),
    (
        "crt_pig",
        "A man buys a pig for $60, sells it for $70, buys it back for $80, and sells it "
        "finally for $90. How much has he made?",
        {"$20": "Twenty dollars", "$10": "Ten dollars", "$0": "Nothing", "$30": "Thirty dollars"},
        "$20",
        "$10",
    ),
]


def probes() -> list[Probe]:
    return [
        binary_choice(
            probe_id=item_id,
            instrument="crt",
            instructions=f"{text} Select the answer.",
            options=options,
            state={"problem": text},
            correct=correct,
            lure=lure,
            scoring="accuracy_and_lure",
        )
        for item_id, text, options, correct, lure in _ITEMS
    ]
