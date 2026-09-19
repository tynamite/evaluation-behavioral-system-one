"""The fame index (`FOLLOWUP_PREREGISTRATION.md`, Section 8.2, Amendment 1).

Three legs, computed before any model call and independent of anything the
model outputs:

  1. citation_count   canonical paper's citation count (Semantic Scholar /
                       Google Scholar), checked on the date recorded here
  2. wikipedia_words   word count of the effect's own dedicated Wikipedia
                       article; 0 if it has none
  3. familiarity        the *comparison arm's* model rating "how well-known is
                       this finding to a general audience" (1-5), averaged
                       over 5 replicates, loaded from
                       `data/fame_familiarity.json` once `scripts/
                       rate_familiarity.py` has produced it

Leg 3 is corroborating, not decisive (Section 8.2): it is sourced from the
comparison model rather than Jev specifically to avoid the circularity of
asking Jev to rate an effect's fame and then using that rating to explain
Jev's own behaviour on it, but both models are still trained on overlapping
text, so it never overrides what legs 1 and 2 say on its own.

Citation counts here were gathered by web search on 2026-09-19, not a single
authoritative API pull — Semantic Scholar's public API was rate-limited
(HTTP 429) for the whole session, and Google Scholar does not serve a
scrapable citation count. Ten of fourteen came back with a number attributable
to a source; those are recorded as approximate. Four (`crt`, `trolley`,
`position_power`, `base_rate`) came back with no number at all from any
source tried — `citation_count=None` on those is a documented gap, not a
guess dressed up as a figure. `position_power` and `base_rate` still have a
Wikipedia figure to lean on; `crt` and `trolley` are missing leg 1 entirely,
which the drop rule below treats as "insufficient data," not as agreement.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from statistics import mean

from .config import REPO_ROOT

FAMILIARITY_PATH = REPO_ROOT / "data" / "fame_familiarity.json"


@dataclass(frozen=True, slots=True)
class FameItem:
    key: str
    label: str
    paper: str
    citation_count: int | None
    citation_note: str
    wikipedia_article: str | None
    wikipedia_words: int
    benchmarks: tuple[str, ...]
    familiarity_prompt: str


ITEMS: dict[str, FameItem] = {
    item.key: item
    for item in [
        FameItem(
            "crt",
            "Cognitive reflection test",
            "Frederick (2005)",
            None,
            "No citation count found via web search on 2026-09-19; Semantic "
            "Scholar's API was rate-limited for the whole session and Google "
            "Scholar isn't scrapable. Widely described in secondary sources as "
            "one of the most-cited papers in judgment-and-decision-making "
            "research, but that is a qualitative impression, not a number, and "
            "is not used as one here.",
            "Cognitive reflection test",
            2300,
            ("crt_proportion_correct",),
            "A short quiz found that people often give an intuitive but wrong "
            "answer to simple math riddles, like the one about a bat and a "
            "ball costing $1.10 together where the bat costs $1 more than the "
            "ball (most people blurt out '10 cents', which is wrong).",
        ),
        FameItem(
            "framing",
            "Framing effect (Asian disease problem)",
            "Tversky & Kahneman (1981)",
            17_313,
            "Approximate, via web search aggregation on 2026-09-19.",
            "Framing effect (psychology)",
            5_700,
            ("framing_gain_certain", "framing_loss_certain"),
            "People choose differently between two mathematically identical "
            "policy options depending on whether the outcome is described in "
            "terms of lives saved or lives lost (the 'Asian disease' problem).",
        ),
        FameItem(
            "conjunction",
            "Conjunction fallacy (Linda problem)",
            "Tversky & Kahneman (1983)",
            3_906,
            "Approximate, via web search aggregation on 2026-09-19.",
            "Conjunction fallacy",
            3_700,
            ("conjunction_fallacy_rate",),
            "Given a detailed personality sketch of a woman named 'Linda,' "
            "most people judge it more probable that she is 'a bank teller "
            "active in the feminist movement' than just 'a bank teller,' even "
            "though that is logically impossible (the conjunction fallacy).",
        ),
        FameItem(
            "sunk_cost",
            "Sunk cost fallacy",
            "Arkes & Blumer (1985)",
            2_520,
            "Approximate, via web search aggregation on 2026-09-19.",
            "Sunk cost",
            4_700,
            ("sunk_cost_continue",),
            "People tend to keep investing in a losing project because of the "
            "money already spent on it, even when a fresh look at the future "
            "costs and benefits alone would say to stop (the sunk cost "
            "fallacy).",
        ),
        FameItem(
            "allais",
            "Allais paradox",
            "Kahneman & Tversky (1979)",
            37_003,
            "Approximate, via web search aggregation on 2026-09-19.",
            "Allais paradox",
            3_700,
            ("allais_p1_certain", "allais_p2_certain"),
            "Faced with a choice between a certain amount of money and a "
            "gamble, then a second, related choice between two gambles, "
            "people's choices violate a basic consistency axiom of expected "
            "utility theory (the Allais paradox).",
        ),
        FameItem(
            "base_rate",
            "Base-rate neglect (mammogram problem)",
            "Eddy (1982)",
            None,
            "No citation count found via web search on 2026-09-19, for the "
            "same reason as `crt`. As a chapter in an edited volume rather "
            "than a journal article, it is also likely undercounted in "
            "citation databases relative to its actual influence, since "
            "citations to the volume as a whole don't attach to this chapter "
            "specifically.",
            "Base rate fallacy",
            4_700,
            ("base_rate_correct_band",),
            "Told a mammogram test's false-positive rate and how rare the "
            "disease is, most doctors and patients badly overestimate the "
            "chance that a positive result means the patient actually has the "
            "disease, ignoring how rare the disease is (base-rate neglect).",
        ),
        FameItem(
            "knobe",
            "Side-effect effect",
            "Knobe (2003)",
            942,
            "Exact, Semantic Scholar Graph API, checked 2026-09-19 (the one "
            "successful call before the API's rate limit fully kicked in for "
            "the rest of this session).",
            None,
            0,
            (),
            "People are more likely to say a side effect was caused "
            "'intentionally' when it's a harmful side effect than when it's an "
            "equally unintended helpful one, even though nothing else about "
            "the decision changed (the Knobe effect).",
        ),
        FameItem(
            "trolley",
            "Trolley problem: switch vs. push",
            "Hauser et al. (2007)",
            None,
            "No citation count found via web search on 2026-09-19, same "
            "reason as `crt`. This is a citation count for this specific "
            "paper, not for the trolley problem as a thought experiment, "
            "which is far older and separately famous (see the Wikipedia "
            "figure).",
            "Trolley problem",
            4_700,
            (),
            "Most people say it's okay to divert a runaway trolley onto a "
            "track where it kills one person instead of five by flipping a "
            "switch, but say it's not okay to achieve the exact same outcome "
            "by pushing one person off a footbridge into its path (the "
            "trolley problem).",
        ),
        FameItem(
            "false_consensus",
            "False consensus effect",
            "Ross, Greene & House (1977)",
            2_870,
            "Approximate, via web search aggregation on 2026-09-19.",
            "False consensus effect",
            5_700,
            (),
            "People who hold a view tend to overestimate how many other "
            "people share that view, compared to people who hold the "
            "opposite view (the false consensus effect).",
        ),
        FameItem(
            "moral_typecasting",
            "Moral typecasting",
            "Gray & Wegner (2009)",
            723,
            "Approximate, via web search aggregation on 2026-09-19.",
            None,
            0,
            ("moral_typecasting_responsibility_man", "moral_typecasting_responsibility_baby"),
            "People rate an adult as more responsible for an accident than a "
            "baby who causes identical physical harm, because responsibility "
            "gets assigned to whichever party seems more like a moral 'agent' "
            "rather than a moral 'patient' (moral typecasting).",
        ),
        FameItem(
            "position_power",
            "Spatial metaphors of power",
            "Giessner & Schubert (2007)",
            None,
            "No citation count found via web search on 2026-09-19, same "
            "reason as `crt`. Secondary sources describe it as 'widely cited' "
            "within its own subfield (embodied cognition / power), but that "
            "subfield is narrower than the other items here, and no number "
            "was ever surfaced.",
            None,
            0,
            ("position_power_long_line", "position_power_short_line"),
            "People judge a manager shown with a taller vertical line on an "
            "org chart as more powerful than the same manager shown with a "
            "shorter line, even though nothing else about the manager "
            "changes (spatial metaphors of power).",
        ),
        FameItem(
            "choosing_rejecting",
            "Choosing vs. rejecting",
            "Shafir (1993)",
            557,
            "Approximate, via web search aggregation on 2026-09-19.",
            None,
            0,
            ("shafir_award_extreme", "shafir_deny_extreme"),
            "In a custody dispute between an average parent and a parent with "
            "a mix of extreme positive and negative traits, the extreme "
            "parent gets chosen more often AND rejected more often than the "
            "average parent, depending only on how the question is asked "
            "(choosing vs. rejecting).",
        ),
        FameItem(
            "categorization",
            "Rule-based vs. family-resemblance categorization",
            "Norenzayan, Smith, Kim & Nisbett (2002)",
            508,
            "Approximate, via web search aggregation on 2026-09-19.",
            None,
            0,
            ("norenzayan_rule_based",),
            "People classify a novel object into a category either by "
            "applying one defining rule or by its overall resemblance to "
            "typical group members, and which strategy dominates differs "
            "somewhat across cultures (rule-based vs. family-resemblance "
            "categorization).",
        ),
        FameItem(
            "incidental_anchors",
            "Incidental anchoring",
            "Critcher & Gilovich (2008)",
            191,
            "Approximate, via web search aggregation on 2026-09-19.",
            None,
            0,
            ("incidental_anchor_p97", "incidental_anchor_p17"),
            "An irrelevant number embedded in something's name, like a "
            "product's model number, can nudge people's later numeric "
            "estimates about something completely unrelated (incidental "
            "anchoring). This is a narrower, less-famous paradigm than "
            "classic anchor-and-adjust anchoring (already a benchmark "
            "elsewhere in this project); it has no dedicated Wikipedia "
            "article of its own, so its wikipedia_words is 0 rather than "
            "borrowed from the general 'Anchoring effect' page.",
        ),
    ]
}


def _terciles(values: list[float]) -> tuple[float, float]:
    """Two cut points splitting `values` into low/medium/high thirds."""
    s = sorted(values)
    n = len(s)
    lo = s[max(0, n // 3 - 1)]
    hi = s[max(0, (2 * n) // 3 - 1)]
    return lo, hi


def citation_tier(item: FameItem) -> str | None:
    known = [i.citation_count for i in ITEMS.values() if i.citation_count is not None]
    if item.citation_count is None or len(known) < 3:
        return None
    lo, hi = _terciles([float(c) for c in known])
    if item.citation_count <= lo:
        return "low"
    if item.citation_count <= hi:
        return "medium"
    return "high"


def wikipedia_tier(item: FameItem) -> str:
    """Zero words is always low; otherwise terciled against the items that have one."""
    if item.wikipedia_words == 0:
        return "low"
    known = [i.wikipedia_words for i in ITEMS.values() if i.wikipedia_words > 0]
    lo, hi = _terciles([float(w) for w in known])
    if item.wikipedia_words <= lo:
        return "low"
    if item.wikipedia_words <= hi:
        return "medium"
    return "high"


_TIER_RANK = {"low": 0, "medium": 1, "high": 2}


def load_familiarity() -> dict[str, list[float]]:
    """Leg 3's raw ratings, keyed by item, from `scripts/rate_familiarity.py`'s output."""
    if not FAMILIARITY_PATH.exists():
        return {}
    data = json.loads(FAMILIARITY_PATH.read_text())
    return {k: [float(v) for v in vs] for k, vs in data.items()}


def familiarity_mean(key: str, ratings: dict[str, list[float]] | None = None) -> float | None:
    ratings = ratings if ratings is not None else load_familiarity()
    vals = ratings.get(key)
    return mean(vals) if vals else None


@dataclass(frozen=True, slots=True)
class FameVerdict:
    key: str
    citation_tier: str | None
    wikipedia_tier: str
    familiarity_mean: float | None
    fame_tier: str | None
    dropped: bool
    reason: str


def evaluate(item: FameItem, ratings: dict[str, list[float]] | None = None) -> FameVerdict:
    """Combine legs 1-2 into a tier, applying the drop rule from Section 8.2.

    Leg 3 (familiarity) is recorded but never decides the tier or the drop,
    per the preregistration: it's corroborating, not decisive, given the
    residual circularity concern even with a different rater model.
    """
    c_tier = citation_tier(item)
    w_tier = wikipedia_tier(item)
    fam = familiarity_mean(item.key, ratings)

    if c_tier is None:
        return FameVerdict(
            item.key, None, w_tier, fam, None, True, "citation count unavailable (leg 1 missing)"
        )

    gap = abs(_TIER_RANK[c_tier] - _TIER_RANK[w_tier])
    if gap > 1:
        return FameVerdict(
            item.key,
            c_tier,
            w_tier,
            fam,
            None,
            True,
            f"legs disagree by {gap} tiers (citations={c_tier}, wikipedia={w_tier})",
        )

    combined = round((_TIER_RANK[c_tier] + _TIER_RANK[w_tier]) / 2)
    tier = {v: k for k, v in _TIER_RANK.items()}[combined]
    return FameVerdict(item.key, c_tier, w_tier, fam, tier, False, "")


def all_verdicts(ratings: dict[str, list[float]] | None = None) -> list[FameVerdict]:
    ratings = ratings if ratings is not None else load_familiarity()
    return [evaluate(item, ratings) for item in ITEMS.values()]
