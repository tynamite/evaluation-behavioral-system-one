"""Classic judgement-and-decision-making anomalies.

These are the effects that define the heuristics-and-biases tradition: cases
where humans reliably and predictably violate normative decision theory. Each
has a large, well-replicated human benchmark.

The conjunction-fallacy probe is the sharpest test in the whole battery. The
Noul primitive returns a probability directly, and the conjunction rule
P(A and B) <= P(A) is an axiom of probability, not a matter of taste. Asking
for the two probabilities as independent Noul questions tests the axiom
directly on the returned numbers — a test that is simply unavailable for a
model that emits text.
"""

from __future__ import annotations

from .base import Probe, binary_choice, noul_probe

LINDA = (
    "Linda is 31 years old, single, outspoken and very bright. She majored in philosophy. "
    "As a student, she was deeply concerned with issues of discrimination and social "
    "justice, and also participated in anti-nuclear demonstrations."
)


def framing() -> list[Probe]:
    """Asian disease problem (Tversky & Kahneman 1981). Identical outcomes, opposite frames."""
    preamble = (
        "Imagine that your country is preparing for the outbreak of an unusual disease, "
        "which is expected to kill 600 people. Two alternative programs to combat the "
        "disease have been proposed."
    )
    gain = binary_choice(
        probe_id="framing_gain",
        instrument="framing",
        instructions="Which of the two programs do you favour?",
        options={
            "program_a": "If Program A is adopted, 200 people will be saved.",
            "program_b": (
                "If Program B is adopted, there is a 1/3 probability that 600 people will "
                "be saved and a 2/3 probability that no people will be saved."
            ),
        },
        state={"scenario": preamble, "frame": "gain"},
        scoring="binary",
        frame="gain",
        certain_option="program_a",
    )
    loss = binary_choice(
        probe_id="framing_loss",
        instrument="framing",
        instructions="Which of the two programs do you favour?",
        options={
            "program_c": "If Program C is adopted, 400 people will die.",
            "program_d": (
                "If Program D is adopted, there is a 1/3 probability that nobody will die "
                "and a 2/3 probability that 600 people will die."
            ),
        },
        state={"scenario": preamble, "frame": "loss"},
        scoring="binary",
        frame="loss",
        certain_option="program_c",
    )
    return [gain, loss]


def allais() -> list[Probe]:
    """Common-ratio effect (Kahneman & Tversky 1979). Choosing A then D violates independence."""
    p1 = binary_choice(
        probe_id="allais_problem1",
        instrument="allais",
        instructions="Which gamble do you choose?",
        options={
            "option_a": "$3,000 with certainty",
            "option_b": "$4,000 with probability 0.80, otherwise $0",
        },
        state={"problem": "Choose between two gambles.", "pair": 1},
        scoring="binary",
        pair=1,
        certain_option="option_a",
    )
    p2 = binary_choice(
        probe_id="allais_problem2",
        instrument="allais",
        instructions="Which gamble do you choose?",
        options={
            "option_c": "$3,000 with probability 0.25, otherwise $0",
            "option_d": "$4,000 with probability 0.20, otherwise $0",
        },
        state={"problem": "Choose between two gambles.", "pair": 2},
        scoring="binary",
        pair=2,
        certain_option="option_c",
    )
    return [p1, p2]


def conjunction() -> list[Probe]:
    """Linda problem (Tversky & Kahneman 1983), in both forced-choice and axiom-test form."""
    forced = binary_choice(
        probe_id="conjunction_forced_choice",
        instrument="conjunction",
        instructions="Which of these two statements is more probable?",
        options={
            "teller": "Linda is a bank teller.",
            "teller_and_feminist": "Linda is a bank teller and is active in the feminist movement.",
        },
        state={"description": LINDA},
        scoring="binary",
        fallacy_option="teller_and_feminist",
    )
    # Asked separately, so neither probability can be anchored on the other.
    single = noul_probe(
        "conjunction_p_single",
        "conjunction_axiom",
        "Linda is a bank teller.",
        state={"description": LINDA},
        component="single",
    )
    conj = noul_probe(
        "conjunction_p_conjunction",
        "conjunction_axiom",
        "Linda is a bank teller and is active in the feminist movement.",
        state={"description": LINDA},
        component="conjunction",
    )
    return [forced, single, conj]


def base_rate() -> list[Probe]:
    """Mammogram problem (Eddy 1982; Gigerenzer & Hoffrage 1995). Normative answer ~7.8%."""
    scenario = (
        "1% of women at age forty who participate in routine screening have breast cancer. "
        "80% of women with breast cancer will get positive mammograms. 9.6% of women "
        "without breast cancer will also get positive mammograms. A woman in this age "
        "group had a positive mammogram in a routine screening."
    )
    return [
        binary_choice(
            probe_id="base_rate_mammogram",
            instrument="base_rate",
            instructions=(
                "What is the probability that she actually has breast cancer? Choose the "
                "closest band."
            ),
            options={
                "0-10%": "Between 0% and 10%",
                "10-30%": "Between 10% and 30%",
                "30-50%": "Between 30% and 50%",
                "50-70%": "Between 50% and 70%",
                "70-90%": "Between 70% and 90%",
                "90-100%": "Between 90% and 100%",
            },
            state={"scenario": scenario},
            scoring="banded_estimate",
            correct="0-10%",
            lure="70-90%",
        )
    ]


def anchoring() -> list[Probe]:
    """Anchoring-and-adjustment (Tversky & Kahneman 1974), high vs low anchor."""
    probes: list[Probe] = []
    for label, anchor in (("low", 10), ("high", 65)):
        probes.append(
            binary_choice(
                probe_id=f"anchoring_{label}",
                instrument="anchoring",
                instructions=(
                    "What is your best estimate of the percentage of United Nations member "
                    "states that are African countries? Choose the closest band."
                ),
                options={
                    "0-15%": "Between 0% and 15%",
                    "15-25%": "Between 15% and 25%",
                    "25-35%": "Between 25% and 35%",
                    "35-45%": "Between 35% and 45%",
                    "45-55%": "Between 45% and 55%",
                    "55-100%": "More than 55%",
                },
                state={
                    "anchor_question": (
                        f"First consider: is the percentage of UN member states that are "
                        f"African countries higher or lower than {anchor}%?"
                    ),
                    "anchor_value": anchor,
                },
                scoring="banded_estimate",
                anchor=anchor,
                condition=label,
            )
        )
    return probes


def sunk_cost() -> list[Probe]:
    """Sunk-cost fallacy (Arkes & Blumer 1985). The prior spend is normatively irrelevant."""
    return [
        binary_choice(
            probe_id="sunk_cost",
            instrument="sunk_cost",
            instructions="What do you do?",
            options={
                "continue": "Continue the project and spend the remaining $1 million",
                "abandon": "Abandon the project and keep the remaining $1 million",
            },
            state={
                "scenario": (
                    "Your company has spent $9 million of a $10 million budget developing a "
                    "product. A competitor has just launched a product that is better and "
                    "cheaper than yours will be. Market research says your product will now "
                    "certainly lose money if completed."
                )
            },
            scoring="binary",
            fallacy_option="continue",
        )
    ]


def probes() -> list[Probe]:
    return [
        *framing(),
        *allais(),
        *conjunction(),
        *base_rate(),
        *anchoring(),
        *sunk_cost(),
    ]
