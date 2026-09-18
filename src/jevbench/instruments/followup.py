"""Follow-up battery: fame vs. replicated effect size, on Many Labs 2 items.

See `FOLLOWUP_PREREGISTRATION.md` at the repo root for the full design and its
two amendments. Five items, each newly sourced from ML2's own preregistered
protocol (https://www.projectimplicit.net/nosek/ML2protocol.pdf), which
specifies exactly which study, condition and dependent variable ML2 itself
replicated — the numbers here are the original authors' own, quoted from that
document, not paraphrased from a secondary source.

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

    Artificial stimuli with 4 binary features, matching the paradigm's logical
    structure exactly: Group 1's members share exactly one feature with each
    other and the target (a usable classification rule); Group 2's members
    share no single feature with the target and each other, but one member
    resembles the target closely overall and the rest moderately — a
    family-resemblance group with no rule. Original pooled proportion
    choosing the rule-based group: 0.67 — `norenzayan_rule_based` in
    `benchmarks.py`.
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
        "Colour: red. Shape: angular. Size: large. Surface: matte.",
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
        "note": (
            "Every Group 1 mineral shares exactly one feature (colour: red) with each "
            "other and with the target mineral. No single feature is shared by every "
            "Group 2 mineral and the target, but the Group 2 minerals resemble the "
            "target closely overall."
        ),
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


def probes() -> list[Probe]:
    return [
        *moral_typecasting(),
        *position_and_power(),
        *choosing_vs_rejecting(),
        *categorization(),
        *incidental_anchors(),
    ]
