"""Many Labs 2's own replicated effect sizes for the follow-up item pool.

Source: Klein et al. (2018), "Many Labs 2: Investigating Variation in
Replicability Across Samples and Settings," *Advances in Methods and
Practices in Psychological Science* 1(4):443-490
(https://doi.org/10.1177/2515245918810225) — specifically its "The 28
Effects" section, which reports the original study's own numbers alongside
ML2's aggregate replication for each of the 28 studies it ran. Fetched and
read in full on 2026-09-19; every number below is transcribed directly from
that section, not from a secondary summary.

**This is not the same check as "is this paper in ML2's 28."** Several items
in this project's pool ARE among ML2's 28 effects but under a *different*
vignette or condition than the one this project actually built:

- `framing`: this project's item is the gain/loss "Asian disease" framing
  problem from Tversky & Kahneman (1981). ML2's effect 16 ("Effect of
  framing on decision making") is a *different* study from the same paper
  (Study 10: a $5-discount travel decision). Same source paper, different
  experiment -- there is no ML2-replicated number for the Asian disease
  problem specifically.
- `false_consensus`: this project's item is the sandwich-board-sign study
  (Ross, Greene & House 1977, Study 3, N=104). ML2 ran two *other* studies
  from the same 1977 paper (effects 13 and 14: the supermarket and
  traffic-ticket vignettes, both from Study 1) -- again, same paper,
  different vignette, no ML2 number for the one this project uses.

Both are recorded here with `matches_probe=False` and a `match_note`
explaining the mismatch, rather than silently omitted or force-matched to
the nearest available number. `crt`, `conjunction`, `sunk_cost`, `allais`
and `base_rate` are not in ML2's 28 at all (confirmed by reading the full
effects list; `crt` appears only as an individual-difference *moderator*
measure using a different CRT variant, never as a replication target).

`knobe` and `categorization` matched studies but with a caveat each:
- `knobe`: ML2's replication (effect 27) measured intentionality on a 7-point
  scale rather than the original dichotomous yes/no judgment this project's
  probe uses. The vignette is the same; the *measure* changed for the
  replication. `replicated_d` is on that different scale.
- `categorization`: ML2's headline test (effect 20) compared the "belongs
  to" and "similar to" conditions against each other; this project only
  built the "belongs to" condition (matching what the follow-up
  preregistration's Section 4.3 already used). ML2's paper separately
  reports the belongs-to condition's own replicated rate (64%), which is
  what `replicated_proportions` uses here -- not the cross-condition d.
"""

from __future__ import annotations

from dataclasses import dataclass

FormatGroup = str  # "choice" (a proportion DV) | "score" (a mean/rating DV)


@dataclass(frozen=True, slots=True)
class ML2Effect:
    item_key: str
    ml2_effect_number: int | str | None
    ml2_title: str
    matches_probe: bool
    match_note: str
    format_group: FormatGroup
    original_proportions: tuple[float, float] | None = None
    replicated_proportions: tuple[float, float] | None = None
    original_d: float | None = None
    replicated_d: float | None = None
    note: str = ""


