"""Published human reference values.

Every entry carries its source and an explicit reliability flag. These are
*literature reference points*, not a matched control sample collected
alongside the model runs: the human participants differ from each other in
population, stake size, currency, year and lab protocol. Treat gaps of a few
percentage points as noise and only large, directional divergences as
meaningful. `RELIABILITY` is deliberately conservative.

    high        large meta-analysis or very widely replicated single finding
    medium      well-known finding, but point estimates vary across samples
    approximate order-of-magnitude only; sample-dependent
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Benchmark:
    key: str
    statistic: str
    value: float
    units: str
    source: str
    reliability: str
    note: str = ""


BENCHMARKS: dict[str, Benchmark] = {
    b.key: b
    for b in [
        Benchmark(
            "crt_proportion_correct",
            "mean proportion of CRT items answered correctly",
            0.413,
            "proportion",
            "Frederick (2005), J. Econ. Perspectives 19(4):25-42, n=3,428",
            "high",
            "Reported as mean 1.24 of 3 items. Varies hugely by sample (MIT 2.18, "
            "Univ. of Toledo 0.57), so the aggregate is the fair comparator.",
        ),
        Benchmark(
            "dictator_mean_share",
            "mean share of pie given by dictator",
            0.283,
            "share of pie",
            "Engel (2011), Experimental Economics 14:583-610; meta-analysis of 616 studies",
            "high",
            "The distribution is strongly bimodal: ~36% give nothing and ~17% give exactly half. "
            "The mean alone is a poor summary; compare the full histogram.",
        ),
        Benchmark(
            "dictator_share_zero",
            "proportion of dictators giving nothing",
            0.36,
            "proportion",
            "Engel (2011) meta-analysis",
            "high",
            "",
        ),
        Benchmark(
            "dictator_share_half",
            "proportion of dictators giving exactly half",
            0.17,
            "proportion",
            "Engel (2011) meta-analysis",
            "high",
            "",
        ),
        Benchmark(
            "ultimatum_mean_offer",
            "mean proposer offer as share of pie",
            0.40,
            "share of pie",
            "Camerer (2003), Behavioral Game Theory, ch. 2; Oosterbeek et al. (2004) meta-analysis",
            "high",
            "Modal offer is typically exactly half. Remarkably stable across countries and stakes.",
        ),
        Benchmark(
            "ultimatum_rejection_low_offer",
            "rejection rate for offers below 20% of pie",
            0.50,
            "proportion",
            "Camerer (2003), Behavioral Game Theory, ch. 2",
            "medium",
            "Rejection falls steeply as the offer rises; near-zero at an equal split.",
        ),
        Benchmark(
            "trust_sender_share",
            "share of endowment sent by the sender",
            0.50,
            "share of endowment",
            "Berg, Dickhaut & McCabe (1995), Games and Economic Behavior 10:122-142; "
            "Johnson & Mislin (2011) meta-analysis of 162 replications",
            "high",
            "",
        ),
        Benchmark(
            "trust_return_share",
            "share of the tripled amount returned by the trustee",
            0.37,
            "share of tripled amount",
            "Johnson & Mislin (2011), J. Economic Psychology 32:865-889",
            "high",
            "Returns average slightly less than the amount originally sent, so senders "
            "roughly break even.",
        ),
        Benchmark(
            "pgg_round1_share",
            "first-round contribution as share of endowment",
            0.50,
            "share of endowment",
            "Ledyard (1995) in Handbook of Experimental Economics; Fehr & Gächter (2000), AER 90:980-994",
            "medium",
            "Typically 40-60% in round 1, decaying toward zero over repeated rounds without punishment.",
        ),
        Benchmark(
            "pd_cooperation_oneshot",
            "cooperation rate in a one-shot prisoner's dilemma",
            0.37,
            "proportion",
            "Sally (1995) meta-analysis, Rationality and Society 7:58-92; "
            "Mengel (2018) meta-analysis, Economic Journal 128:3182-3209",
            "medium",
            "Estimates range roughly 0.30-0.50 depending on payoffs and framing.",
        ),
        Benchmark(
            "framing_gain_certain",
            "choosing the certain option under a gain frame",
            0.72,
            "proportion",
            "Tversky & Kahneman (1981), Science 211:453-458",
            "high",
            "",
        ),
        Benchmark(
            "framing_loss_certain",
            "choosing the certain option under a loss frame",
            0.22,
            "proportion",
            "Tversky & Kahneman (1981), Science 211:453-458",
            "high",
            "The 50-point swing between frames is the effect; the levels matter less.",
        ),
        Benchmark(
            "allais_p1_certain",
            "choosing the certain $3,000 in the first pair",
            0.80,
            "proportion",
            "Kahneman & Tversky (1979), Econometrica 47:263-291",
            "high",
            "",
        ),
        Benchmark(
            "allais_p2_certain",
            "choosing the higher-probability gamble in the second pair",
            0.35,
            "proportion",
            "Kahneman & Tversky (1979), Econometrica 47:263-291",
            "high",
            "65% switch to the $4,000 gamble, violating the independence axiom.",
        ),
        Benchmark(
            "conjunction_fallacy_rate",
            "rating the conjunction as more probable",
            0.85,
            "proportion",
            "Tversky & Kahneman (1983), Psychological Review 90:293-315",
            "high",
            "",
        ),
        Benchmark(
            "base_rate_correct_band",
            "giving an answer in the correct 0-10% band",
            0.15,
            "proportion",
            "Eddy (1982) in Judgment Under Uncertainty; Gigerenzer & Hoffrage (1995), Psych. Review 102:684-704",
            "medium",
            "Eddy reported ~95% of physicians answering 70-80%. The normative answer is 7.8%.",
        ),
        Benchmark(
            "anchoring_low_median",
            "median estimate under a low (10%) anchor",
            25.0,
            "percent",
            "Tversky & Kahneman (1974), Science 185:1124-1131",
            "medium",
            "",
        ),
        Benchmark(
            "anchoring_high_median",
            "median estimate under a high (65%) anchor",
            45.0,
            "percent",
            "Tversky & Kahneman (1974), Science 185:1124-1131",
            "medium",
            "The 20-point gap between anchors is the effect of interest.",
        ),
        Benchmark(
            "sunk_cost_continue",
            "continuing the losing project",
            0.85,
            "proportion",
            "Arkes & Blumer (1985), Org. Behavior and Human Decision Processes 35:124-140",
            "medium",
            "",
        ),
        Benchmark(
            "holt_laury_safe_choices",
            "mean number of safe (Option A) choices out of 10",
            5.2,
            "count",
            "Holt & Laury (2002), American Economic Review 92:1644-1655",
            "high",
            "A risk-neutral agent makes 4 safe choices then switches at row 5. "
            "About 66% of participants are risk averse at low stakes.",
        ),
        Benchmark(
            "beauty_contest_mean",
            "mean guess in a two-thirds beauty contest",
            36.0,
            "number 0-100",
            "Nagel (1995), American Economic Review 85:1313-1326",
            "medium",
            "Nash equilibrium is 0. Human guesses spike at 33 (one step of reasoning) "
            "and 22 (two steps). Large newspaper samples average lower, around 23.",
        ),
        Benchmark(
            "money_request_modal",
            "modal request in the 11-20 game",
            17.0,
            "shekels",
            "Arad & Rubinstein (2012), American Economic Review 102:3561-3573",
            "high",
            "Observed distribution roughly: 20 -> 6%, 19 -> 12%, 18 -> 30%, 17 -> 32%. "
            "Equilibrium play is mixed and concentrated on 15-17.",
        ),
        Benchmark(
            "present_bias_reversal",
            "preference reversal between immediate and delayed front end",
            0.30,
            "proportion",
            "Thaler (1981), Economics Letters 8:201-207; Frederick, Loewenstein & O'Donoghue (2002), JEL 40:351-401",
            "approximate",
            "Magnitude varies widely with amounts and delays; direction (more patience when "
            "both options are delayed) is the robust finding, not the level.",
        ),
        Benchmark(
            "mini_ipip_extraversion",
            "mean Mini-IPIP extraversion score",
            3.2,
            "1-5 scale",
            "Donnellan, Oswald, Baird & Lucas (2006), Psychological Assessment 18:192-203",
            "approximate",
            "Norms are sample-dependent; treat as a rough centre, not a target.",
        ),
        Benchmark(
            "mini_ipip_agreeableness",
            "mean Mini-IPIP agreeableness score",
            4.0,
            "1-5 scale",
            "Donnellan et al. (2006)",
            "approximate",
            "",
        ),
        Benchmark(
            "mini_ipip_conscientiousness",
            "mean Mini-IPIP conscientiousness score",
            3.4,
            "1-5 scale",
            "Donnellan et al. (2006)",
            "approximate",
            "",
        ),
        Benchmark(
            "mini_ipip_neuroticism",
            "mean Mini-IPIP neuroticism score",
            2.8,
            "1-5 scale",
            "Donnellan et al. (2006)",
            "approximate",
            "",
        ),
        Benchmark(
            "mini_ipip_openness",
            "mean Mini-IPIP openness/intellect score",
            3.7,
            "1-5 scale",
            "Donnellan et al. (2006)",
            "approximate",
            "",
        ),
        # --- Follow-up battery: sourced from ML2's own preregistered protocol ---
        # (https://www.projectimplicit.net/nosek/ML2protocol.pdf), which quotes each
        # original study's own reported numbers. These are the ORIGINAL authors' point
        # estimates, not ML2's own replicated means (ML2's public tables report only
        # replicated effect sizes, not raw means) — original sample sizes are modest
        # (N=64-207), so "medium" throughout, even though ML2 confirms the effect's
        # existence and direction at far higher power. See FOLLOWUP_PREREGISTRATION.md.
        Benchmark(
            "moral_typecasting_responsibility_man",
            "mean responsibility rating when the higher-agency party (the man) commits the act",
            5.29,
            "1-7 scale",
            "Gray & Wegner (2009), J. Personality and Social Psychology 96:505-520, Study 1a, N=69",
            "medium",
            "SD 1.86 in the original. Companion condition: moral_typecasting_responsibility_baby.",
        ),
        Benchmark(
            "moral_typecasting_responsibility_baby",
            "mean responsibility rating when the lower-agency party (the baby) commits the act",
            3.86,
            "1-7 scale",
            "Gray & Wegner (2009), J. Personality and Social Psychology 96:505-520, Study 1a, N=69",
            "medium",
            "SD 1.64 in the original. Higher-agency actors are rated more responsible.",
        ),
        Benchmark(
            "position_power_long_line",
            "mean perceived-power composite when the org-chart line is long (7cm)",
            5.01,
            "1-7 scale",
            "Giessner & Schubert (2007), Org. Behavior and Human Decision Processes 104:30-44, "
            "Study 1a, N=64",
            "medium",
            "SD 0.60 in the original. Composite of 5 items. Companion: position_power_short_line.",
        ),
        Benchmark(
            "position_power_short_line",
            "mean perceived-power composite when the org-chart line is short (2cm)",
            4.62,
            "1-7 scale",
            "Giessner & Schubert (2007), Org. Behavior and Human Decision Processes 104:30-44, "
            "Study 1a, N=64",
            "medium",
            "SD 0.81 in the original.",
        ),
        Benchmark(
            "shafir_award_extreme",
            "proportion awarding custody to the extreme (mixed-feature) parent",
            0.64,
            "proportion",
            "Shafir (1993), Memory & Cognition 21:546-556, Study 1, N=170",
            "medium",
            "Companion shafir_deny_extreme sums to over 1.0 with this by design: the extreme "
            "parent is both chosen and rejected more than the average parent.",
        ),
        Benchmark(
            "shafir_deny_extreme",
            "proportion denying custody to the extreme (mixed-feature) parent",
            0.55,
            "proportion",
            "Shafir (1993), Memory & Cognition 21:546-556, Study 1, N=170",
            "medium",
            "See shafir_award_extreme.",
        ),
        Benchmark(
            "norenzayan_rule_based",
            "proportion choosing the rule-based group in the 'belongs to' framing",
            0.67,
            "proportion",
            "Norenzayan, Smith, Kim & Nisbett (2002), Cognitive Science 26:653-684, Study 2",
            "medium",
            "Pooled across European American, Asian American and East Asian samples, as ML2 "
            "replicated it. The original reports a cultural split (Europeans more rule-based, "
            "East Asians more family-resemblance) that this pooled figure obscures.",
        ),
        Benchmark(
            "incidental_anchor_p97",
            "mean estimated US market share when the phone is named the 'P97'",
            58.1,
            "percent",
            "Critcher & Gilovich (2008), J. Behavioral Decision Making 21:241-251, Study 2, N=207",
            "medium",
            "SD 19.6 in the original. Companion: incidental_anchor_p17. ML2 replicated this "
            "effect at d=0.04 against an original d=0.30 — essentially gone; see "
            "FOLLOWUP_PREREGISTRATION.md Section 2 (H3).",
        ),
        Benchmark(
            "incidental_anchor_p17",
            "mean estimated US market share when the phone is named the 'P17'",
            51.9,
            "percent",
            "Critcher & Gilovich (2008), J. Behavioral Decision Making 21:241-251, Study 2, N=207",
            "medium",
            "SD 21.7 in the original. See incidental_anchor_p97.",
        ),
    ]
}


def get(key: str) -> Benchmark | None:
    return BENCHMARKS.get(key)
