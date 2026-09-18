"""Fluid reasoning battery, in the format of the ICAR public-domain item bank.

A deliberate naming decision: this measures **reasoning accuracy**, not IQ. An
IQ score is norm-referenced — it positions a person against a standardisation
sample with age norms. A model has neither an age nor a reference population,
so "Jev's IQ" is not a quantity that exists. Accuracy on a fixed item set is.

Items are authored for this study in the format of the International Cognitive
Ability Resource (Condon & Revelle 2014, Intelligence 43:52-64), which is the
open, public-domain alternative to the commercial instruments. They are *not*
the validated ICAR-16 items and carry no ICAR norms. The commercial batteries
(WAIS, Raven's APM) are copyrighted and could not be reproduced here.

Three-dimensional rotation items, the fourth ICAR item type, are omitted: they
are inherently visual and Jev accepts text only.

Every item carries a `steps` count — the number of chained inferences needed.
That is the variable of interest: a model with no deliberation should degrade
as the chain lengthens, which is a sharper test than overall accuracy.
"""

from __future__ import annotations

from .base import Probe, binary_choice

# (id, prompt, options, correct, steps, subtype)
_ITEMS: list[tuple[str, str, dict[str, str], str, int, str]] = [
    (
        "series_squares",
        "What number comes next in this series?  1, 4, 9, 16, 25, ?",
        {"36": "36", "30": "30", "35": "35", "49": "49"},
        "36",
        1,
        "letter_number_series",
    ),
    (
        "series_odd_diff",
        "What number comes next in this series?  3, 6, 11, 18, 27, ?",
        {"38": "38", "36": "36", "37": "37", "40": "40"},
        "38",
        2,
        "letter_number_series",
    ),
    (
        "series_double_minus",
        "What number comes next in this series?  2, 3, 5, 9, 17, ?",
        {"33": "33", "31": "31", "34": "34", "25": "25"},
        "33",
        2,
        "letter_number_series",
    ),
    (
        "series_letters_skip",
        "What letter comes next in this series?  A, C, F, J, O, ?",
        {"U": "U", "T": "T", "V": "V", "S": "S"},
        "U",
        3,
        "letter_number_series",
    ),
    (
        "series_alternating",
        "What number comes next in this series?  8, 4, 12, 6, 18, 9, ?",
        {"27": "27", "13": "13", "36": "36", "21": "21"},
        "27",
        3,
        "letter_number_series",
    ),
    (
        "series_additive",
        "What number comes next in this series?  5, 7, 12, 19, 31, ?",
        {"50": "50", "43": "43", "48": "48", "62": "62"},
        "50",
        3,
        "letter_number_series",
    ),
    (
        "verbal_barometer",
        "Thermometer is to temperature as barometer is to what?",
        {
            "pressure": "pressure",
            "altitude": "altitude",
            "humidity": "humidity",
            "weather": "weather",
        },
        "pressure",
        1,
        "verbal_reasoning",
    ),
    (
        "verbal_oasis",
        "Oasis is to desert as island is to what?",
        {"ocean": "ocean", "sand": "sand", "palm": "palm", "beach": "beach"},
        "ocean",
        2,
        "verbal_reasoning",
    ),
    (
        "verbal_ephemeral",
        "Ephemeral is to permanent as scarce is to what?",
        {"abundant": "abundant", "rare": "rare", "valuable": "valuable", "limited": "limited"},
        "abundant",
        2,
        "verbal_reasoning",
    ),
    (
        "verbal_negation",
        ("If it is false that 'all of the boxes are empty', which statement must be true?"),
        {
            "at least one box is not empty": "At least one box is not empty",
            "none of the boxes are empty": "None of the boxes are empty",
            "exactly one box is not empty": "Exactly one box is not empty",
            "all of the boxes are full": "All of the boxes are full",
        },
        "at least one box is not empty",
        2,
        "verbal_reasoning",
    ),
    (
        "matrix_count",
        (
            "In this 3x3 grid, each cell is described by shape and count.\n"
            "Row 1: one circle | two circles | three circles\n"
            "Row 2: one square | two squares | three squares\n"
            "Row 3: one triangle | two triangles | ?\n"
            "What belongs in the empty cell?"
        ),
        {
            "three triangles": "three triangles",
            "three squares": "three squares",
            "two triangles": "two triangles",
            "one triangle": "one triangle",
        },
        "three triangles",
        1,
        "matrix_reasoning",
    ),
    (
        "matrix_two_rules",
        (
            "In this 3x3 grid, each cell is described by shape, count and shading.\n"
            "Row 1: one white circle | two white circles | three white circles\n"
            "Row 2: one grey square | two grey squares | three grey squares\n"
            "Row 3: one black triangle | two black triangles | ?\n"
            "What belongs in the empty cell?"
        ),
        {
            "three black triangles": "three black triangles",
            "three grey triangles": "three grey triangles",
            "three black squares": "three black squares",
            "two black triangles": "two black triangles",
        },
        "three black triangles",
        2,
        "matrix_reasoning",
    ),
    (
        "matrix_rotation_rule",
        (
            "In this 3x3 grid, an arrow rotates by a fixed amount from each cell to the next, "
            "moving left to right along each row and then continuing on the next row.\n"
            "Row 1: arrow points north | arrow points east | arrow points south\n"
            "Row 2: arrow points west | arrow points north | arrow points east\n"
            "Row 3: arrow points south | arrow points west | ?\n"
            "What belongs in the empty cell?"
        ),
        {
            "arrow points north": "arrow points north",
            "arrow points east": "arrow points east",
            "arrow points south": "arrow points south",
            "arrow points west": "arrow points west",
        },
        "arrow points north",
        3,
        "matrix_reasoning",
    ),
    (
        "matrix_subtractive",
        (
            "In this 3x3 grid, the third cell in each row is obtained by removing from the "
            "first cell every element that also appears in the second cell.\n"
            "Row 1: circle, square, triangle | square | circle, triangle\n"
            "Row 2: star, circle, square | circle, square | star\n"
            "Row 3: triangle, star, square, circle | star, circle | ?\n"
            "What belongs in the empty cell?"
        ),
        {
            "triangle, square": "triangle, square",
            "triangle, star": "triangle, star",
            "square, circle": "square, circle",
            "triangle, square, circle": "triangle, square, circle",
        },
        "triangle, square",
        3,
        "matrix_reasoning",
    ),
    (
        "quant_average",
        (
            "A student's mean mark over 4 tests is 80. After a fifth test the mean is 82. "
            "What did the student score on the fifth test?"
        ),
        {"90": "90", "84": "84", "82": "82", "88": "88"},
        "90",
        3,
        "quantitative",
    ),
    (
        "quant_relative_speed",
        (
            "A train travels 60 km at 60 km/h, then 60 km at 30 km/h. "
            "What is its average speed over the whole journey?"
        ),
        {"40 km/h": "40 km/h", "45 km/h": "45 km/h", "50 km/h": "50 km/h", "35 km/h": "35 km/h"},
        "40 km/h",
        4,
        "quantitative",
    ),
    (
        "quant_deduction",
        (
            "Five runners finish a race. C finishes before D but after B. "
            "E finishes after D. A finishes before B. Who finishes third?"
        ),
        {"C": "C", "B": "B", "D": "D", "A": "A"},
        "C",
        4,
        "quantitative",
    ),
    (
        "quant_compound",
        (
            "A shop raises a price by 20%, then discounts the new price by 20%. "
            "Compared with the original price, the final price is:"
        ),
        {
            "4% lower": "4% lower",
            "the same": "the same",
            "4% higher": "4% higher",
            "2% lower": "2% lower",
        },
        "4% lower",
        3,
        "quantitative",
    ),
]


def probes() -> list[Probe]:
    return [
        binary_choice(
            probe_id=f"reason_{item_id}",
            instrument="fluid_reasoning",
            instructions=f"{prompt}\n\nSelect the answer.",
            options=options,
            state={"problem": prompt},
            scoring="accuracy",
            correct=correct,
            steps=steps,
            subtype=subtype,
        )
        for item_id, prompt, options, correct, steps, subtype in _ITEMS
    ]
