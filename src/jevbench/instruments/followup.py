"""Follow-up battery: fame vs. replicated effect size, on Many Labs 2 items.

See `FOLLOWUP_PREREGISTRATION.md` at the repo root for the full design and its
three amendments. Eight effects, from two sources (Section 4.2 vs. 4.3), plus
the population questions for the six items reused from the first project
(Section 4.1; see `reused_estimates`):

- Five items (moral_typecasting, position_power, choosing_rejecting,
  categorization, incidental_anchors) are newly sourced from ML2's own
  preregistered protocol (https://www.projectimplicit.net/nosek/ML2protocol.pdf),
  which specifies exactly which study, condition and dependent variable ML2
  itself replicated — the numbers are the original authors' own, quoted from
  that document, not paraphrased from a secondary source.
- Three items (knobe, trolley, false_consensus) are Section 4.2, sourced from
  the original papers directly rather than from ML2's protocol (Amendment 3
  later found that ML2 did replicate knobe and trolley; see `ml2_effects.py`),
  cross-checked against secondary sources rather than the papers' own PDFs
  (not accessible here) — see each function's docstring for exactly what that
  means for its wording.

Every item is built three ways:

  own       neutral framing — the model's own answer (persona = neutral)
  simulate  "answer as a typical participant would" (persona = typical_human)
  estimate  a *different question*: predicting the population statistic
            itself, not answering as a participant

`own` and `simulate` reuse the existing persona machinery on one probe, the
same as every other instrument in the battery. `estimate` is a distinct probe
per Amendment 2: items whose human number is a *proportion* (Shafir,
Norenzayan) get a `Noul` targeting the named option the human proportion
refers to; items whose human number is a *mean* (Gray & Wegner's and
Giessner & Schubert's ratings, and incidental anchors' banded percentage
estimate) keep the same primitive and criteria as `own`/`simulate` and only
reword the instructions into a population prediction — so the mean is read
off with the same machinery already used for that item's own/simulate answer.
"""

from __future__ import annotations

from . import cognitive, decision
from .base import Probe, binary_choice, noul_probe, score_probe

RESPONSIBILITY_SCALE = [
    "Not at all responsible",
    "Slightly responsible",
    "Somewhat responsible",
    "Moderately responsible",
    "Quite responsible",
    "Very responsible",
    "Fully responsible",
]

POWER_SCALE = [
    "Totally disagree",
    "Disagree",
    "Slightly disagree",
    "Neither agree nor disagree",
    "Slightly agree",
    "Agree",
    "Totally agree",
]


def moral_typecasting() -> list[Probe]:
    """Gray & Wegner (2009), Study 1a, N=69.

    A man or a baby knocks over a tray of glasses, harming the other. Original
    means on the responsibility item (1-7): man 5.29 (SD 1.86), baby 3.86
    (SD 1.64) — both in `benchmarks.py` as
    `moral_typecasting_responsibility_{man,baby}`.
    """
    conditions = [
        (
            "man",
            "man_commits",
            "The man knocked over the tray of glasses, harming the baby.",
            "the man",
        ),
        (
            "baby",
            "baby_commits",
            "The baby knocked over the tray of glasses, harming the man.",
            "the baby",
        ),
    ]
    probes: list[Probe] = []
    for who, key, vignette, actor_phrase in conditions:
        state = {"scenario": vignette}
        probes.append(
            score_probe(
                probe_id=f"moral_typecasting_{key}",
                instrument="moral_typecasting",
                instructions=f"How responsible is {actor_phrase} for the behaviour?",
                criteria=RESPONSIBILITY_SCALE,
                state=state,
                condition=who,
                elicitation="response",
            )
        )
        probes.append(
            score_probe(
                probe_id=f"moral_typecasting_{key}_estimate",
                instrument="moral_typecasting_estimate",
                instructions=(
                    "In a real study, participants read this scenario and rated how "
                    f"responsible {actor_phrase} was for the behaviour, from 1 (not at all "
                    "responsible) to 7 (fully responsible). What do you estimate the average "
                    "rating participants gave?"
                ),
                criteria=RESPONSIBILITY_SCALE,
                state=state,
                condition=who,
                elicitation="estimate",
            )
        )
    return probes


