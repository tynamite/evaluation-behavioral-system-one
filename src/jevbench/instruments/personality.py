"""Mini-IPIP Big Five (Donnellan, Oswald, Baird & Lucas 2006).

Items come from the International Personality Item Pool, which is explicitly
public domain — a deliberate choice, since the widely used commercial
inventories (NEO-PI-R, 16PF, MMPI) are copyrighted and could not be reproduced
in a public repository.

Each factor has four items, two of which are reverse-keyed (openness has
three, as in the published Mini-IPIP). The reverse-keyed
items double as a consistency check: a respondent answering the content rather
than the surface wording must reverse its answers on them.
"""

from __future__ import annotations

from .base import Probe, likert_item

# (item text, trait, reverse-keyed)
_ITEMS: list[tuple[str, str, bool]] = [
    ("Am the life of the party.", "extraversion", False),
    ("Sympathize with others' feelings.", "agreeableness", False),
    ("Get chores done right away.", "conscientiousness", False),
    ("Have frequent mood swings.", "neuroticism", False),
    ("Have a vivid imagination.", "openness", False),
    ("Don't talk a lot.", "extraversion", True),
    ("Am not interested in other people's problems.", "agreeableness", True),
    ("Often forget to put things back in their proper place.", "conscientiousness", True),
    ("Am relaxed most of the time.", "neuroticism", True),
    ("Have difficulty understanding abstract ideas.", "openness", True),
    ("Talk to a lot of different people at parties.", "extraversion", False),
    ("Feel others' emotions.", "agreeableness", False),
    ("Like order.", "conscientiousness", False),
    ("Get upset easily.", "neuroticism", False),
    ("Do not have a good imagination.", "openness", True),
    ("Keep in the background.", "extraversion", True),
    ("Am not really interested in others.", "agreeableness", True),
    ("Make a mess of things.", "conscientiousness", True),
    ("Seldom feel blue.", "neuroticism", True),
    ("Am not interested in abstract ideas.", "openness", True),
]


def probes() -> list[Probe]:
    return [
        likert_item(
            probe_id=f"ipip_{i:02d}",
            instrument="mini_ipip",
            statement=text,
            trait=trait,
            reverse=reverse,
        )
        for i, (text, trait, reverse) in enumerate(_ITEMS, start=1)
    ]
