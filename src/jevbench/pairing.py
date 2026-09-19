"""The Section 3 pairing rule (`FOLLOWUP_PREREGISTRATION.md`).

"Within each response-format group (Choice-binary, Score-rating), rank items
by ML2-replicated proportion/effect size and by fame index; pair each item
with its nearest neighbour on magnitude from the opposite fame tercile."

Three things had to be made concrete that the preregistration left implicit,
each documented at the point it's decided rather than silently:

1. **Magnitude.** ML2 reports a Cohen's *d* for every one of its 28 effects,
   but this project's `choice`-format items are proportions, for which *d* is
   the wrong effect size. `magnitude()` uses Cohen's *h* (the arcsine-based
   effect size for two proportions), computed from ML2's own *replicated*
   proportions where those exist; where an item's replication changed
   measurement scale entirely (`knobe`: dichotomous originally, a 7-point
   Likert in ML2's replication), ML2's own reported *d* is used as the next
   best standardized magnitude, since no replicated proportion exists to
   compute *h* from. `score`-format items use ML2's own replicated *d*
   directly, the metric it was already computed in.
2. **"Opposite tercile."** Well-defined for `low` (opposite `high`) and
   `high` (opposite `low`); the preregistration never says what `medium`'s
   opposite is. Here `medium` prefers `high`, falling back to `low` if no
   `high` item is available in that format group -- documented here because
   nothing upstream specifies it, not because it's expected to matter (see
   `build_pairs`'s module-level result on the real data).
3. **One-to-one, not many-to-one.** The unit of analysis in Section 3 is a
   *paired* difference tested with Wilcoxon signed-rank across "12-16
   pairs" -- a design that assumes each item anchors at most one pair, not
   one famous item anchoring several obscure ones. Matching here is
   nearest-neighbour *without replacement*: greedily pair the closest
   available cross-tercile magnitudes, removing both items from the pool
   each time, until one side of a format group is exhausted.

Eligibility for pairing requires passing two independent filters, not one:
the fame index's own drop rule (`fame.evaluate`, Amendment 1's leg
disagreement/missing-leg rule) AND `ml2_effects.ML2_EFFECTS[key].matches_probe`
(this project's probe must be the same vignette/condition ML2 actually
replicated, not just any effect ML2 happened to run on the same source
paper). Both are necessary: an item can be famous enough to survive the fame
filter and still have no valid ML2-replicated number for the specific item
this project built (`framing`, `false_consensus` — see
`ml2_effects.py`'s module docstring for why), and an item can have a clean
ML2 match and still be dropped for missing fame data (`trolley`,
`position_power`, both dropped upstream for a missing citation count).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from . import fame
from .ml2_effects import ML2_EFFECTS, ML2Effect

TERCILE_RANK = {"low": 0, "medium": 1, "high": 2}
OPPOSITE_PREFERENCE = {
    "low": ("high", "medium"),
    "medium": ("high", "low"),
    "high": ("low", "medium"),
}


def cohens_h(p1: float, p2: float) -> float:
    """Arcsine effect size for two proportions -- the right metric for a
    Choice-binary item's magnitude, unlike Cohen's d, which assumes means."""
    return 2 * math.asin(math.sqrt(p1)) - 2 * math.asin(math.sqrt(p2))


def magnitude(effect: ML2Effect) -> float | None:
    """The standardized magnitude used for ranking and nearest-neighbour matching."""
    if effect.format_group == "score":
        return abs(effect.replicated_d) if effect.replicated_d is not None else None
    if effect.replicated_proportions is not None:
        p1, p2 = effect.replicated_proportions
        return abs(cohens_h(p1, p2))
    if effect.replicated_d is not None:
        return abs(effect.replicated_d)
    return None


@dataclass(frozen=True, slots=True)
class EligibleItem:
    key: str
    fame_tier: str
    format_group: str
    magnitude: float


def eligible_items() -> list[EligibleItem]:
    """Items that pass BOTH the fame drop rule and have a usable ML2-replicated
    magnitude for the exact item this project built."""
    verdicts = {v.key: v for v in fame.all_verdicts()}
    out: list[EligibleItem] = []
    for key, effect in ML2_EFFECTS.items():
        if not effect.matches_probe:
            continue
        verdict = verdicts.get(key)
        if verdict is None or verdict.dropped or verdict.fame_tier is None:
            continue
        mag = magnitude(effect)
        if mag is None:
            continue
        out.append(EligibleItem(key, verdict.fame_tier, effect.format_group, mag))
    return out


@dataclass(frozen=True, slots=True)
class Pair:
    lower_fame_key: str
    higher_fame_key: str
    format_group: str
    magnitude_gap: float


def build_pairs(items: list[EligibleItem] | None = None) -> list[Pair]:
    """Section 3's pairing rule: within each format group, greedily match each
    item to its nearest still-unmatched neighbour on magnitude from the
    opposite fame tercile, without replacement. Returns an empty list for a
    format group with items in only one tercile -- there is no "opposite" to
    pair against, and nothing here invents one.
    """
    items = items if items is not None else eligible_items()
    pairs: list[Pair] = []
    groups: dict[str, list[EligibleItem]] = {}
    for it in items:
        groups.setdefault(it.format_group, []).append(it)

    for group_items in groups.values():
        pool = list(group_items)
        # Highest-magnitude items are matched first, so the most extreme cases
        # (most informative for H1/H2) are not left stranded by an earlier,
        # closer-but-less-informative match consuming their only opposite-tercile
        # candidate.
        pool.sort(key=lambda it: -it.magnitude)
        used: set[str] = set()
        for item in pool:
            if item.key in used:
                continue
            candidates = [
                other
                for other in pool
                if other.key not in used
                and other.key != item.key
                and other.fame_tier in OPPOSITE_PREFERENCE[item.fame_tier]
            ]
            if not candidates:
                continue
            for preferred_tier in OPPOSITE_PREFERENCE[item.fame_tier]:
                tier_candidates = [c for c in candidates if c.fame_tier == preferred_tier]
                if tier_candidates:
                    candidates = tier_candidates
                    break
            best = min(candidates, key=lambda c: abs(c.magnitude - item.magnitude))
            used.add(item.key)
            used.add(best.key)
            lower, higher = sorted((item, best), key=lambda it: TERCILE_RANK[it.fame_tier])
            pairs.append(
                Pair(
                    lower_fame_key=lower.key,
                    higher_fame_key=higher.key,
                    format_group=item.format_group,
                    magnitude_gap=abs(item.magnitude - best.magnitude),
                )
            )
    return pairs