def position_and_power() -> list[Probe]:
    """Giessner & Schubert (2007), Study 1a, N=64.

    A manager's org chart shows a short (2cm) or long (7cm) line to their
    team. Original means, composite of 5 items (1-7): long line 5.01
    (SD 0.60), short line 4.62 (SD 0.81) —
    `position_power_{long,short}_line` in `benchmarks.py`.
    """
    company = (
        "Company A has 126 employees and an average gross salary of about $49,000. "
        "You will evaluate Manager A of this company based on very little information: "
        "an organisation chart showing Manager A connected to their team by a "
    )
    conditions = [("long", "long_line", "long (7cm)"), ("short", "short_line", "short (2cm)")]
    instructions = (
        "Rate the following statements about Manager A on a scale from 1 (totally "
        "disagree) to 7 (totally agree): Manager A is dominant; has a strong leader "
        "personality; is self-confident; has a lot of control in the company; holds a "
        "very high status within the company. Give your overall rating, averaging across "
        "these five qualities."
    )
    probes: list[Probe] = []
    for label, key, line_desc in conditions:
        state = {"company": f"{company}{line_desc} vertical line."}
        probes.append(
            score_probe(
                probe_id=f"position_power_{key}",
                instrument="position_power",
                instructions=instructions,
                criteria=POWER_SCALE,
                state=state,
                condition=label,
                elicitation="response",
            )
        )
        probes.append(
            score_probe(
                probe_id=f"position_power_{key}_estimate",
                instrument="position_power_estimate",
                instructions=(
                    "In a real study, participants saw this organisation chart and rated "
                    "Manager A's perceived power on the same five qualities, from 1 (totally "
                    "disagree) to 7 (totally agree). What do you estimate the average overall "
                    "rating participants gave?"
                ),
                criteria=POWER_SCALE,
                state=state,
                condition=label,
                elicitation="estimate",
            )
        )
    return probes


def choosing_vs_rejecting() -> list[Probe]:
    """Shafir (1993), Study 1, N=170.

    A custody case: Parent A has uniformly average features, Parent B has a
    mix of strongly positive and strongly negative features. Original
    proportions choosing the extreme parent (B): 0.64 when framed as
    "award", 0.55 when framed as "deny" — `shafir_{award,deny}_extreme` in
    `benchmarks.py`. The sum exceeds 1.0 by design: that asymmetry is the
    finding.
    """
    preamble = (
        "Imagine that you serve on the jury of an only-child sole-custody case "
        "following a relatively messy divorce. The facts of the case are complicated "
        "by ambiguous economic, social, and emotional considerations, and you decide "
        "to base your decision entirely on the following few observations."
    )
    parents = {
        "parent_a": (
            "Parent A: average income, average health, average working hours, "
            "reasonable rapport with the child, and a relatively stable social life."
        ),
        "parent_b": (
            "Parent B: above-average income, a very close relationship with the child, "
            "an extremely active social life, lots of work-related travel, and minor "
            "health problems."
        ),
    }
    state = {"case": preamble, **parents}
    probes: list[Probe] = [
        binary_choice(
            probe_id="shafir_award",
            instrument="choosing_rejecting",
            instructions="To which parent would you award sole custody of the child?",
            options={"parent_a": parents["parent_a"], "parent_b": parents["parent_b"]},
            state=state,
            framing="award",
            extreme_option="parent_b",
        ),
        binary_choice(
            probe_id="shafir_deny",
            instrument="choosing_rejecting",
            instructions="Which parent would you deny sole custody of the child?",
            options={"parent_a": parents["parent_a"], "parent_b": parents["parent_b"]},
            state=state,
            framing="deny",
            extreme_option="parent_b",
        ),
        noul_probe(
            probe_id="shafir_award_estimate",
            instrument="choosing_rejecting_estimate",
            instructions=(
                "In a real study, participants read about these two parents and were asked "
                "to award sole custody to one of them. What proportion of participants "
                "awarded custody to Parent B, the parent with more extreme — both more "
                "positive and more negative — features?"
            ),
            state=state,
            framing="award",
            target="parent_b",
        ),
        noul_probe(
            probe_id="shafir_deny_estimate",
            instrument="choosing_rejecting_estimate",
            instructions=(
                "In a real study, participants read about these two parents and were asked "
                "to deny sole custody to one of them. What proportion of participants denied "
                "custody to Parent B, the parent with more extreme — both more positive and "
                "more negative — features?"
            ),
            state=state,
            framing="deny",
            target="parent_b",
        ),
    ]
    return probes