ML2_EFFECTS: dict[str, ML2Effect] = {
    e.item_key: e
    for e in [
        ML2Effect(
            "crt",
            None,
            "not a replication target",
            False,
            "CRT appears in ML2 only as an individual-difference moderator measure "
            "(the Finucane & Gullion 2010 variant), never as one of the 28 replicated "
            "effects.",
            "choice",
        ),
        ML2Effect(
            "framing",
            16,
            "Effect of framing on decision making (Study 10)",
            False,
            "Different T&K (1981) sub-study (a $5-discount travel decision, not the "
            "gain/loss Asian disease problem this project built). No ML2 number exists "
            "for the Asian disease item specifically.",
            "choice",
            original_proportions=(0.68, 0.29),
            replicated_proportions=(0.49, 0.32),
            replicated_d=0.40,
            note="Kept for the record; NOT usable as this project's framing item's "
            "ML2-replicated magnitude.",
        ),
        ML2Effect(
            "conjunction",
            None,
            "not a replication target",
            False,
            "Not among ML2's 28 effects.",
            "choice",
        ),
        ML2Effect(
            "sunk_cost",
            None,
            "not a replication target",
            False,
            "Not among ML2's 28 effects.",
            "choice",
        ),
        ML2Effect(
            "allais",
            None,
            "not a replication target",
            False,
            "Not among ML2's 28 effects.",
            "choice",
        ),
        ML2Effect(
            "base_rate",
            None,
            "not a replication target",
            False,
            "Not among ML2's 28 effects.",
            "choice",
        ),
        ML2Effect(
            "knobe",
            27,
            "Perceived intentionality for side effects (Study 1)",
            True,
            "Same chairman/environment vignette as this project's probe. The "
            "replication's own DV changed to a 7-point Likert scale rather than the "
            "original's dichotomous yes/no; replicated_d is on that scale.",
            "choice",
            original_proportions=(0.82, 0.23),
            original_d=1.45,
            replicated_d=1.75,
            note="Replicated means were Likert 1-7: harmful 5.34 (SD 1.94), helpful "
            "2.17 (SD 1.69) -- not directly comparable to this project's own/simulate "
            "proportions, only usable as a standardized magnitude for ranking.",
        ),
        ML2Effect(
            "trolley",
            11,
            "Trolley Dilemma 1: principle of double effect (Scenarios 1 and 2)",
            True,
            "Same switch/push vignette pair as this project's probe.",
            "choice",
            original_proportions=(0.89, 0.11),
            original_d=2.50,
            replicated_proportions=(0.71, 0.17),
            replicated_d=1.35,
        ),
        ML2Effect(
            "false_consensus",
            "13, 14",
            "False consensus: supermarket / traffic-ticket scenarios (Study 1)",
            False,
            "This project's item is Ross, Greene & House (1977) Study 3 (the "
            "sandwich-board sign, N=104). ML2 ran two different scenarios from the "
            "same paper's Study 1 instead -- neither is the sandwich-board vignette, "
            "so no ML2 number exists for this project's item.",
            "choice",
            replicated_d=1.18,
            note="1.18 is the supermarket scenario's (effect 13) replicated d; the "
            "traffic-ticket scenario (effect 14) replicated at d=0.95. Both kept for "
            "the record; NEITHER is usable as this project's false_consensus item's "
            "ML2-replicated magnitude.",
        ),
        ML2Effect(
            "moral_typecasting",
            22,
            "Moral typecasting (Study 1a)",
            True,
            "Exact match: same vignette, same responsibility-rating DV.",
            "score",
            original_d=0.80,
            replicated_d=0.95,
            note="Replicated means: man 5.41 (SD 1.63), baby 3.77 (SD 1.79) -- close "
            "to but not identical to this project's benchmark (5.29/3.86, the "
            "ORIGINAL study's own means, per Amendment 1's design).",
        ),
        ML2Effect(
            "position_power",
            15,
            "Vertical position and power (Study 1a)",
            True,
            "Exact match: same organisation-chart vignette and power-rating DV.",
            "score",
            original_d=0.55,
            replicated_d=0.03,
            note="Replicated means: long line 4.97 (SD 1.09), short line 4.93 "
            "(SD 1.07) -- essentially no effect, a near-total non-replication of the "
            "original d=0.55.",
        ),
        ML2Effect(
            "choosing_rejecting",
            25,
            "Effect of choosing versus rejecting on relative desirability (Study 1)",
            True,
            "Exact match: same custody-case vignette and award/deny framing.",
            "choice",
            original_proportions=(0.64, 0.55),
            original_d=0.35,
            replicated_proportions=(0.455, 0.476),
            replicated_d=-0.13,
            note="The replication REVERSED direction: award+deny summed to 93% "
            "(< 100%), the opposite of the original's >100% finding -- see "
            "Amendment 3.",
        ),
        ML2Effect(
            "categorization",
            20,
            "Preferences for formal versus intuitive reasoning (Study 2)",
            True,
            "Same target/group stimulus structure and 'belongs to' condition as this "
            "project's probe; ML2's headline test compared 'belongs to' against "
            "'similar to', but the paper separately reports the belongs-to "
            "condition's own rate, used here.",
            "choice",
            replicated_proportions=(0.64, 0.36),
            note="64% rule-based in the belongs-to condition (SD 25%), N=7,396 "
            "pooled. Close to this project's original-study benchmark (0.67).",
        ),
        ML2Effect(
            "incidental_anchors",
            9,
            "Influence of incidental anchors on judgment (Study 2)",
            True,
            "Exact match: same P97/P17 smartphone vignette.",
            "score",
            original_d=0.30,
            replicated_d=0.04,
            note="Already used directly in FOLLOWUP_PREREGISTRATION.md's H3 "
            "(currency) test and fig9_followup_currency.",
        ),
    ]
}