def categorization() -> list[Probe]:
    """Norenzayan, Smith, Kim & Nisbett (2002), Study 2, "belongs to" condition.

    Artificial stimuli matching the paradigm's logical structure as the Many
    Labs 2 protocol describes it: four binary features. In Group 1 one feature
    (colour: red) is common to every member and the target, a usable rule. In
    Group 2 no feature is common to every member and the target, but one member
    shares three features with the target and three share two: a family
    resemblance with no rule. Original pooled proportion choosing the
    rule-based group: 0.67, `norenzayan_rule_based` in `benchmarks.py`.

    The committed 12 Oct 2026 runs used a version in which one Group 2 member
    duplicated a Group 1 member, and a note in the prompt described the
    structure; docs/LEARNINGS.md has the detail.
    """
    target = "Colour: red. Shape: round. Size: large. Surface: glossy."
    group1 = [
        "Colour: red. Shape: angular. Size: small. Surface: matte.",
        "Colour: red. Shape: round. Size: small. Surface: matte.",
        "Colour: red. Shape: angular. Size: large. Surface: matte.",
        "Colour: red. Shape: angular. Size: small. Surface: glossy.",
    ]
    group2 = [
        "Colour: red. Shape: round. Size: small. Surface: glossy.",
        "Colour: blue. Shape: round. Size: small. Surface: glossy.",
        "Colour: blue. Shape: round. Size: large. Surface: matte.",
        "Colour: blue. Shape: angular. Size: large. Surface: glossy.",
    ]
    state = {
        "task": (
            "A newly discovered mineral has these features: "
            f"{target} Two groups of minerals have already been classified."
        ),
        "target": target,
        "group_1": group1,
        "group_2": group2,
    }
    return [
        binary_choice(
            probe_id="norenzayan_belongs_to",
            instrument="categorization",
            instructions="Which group does the target mineral belong to?",
            options={"group_1": "Group 1", "group_2": "Group 2"},
            state=state,
            rule_based_option="group_1",
        ),
        noul_probe(
            probe_id="norenzayan_belongs_to_estimate",
            instrument="categorization_estimate",
            instructions=(
                "In a real study, participants were shown a target object with four binary "
                "features and two candidate groups — one defined by a single shared feature "
                "(a usable classification rule), the other sharing no single feature with the "
                "target but resembling it closely overall — and asked which group the target "
                "belongs to. What proportion of participants chose the rule-based group?"
            ),
            state=state,
            target="group_1",
        ),
    ]


def incidental_anchors() -> list[Probe]:
    """Critcher & Gilovich (2008), Study 2, N=207.

    A smartphone is named the "P97" or the "P17"; participants estimate its
    US market share. Original means: P97 58.1% (SD 19.6), P17 51.9%
    (SD 21.7) — `incidental_anchor_{p97,p17}` in `benchmarks.py`. The bands
    below are centred on that 46-70% range rather than reusing the existing
    UN-Africa anchoring item's bands, which cluster around 0-55%.
    """
    phone_text = (
        'The Sony Ericsson {model} is an Android-powered smartphone with a 5.2" Full HD '
        "resolution display. The {model} is designed to be lightweight and compact, and "
        "features the most up-to-date processor and battery components. It will be sold "
        "in both the United States and Europe."
    )
    bands = {
        "0-35%": "Between 0% and 35%",
        "35-45%": "Between 35% and 45%",
        "45-55%": "Between 45% and 55%",
        "55-65%": "Between 55% and 65%",
        "65-80%": "Between 65% and 80%",
        "80-100%": "Between 80% and 100%",
    }
    probes: list[Probe] = []
    for model in ("P97", "P17"):
        state = {"product": phone_text.format(model=model)}
        probes.append(
            binary_choice(
                probe_id=f"incidental_anchor_{model.lower()}",
                instrument="incidental_anchors",
                instructions=(
                    f"What percentage of {model} smartphones sold will be sold in the "
                    "United States? Choose the closest band."
                ),
                options=bands,
                state=state,
                model=model,
                scoring="banded_estimate",
            )
        )
        probes.append(
            binary_choice(
                probe_id=f"incidental_anchor_{model.lower()}_estimate",
                instrument="incidental_anchors_estimate",
                instructions=(
                    f"In a real study, participants saw this description of the {model} and "
                    "estimated what percentage of units would be sold in the United States. "
                    "What do you estimate the average participant answer was? Choose the "
                    "closest band."
                ),
                options=bands,
                state=state,
                model=model,
                scoring="banded_estimate",
            )
        )
    return probes


def intentional_side_effects() -> list[Probe]:
    """Knobe (2003), Analysis 63:190-194, N=78 (39 harm / 39 help).

    A company chairman starts a program that will incidentally harm or help
    the environment; he says he doesn't care about the environment, only
    profit. The vignette below is quoted close to the original (verified
    against secondary sources reproducing it, not the original PDF).
    Original proportions judging the side effect intentional: harm 0.82,
    help 0.23 — `knobe_{harm,help}_intentional` in `benchmarks.py`.
    """
    harm_vignette = (
        "The vice-president of a company went to the chairman of the board and said, "
        "'We are thinking of starting a new program. It will help us increase profits, "
        "but it will also harm the environment.' The chairman of the board answered, "
        "'I don't care at all about harming the environment. I just want to make as much "
        "profit as I can. Let's start the new program.' They started the new program. "
        "Sure enough, the environment was harmed."
    )
    help_vignette = (
        "The vice-president of a company went to the chairman of the board and said, "
        "'We are thinking of starting a new program. It will help us increase profits, "
        "and it will also help the environment.' The chairman of the board answered, "
        "'I don't care at all about helping the environment. I just want to make as much "
        "profit as I can. Let's start the new program.' They started the new program. "
        "Sure enough, the environment was helped."
    )
    options = {
        "intentional": "Yes, he did it intentionally",
        "unintentional": "No, he did not do it intentionally",
    }
    conditions = [("harm", harm_vignette), ("help", help_vignette)]
    probes: list[Probe] = []
    for verb, vignette in conditions:
        state = {"scenario": vignette}
        probes.append(
            binary_choice(
                probe_id=f"knobe_{verb}",
                instrument="knobe",
                instructions=f"Did the chairman intentionally {verb} the environment?",
                options=options,
                state=state,
                condition=verb,
                intentional_option="intentional",
            )
        )
        probes.append(
            noul_probe(
                probe_id=f"knobe_{verb}_estimate",
                instrument="knobe_estimate",
                instructions=(
                    "In a real study, participants read this scenario and were asked "
                    f"whether the chairman intentionally {verb}ed the environment. What "
                    "proportion of participants said yes, he did it intentionally?"
                ),
                state=state,
                condition=verb,
                target="intentional",
            )
        )
    return probes


def trolley_dilemma() -> list[Probe]:
    """Hauser, Cushman, Young, Jin & Mikhail (2007), Mind & Language 22:1-21.

    Web-based "Moral Sense Test", large international sample. The vignettes
    below are the standard switch/footbridge formulation used throughout the
    trolley-problem literature, including this study's own web instrument —
    the original paper's exact item wording wasn't accessible here, so this
    is the canonical version rather than a verbatim quote; only the reported
    percentages are the paper's own. Original proportions judging the action
    permissible: switch 0.89, push 0.11 —
    `trolley_{switch,push}_permissible` in `benchmarks.py`.
    """
    switch_vignette = (
        "A runaway trolley is heading down the tracks toward five people who will be "
        "killed if it proceeds on its present course. You are standing next to a switch. "
        "If you pull the switch, the trolley will be diverted onto a side track, where it "
        "will kill one person instead of the five people on the main track."
    )
    push_vignette = (
        "A runaway trolley is heading down the tracks toward five people who will be "
        "killed if it proceeds on its present course. You are standing on a footbridge "
        "above the tracks, next to a large stranger. The only way to save the five people "
        "is to push the stranger off the footbridge and onto the tracks below; his body "
        "will stop the trolley before it reaches the five people, but he will die."
    )
    options = {
        "permissible": "Yes, it is morally permissible",
        "not_permissible": "No, it is not morally permissible",
    }
    conditions = [
        ("switch", switch_vignette, "pull the switch"),
        ("push", push_vignette, "push the stranger off the footbridge"),
    ]
    probes: list[Probe] = []
    for label, vignette, action in conditions:
        state = {"scenario": vignette}
        probes.append(
            binary_choice(
                probe_id=f"trolley_{label}",
                instrument="trolley",
                instructions=f"Is it morally permissible for you to {action}?",
                options=options,
                state=state,
                condition=label,
            )
        )
        probes.append(
            noul_probe(
                probe_id=f"trolley_{label}_estimate",
                instrument="trolley_estimate",
                instructions=(
                    "In a real study, participants read this scenario and were asked "
                    f"whether it would be morally permissible to {action}. What proportion "
                    "of participants said yes, it is permissible?"
                ),
                state=state,
                condition=label,
                target="permissible",
            )
        )
    return probes


def false_consensus() -> list[Probe]:
    """Ross, Greene & House (1977), J. Experimental Social Psychology 13:279-301,
    Study 3, N=104.

    Participants are asked whether they would wear a sandwich-board sign
    reading "EAT AT JOE'S" around campus for 30 minutes, then estimate what
    proportion of their peers would also agree. Original mean estimates:
    participants who agreed to wear it predicted 0.614 of peers would also
    agree (reported as 61.4% in the paper); participants who refused
    predicted 0.304 (30.4%) —
    `false_consensus_{wearer,nonwearer}_predicts_wear` in `benchmarks.py`.
    Unlike this module's other items, the published DV is itself a
    proportion estimate, so `own`/`simulate` are already `Noul` probes here
    rather than a `Choice` converted into one only for `estimate`. The
    instructions ask for a proportion (0 to 1), not a 0-100 percentage,
    to match `Noul`'s own [0, 1] output — the same convention the
    proportion-type `estimate` probes elsewhere in this module already use.
    """
    sign = (
        "A researcher on campus asks whether you would be willing to walk around campus "
        'for 30 minutes wearing a sandwich-board sign that reads "EAT AT JOE\'S."'
    )
    conditions = [
        ("wearer", "Suppose you agree to wear the sign.", "agreed to wear it"),
        ("nonwearer", "Suppose you refuse to wear the sign.", "refused to wear it"),
    ]
    probes: list[Probe] = []
    for label, frame, past_choice in conditions:
        state = {"scenario": sign, "frame": frame}
        probes.append(
            noul_probe(
                probe_id=f"false_consensus_{label}",
                instrument="false_consensus",
                instructions=(
                    f"{frame} What proportion (from 0 to 1) of your fellow students do you "
                    "think would also agree to wear the sign?"
                ),
                state=state,
                condition=label,
            )
        )
        probes.append(
            noul_probe(
                probe_id=f"false_consensus_{label}_estimate",
                instrument="false_consensus_estimate",
                instructions=(
                    "In a real study, participants were asked whether they would agree to "
                    f"wear this sign around campus. Among those who {past_choice}, what do "
                    "you estimate was the average proportion (from 0 to 1) they predicted "
                    "for how many of their fellow students would also agree to wear it?"
                ),
                state=state,
                condition=label,
            )
        )
    return probes


def _estimate_of(item: Probe, target: str) -> Probe:
    """The population question for a reused item: what share chose `target`?

    Section 8.1 of the follow-up preregistration: for a `Choice` item,
    "estimate" is a `Noul` asking for the proportion who gave one named option,
    the option the item's human value counts. The participant's question and
    options go in the state unchanged, so only the instruction differs.
    """
    criteria = item.question.criteria
    assert isinstance(criteria, dict), f"{item.probe_id} is not a Choice item"
    return noul_probe(
        probe_id=f"{item.probe_id}_estimate",
        instrument=f"{item.instrument}_estimate",
        instructions=(
            "In a real study, participants were given this question and chose one of "
            "these options. What proportion of participants chose this option: "
            f'"{criteria[target]}"?'
        ),
        state={**(item.state or {}), "question": item.question.instructions, "options": criteria},
        target=target,
    )


def reused_estimates() -> list[Probe]:
    """Population questions for the six items reused from the first project (section 4.1).

    The items themselves are asked in their own modules, unchanged; only their
    estimate twins live here. Each targets the option its human value counts:
    the correct answer for Frederick's three CRT items (the benchmark covers
    those three only), the certain programme in each framing problem, the
    certain or higher-probability gamble in each Allais pair, the conjunction
    for Linda, the 0-10% band for the mammogram problem, and finishing the
    plane for sunk cost. These were added after the 12-13 Oct 2026 runs and
    asked in a separate run (data/raw/README.md).
    """
    by_id = {
        p.probe_id: p
        for p in (
            *cognitive.probes(),
            *decision.framing(),
            *decision.allais(),
            *decision.conjunction(),
            *decision.base_rate(),
            *decision.sunk_cost(),
        )
    }
    targets = {
        "crt_bat_ball": "$0.05",
        "crt_widgets": "5 minutes",
        "crt_lilypads": "47 days",
        "framing_gain": "program_a",
        "framing_loss": "program_c",
        "allais_problem1": "option_a",
        "allais_problem2": "option_c",
        "conjunction_forced_choice": "teller_and_feminist",
        "base_rate_mammogram": "0-10%",
        "sunk_cost": "continue",
    }
    return [_estimate_of(by_id[pid], target) for pid, target in targets.items()]


def probes() -> list[Probe]:
    return [
        *moral_typecasting(),
        *position_and_power(),
        *choosing_vs_rejecting(),
        *categorization(),
        *incidental_anchors(),
        *intentional_side_effects(),
        *trolley_dilemma(),
        *false_consensus(),
        *reused_estimates(),
    ]
