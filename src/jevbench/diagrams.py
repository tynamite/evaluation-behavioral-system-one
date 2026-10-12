"""Editorial figures, drawn in the diagram-design house style.

Each figure is one self-contained HTML file with an inline SVG, generated from
the committed tables and raw records so that, like the rest of the repository,
every mark is recomputable. The visual grammar — tokens, type ramp, plot
geometry, dumbbell and scatter conventions, the accessible-SVG contract — is
taken from the diagram-design skill (github.com/cathrynlavery/diagram-design,
MIT), default skin. Its rules are kept where they bind:

- one focal accent per figure, everything else ink and muted;
- dumbbells: hollow reference end, solid accent end, shared untruncated axis,
  both values printed, row order stated;
- at most 8 rows or bars and 30 points per chart, so wide data is split rather
  than crammed;
- every drawn value carries a `data-*` attribute stating the number it encodes.

`build_diagrams` writes the HTML; `export_pngs` renders each SVG to PNG at 2x
with a headless Chromium, which is what the README embeds.
"""

from __future__ import annotations

import html
import itertools
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .benchmarks import BENCHMARKS

# -- skin: diagram-design default (light) --------------------------------

PAPER = "#f5f5f5"
INK = "#2d3142"
MUTED = "#4f5d75"
SOFT = "#5a6580"
ACCENT = "#157a6e"  # teal accent for everything that is not Jev (4.8:1 on paper)
LINK = "#2e5aa8"
WHITE = "#ffffff"
# Jev with no instruction is hot pink in every chart. The pink is too light to
# be a mark's only edge (2.4:1 on paper), so pink dots keep an ink outline and
# pink bars take the deeper JEV_PINK_EDGE (4.6:1), which also serves as text.
JEV_PINK = "#ff69b4"
JEV_PINK_EDGE = "#d6126f"
# Jev under a prompt (typical person, antisocial persona) stays in the same pink
# family, darker, so every Jev mark reads as Jev.
JEV_PROMPT = "#a3195b"
# Claude Haiku 5.5 is the one non-Jev mark with its own colour: Anthropic orange.
# Too light to be its own edge (2.9:1), so it keeps an ink outline.
ANTHROPIC_ORANGE = "#d97757"


def ink(a: float) -> str:
    return f"rgba(45,49,66,{a})"


def accent(a: float) -> str:
    return f"rgba(21,122,110,{a})"


def muted(a: float) -> str:
    return f"rgba(79,93,117,{a})"


SANS = "'Geist', system-ui, sans-serif"
MONO = "'Geist Mono', ui-monospace, monospace"
SERIF = "'Instrument Serif', serif"

FONT_LINK = (
    "https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1"
    "&family=Geist:wght@400;500;600&family=Geist+Mono:wght@400;500;600&display=swap"
)


def esc(s: object) -> str:
    return html.escape(str(s), quote=True)


def text_width(s: str, size: float, mono: bool = False) -> float:
    """The style guide's width budget: 0.60em per sans glyph, 0.62em mono."""
    return len(s) * size * (0.62 if mono else 0.60)


# -- page wrapper ----------------------------------------------------------


@dataclass
class Figure:
    slug: str
    eyebrow: str
    title: str
    subtitle: str
    desc: str
    width: int
    height: int
    body: str
    source: str

    def html(self) -> str:
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{esc(self.title)}</title>
  <link href="{FONT_LINK}" rel="stylesheet">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    :root {{
      --color-paper: {PAPER}; --color-ink: {INK}; --color-muted: {MUTED};
      --font-sans: {SANS}; --font-serif: {SERIF}; --font-mono: {MONO};
    }}
    body {{
      font-family: var(--font-sans); background: var(--color-paper); color: var(--color-ink);
      min-height: 100vh; display: flex; align-items: center; justify-content: center;
      padding: 3rem 2rem;
    }}
    .frame {{ max-width: {self.width + 80}px; width: 100%; padding: 32px 40px; background: var(--color-paper); }}
    .diagram-container {{ width: 100%; overflow-x: auto; }}
    .eyebrow {{
      font-family: var(--font-mono); font-size: 0.66rem; font-weight: 500;
      letter-spacing: 0.18em; text-transform: uppercase; color: var(--color-muted);
      margin-bottom: 0.5rem;
    }}
    h1 {{
      font-family: var(--font-serif); font-size: clamp(1.5rem, 2.4vw + 0.75rem, 2rem);
      font-weight: 400; letter-spacing: -0.02em; line-height: 1.15; margin-bottom: 0.5rem;
    }}
    .subtitle {{ color: var(--color-muted); font-size: 0.95rem; line-height: 1.45;
      max-width: 60rem; margin-bottom: 1.5rem; }}
    .source {{ font-family: var(--font-mono); font-size: 0.7rem; color: var(--color-muted);
      border-top: 1px solid {ink(0.12)}; margin-top: 1rem; padding-top: 0.75rem; line-height: 1.5; }}
    svg {{ width: 100%; min-width: {self.width}px; display: block; }}
    @media print {{ .diagram-container {{ overflow-x: visible; }} svg {{ min-width: 0; }} }}
  </style>
</head>
<body>
  <div class="frame">
    <p class="eyebrow">{esc(self.eyebrow)}</p>
    <h1>{esc(self.title)}</h1>
    <p class="subtitle">{esc(self.subtitle)}</p>
    <div class="diagram-container">
      <svg viewBox="0 0 {self.width} {self.height}" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="{self.slug}-title {self.slug}-desc">
        <title id="{self.slug}-title">{esc(self.title)}</title>
        <desc id="{self.slug}-desc">{esc(self.desc)}</desc>
        <defs>
          <marker id="arrow" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polygon points="0 0, 8 3, 0 6" fill="{MUTED}"/></marker>
          <marker id="arrow-accent" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polygon points="0 0, 8 3, 0 6" fill="{ACCENT}"/></marker>
          <marker id="arrow-link" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polygon points="0 0, 8 3, 0 6" fill="{LINK}"/></marker>
        </defs>
        <rect width="100%" height="100%" fill="{PAPER}"/>
{self.body}
      </svg>
    </div>
    <p class="source">{esc(self.source)}</p>
  </div>
</body>
</html>
"""


# -- shared chart pieces -----------------------------------------------------


def _t(
    x: float,
    y: float,
    s: str,
    *,
    size: float = 8,
    fill: str = MUTED,
    family: str = MONO,
    anchor: str = "start",
    weight: int | None = None,
    spacing: str | None = None,
    extra: str = "",
    halo: bool = False,
) -> str:
    if halo:
        extra += f' stroke="{PAPER}" stroke-width="3" paint-order="stroke"'
    w = f' font-weight="{weight}"' if weight else ""
    ls = f' letter-spacing="{spacing}"' if spacing else ""
    return (
        f'<text x="{x:g}" y="{y:g}" fill="{fill}" font-size="{size}" font-family="{family}"'
        f' text-anchor="{anchor}"{w}{ls}{extra}>{esc(s)}</text>'
    )


def _legend(width: int, rule_y: int, keys: list[str], right_note: str = "") -> str:
    parts = [
        f'<line x1="30" y1="{rule_y}" x2="{width - 30}" y2="{rule_y}" stroke="{ink(0.10)}" stroke-width="0.8"/>',
        _t(30, rule_y + 16, "LEGEND", size=7, spacing="0.14em"),
    ]
    parts.extend(keys)
    if right_note:
        parts.append(_t(width - 30, rule_y + 35, right_note, anchor="end"))
    return "\n".join(parts)


def _domain(values: list[float], step: float) -> tuple[float, float]:
    """The dumbbell honesty rule: anchor at zero, round outward, never fit min/max."""
    lo, hi = min(values), max(values)
    if lo == hi == 0:
        return 0.0, step
    floor = 0.0 if lo >= 0 else -math.ceil(-lo / step) * step
    ceil = 0.0 if hi <= 0 else math.ceil(hi / step) * step
    return floor, ceil


ROW_LAYOUT = {4: (88, 96), 5: (64, 96), 6: (64, 76), 7: (52, 72), 8: (48, 68)}


def dumbbell(
    rows: list[tuple[str, str, float, float]],
    *,
    ref_name: str,
    focal_name: str,
    ref_fill: str | None = None,
    focal_fill: str = ACCENT,
    row_ref_fill: dict[str, tuple[str, str]] | None = None,
    row_focal_fill: dict[str, tuple[str, str]] | None = None,
    axis_title: str,
    step: float,
    fmt: str = "{:.2f}",
    domain: tuple[float, float] | None = None,
    order_note: str,
    reference_line: tuple[float, str] | None = None,
    label_col: int = 300,
) -> str:
    """Rows of (name, what was asked and measured, reference, focal) inside `0 0 1000 500`.

    The label column is wider than the type reference's 200px because every row
    carries a second line saying what the test was and what the number counts:
    the rows do not all point the same way (some count correct answers, others
    the error), and without that line a reader cannot tell which.
    """
    n = len(rows)
    if not 4 <= n <= 8:
        raise ValueError(f"dumbbell takes 4-8 rows, got {n}")
    # The reference end is hollow by default; a solid fill marks it as a series
    # of its own (Jev with no instruction, in pink), still with an ink edge.
    ref_style = (
        f'fill="{ref_fill}" stroke="{INK}" stroke-width="1"'
        if ref_fill
        else f'fill="{PAPER}" stroke="{MUTED}" stroke-width="1.5"'
    )
    pitch, y0 = ROW_LAYOUT[n]
    vals = [v for _, _, a, b in rows for v in (a, b)]
    if reference_line:
        vals.append(reference_line[0])
    floor, ceil = domain or _domain(vals, step)
    L, R = label_col, 960
    for name, sub, _a, _b in rows:
        if text_width(name, 11) > L - 24 or text_width(sub, 9) > L - 24:
            raise ValueError(f"row label does not fit the label column: {name!r} / {sub!r}")

    def px(v: float) -> int:
        return round(L + (v - floor) / (ceil - floor) * (R - L))

    out: list[str] = []
    ticks = [floor + i * step for i in range(round((ceil - floor) / step) + 1)]
    for t in ticks:
        x = px(t)
        if abs(t - floor) >= 1e-9:
            out.append(
                f'<line x1="{x}" y1="56" x2="{x}" y2="408" stroke="{ink(0.08)}" stroke-width="0.8"/>'
            )
        out.append(
            _t(x, 440, fmt.format(t), anchor="middle", extra=f' data-tick="x" data-value="{t:g}"')
        )
    out.append(f'<line x1="{L}" y1="40" x2="{L}" y2="420" stroke="{ink(0.25)}" stroke-width="1"/>')
    if floor < 0 < ceil:
        out.append(
            f'<line x1="{px(0)}" y1="40" x2="{px(0)}" y2="420" stroke="{ink(0.25)}" stroke-width="1"/>'
        )
    out.append(_t((L + R) / 2, 456, axis_title.upper(), size=7, anchor="middle", spacing="0.14em"))

    if reference_line:
        v, label = reference_line
        x = px(v)
        out.append(
            f'<line x1="{x}" y1="48" x2="{x}" y2="420" stroke="{ink(0.55)}" stroke-width="1" stroke-dasharray="4,3" data-value="{v:g}"/>'
        )
        w = text_width(label, 8, mono=True) + 8
        out.append(
            f'<rect x="{x - w / 2:g}" y="28" width="{w:g}" height="12" rx="2" fill="{PAPER}"/>'
        )
        out.append(_t(x, 37, label, anchor="middle", fill=INK, spacing="0.06em"))

    for i, (name, sub, a, b) in enumerate(rows):
        y = y0 + i * pitch
        xa, xb = px(a), px(b)
        close = abs(xa - xb) < 16
        row_style = ref_style
        row_focal = (row_focal_fill or {}).get(name, (focal_fill, ""))[0]
        if row_ref_fill and name in row_ref_fill:
            row_style = f'fill="{row_ref_fill[name][0]}" stroke="{INK}" stroke-width="1"'
        # A pair too close to separate horizontally is split vertically instead,
        # one dot just above the row and one just below, so neither hides the
        # other; the positions along the axis stay exact.
        r = 5 if close else 6
        ya, yb = (y - 6, y + 6) if close else (y, y)
        out.append(
            f'<line x1="{xa}" y1="{ya}" x2="{xb}" y2="{yb}" stroke="{ink(0.55)}" stroke-width="1"/>'
        )
        out.append(
            f'<circle data-series="reference" data-value="{a:.4f}" cx="{xa}" cy="{ya}" r="{r}" {row_style}/>'
        )
        out.append(
            f'<circle data-series="focal" data-value="{b:.4f}" cx="{xb}" cy="{yb}" r="{r}" fill="{row_focal}" stroke="{INK}" stroke-width="1"/>'
        )
        left, right = (a, b) if xa <= xb else (b, a)
        xl, xr = min(xa, xb), max(xa, xb)
        if close:
            # Too close to separate two labels: print both above the pair.
            out.append(
                _t(
                    (xa + xb) / 2,
                    y - 16,
                    f"{fmt.format(a)} · {fmt.format(b)}",
                    anchor="middle",
                    halo=True,
                )
            )
        else:
            # The floor exception, by drawn width rather than anchor: a left label
            # that would reach into the row-label column goes above its dot.
            if xl - 12 - text_width(fmt.format(left), 8, mono=True) < L - 4:
                out.append(_t(xl, y - 10, fmt.format(left), anchor="middle", halo=True))
            else:
                out.append(_t(xl - 12, y + 4, fmt.format(left), anchor="end", halo=True))
            out.append(_t(xr + 12, y + 4, fmt.format(right), halo=True))
        out.append(
            _t(L - 12, y - 1, name, size=11, fill=INK, family=SANS, anchor="end", weight=600)
        )
        out.append(_t(L - 12, y + 12, sub, size=9, fill=MUTED, family=SANS, anchor="end"))

    keys = [
        f'<circle cx="104" cy="493" r="5" {ref_style}/>',
        _t(116, 497, ref_name, size=9, family=SANS, fill=INK),
        f'<circle cx="{132 + text_width(ref_name, 9) + 24:g}" cy="493" r="5" fill="{focal_fill}" stroke="{INK}" stroke-width="1"/>',
        _t(132 + text_width(ref_name, 9) + 36, 497, focal_name, size=9, family=SANS, fill=INK),
    ]
    out.append(_legend(1000, 462, [], ""))
    out.extend(keys)
    if row_ref_fill or row_focal_fill:
        kx = int(132 + text_width(ref_name, 9) + 36 + text_width(focal_name, 9) + 40)
        for fill, label in [*(row_ref_fill or {}).values(), *(row_focal_fill or {}).values()]:
            out.append(
                f'<circle cx="{kx}" cy="493" r="5" fill="{fill}" stroke="{INK}" stroke-width="1"/>'
            )
            out.append(_t(kx + 12, 497, label, size=9, family=SANS, fill=INK))
            kx += int(12 + text_width(label, 9) + 36)
    out.append(_t(970, 497, order_note, anchor="end"))
    return "\n".join(out)


# -- figure builders -------------------------------------------------------------

# (instrument, statistic, benchmark key, test name, what was asked · what the number counts)
DECISION_MEASURES = [
    (
        "crt",
        "proportion_correct",
        "crt_proportion_correct",
        "Cognitive reflection test",
        "6 trick questions (bat and ball) · correct",
    ),
    (
        "framing",
        "prob_certain_gain_frame",
        "framing_gain_certain",
        "Framing, worded as gains",
        "Disease problem, '200 saved' · picks sure option",
    ),
    (
        "framing",
        "prob_certain_loss_frame",
        "framing_loss_certain",
        "Framing, worded as losses",
        "Same problem, '400 die' · picks sure option",
    ),
    (
        "allais",
        "prob_certain_pair1",
        "allais_p1_certain",
        "Certainty effect (Allais)",
        "$3,000 for sure vs 80% of $4,000 · picks sure",
    ),
    (
        "conjunction",
        "prob_fallacy_forced_choice",
        "conjunction_fallacy_rate",
        "Conjunction fallacy",
        "Linda problem · picks 'teller and feminist'",
    ),
    (
        "base_rate",
        "prob_correct_band",
        "base_rate_correct_band",
        "Base rates (mammogram)",
        "Cancer risk after a positive test · right band",
    ),
    (
        "sunk_cost",
        "prob_continue",
        "sunk_cost_continue",
        "Sunk cost",
        "$9m spent, product now sure to lose · carries on",
    ),
]

GAME_MEASURES = [
    (
        "dictator",
        "mean_share",
        "dictator_mean_share",
        "Dictator game",
        "Give part of $10 to a stranger · share given",
    ),
    (
        "ultimatum_proposer",
        "mean_share",
        "ultimatum_mean_offer",
        "Ultimatum game, proposing",
        "Offer a split of $10 · share offered",
    ),
    (
        "ultimatum_responder",
        "prob_reject_low_offer",
        "ultimatum_rejection_low_offer",
        "Ultimatum game, responding",
        "Offered $0 or $1 of $10 · rejects",
    ),
    (
        "trust_sender",
        "mean_share",
        "trust_sender_share",
        "Trust game, sending",
        "Send part of $10, tripled on arrival · share sent",
    ),
    (
        "trust_trustee",
        "return_share_sent_5",
        "trust_return_share",
        "Trust game, returning",
        "Sent $5, received $15 · share returned",
    ),
    (
        "public_goods",
        "mean_share",
        "pgg_round1_share",
        "Public goods game",
        "4 players, shared pot doubled · share put in",
    ),
    (
        "prisoners_dilemma",
        "cooperation_one_shot",
        "pd_cooperation_oneshot",
        "Prisoner's dilemma",
        "One round, anonymous · cooperates",
    ),
]


def _prompt(key: str) -> str:
    from .instruments import PERSONAS

    return PERSONAS[key].preamble


def _stat(sdf: pd.DataFrame, inst: str, stat: str, persona: str, arm: str = "jev") -> float:
    sel = sdf[
        (sdf.instrument == inst)
        & (sdf.statistic == stat)
        & (sdf.persona == persona)
        & (sdf.arm == arm)
    ]
    if not len(sel):
        raise KeyError(f"{inst}/{stat}/{persona}/{arm} not in statistics")
    return float(sel["value"].iloc[0])


def fig_jev_vs_people(sdf: pd.DataFrame, which: str, persona: str) -> Figure:
    measures = DECISION_MEASURES if which == "decisions" else GAME_MEASURES
    rows = [
        (name, sub, BENCHMARKS[b].value, _stat(sdf, i, s, persona))
        for i, s, b, name, sub in measures
    ]
    as_person = persona == "typical_human"
    slug = f"jev-{which}-{'typical' if as_person else 'neutral'}"
    focal = (
        "Jev 1.13, told to answer like a typical person"
        if as_person
        else "Jev 1.13, no instruction"
    )
    tests = "seven decision-making tests" if which == "decisions" else "five economic games"
    if as_person:
        title = "Jev 1.13 vs. published human results, told to answer like a typical person"
        subtitle = (
            f"The same {tests} as the no-instruction chart, with this sentence added before each: "
            f"\u201c{_prompt('typical_human')}\u201d"
        )
    elif which == "decisions":
        title = f"Jev 1.13 vs. published human results: {tests}"
        subtitle = (
            "Classic problems from behavioural economics, asked with no instruction about how to answer. "
            "Each row says what was asked and which answer is being counted; some rows count the correct "
            "answer, others the typical human error. Jev's value is the probability it puts on that answer."
        )
    else:
        title = f"Jev 1.13 vs. published human results: {tests}"
        subtitle = (
            "One-shot, anonymous games played for a hypothetical $10, asked with no instruction about how to "
            "answer. Each row says what the player could do and what the number measures. Jev's value is the "
            "expected share, or the probability of the choice, from its returned distribution."
        )
    body = dumbbell(
        rows,
        ref_name="Published human result",
        focal_name=focal,
        focal_fill=JEV_PROMPT if as_person else JEV_PINK,
        axis_title="share of answers, or share of the money",
        step=0.2,
        fmt="{:.2f}",
        domain=(0.0, 1.0),
        order_note="ROWS IN BATTERY ORDER",
    )
    return Figure(
        slug=slug,
        eyebrow=f"{'Decision-making tests' if which == 'decisions' else 'Economic games'} · "
        f"{'told to answer like a typical person' if as_person else 'no instruction'}",
        title=title,
        subtitle=subtitle,
        desc=f"Dumbbell chart comparing Jev 1.13's answers{', told to answer like a typical person,' if as_person else ''} with published human results on {len(rows)} measures from {tests}.",
        width=1000,
        height=510,
        body=body,
        source="Jev: mean of the probability distributions returned over 10 repeats, run of 18 Sep 2026. "
        "Human results: published studies or meta-analyses, listed in docs/BENCHMARKS.md; different people, "
        "decades and stakes, so a gap of a few points is not meaningful.",
    )


def fig_jev_decisions(sdf: pd.DataFrame) -> Figure:
    """Three series per row: people, Jev with no instruction, Jev told to answer like a person.

    The dumbbell takes two series, so this is its dot-plot sibling: one hairline
    spanning the three values, a hollow dot for people and two solid colours for
    the two Jev conditions, and the numbers in a table column at the right
    rather than beside the dots, where three labels per row would collide.
    """
    rows = [
        (
            name,
            sub,
            BENCHMARKS[b].value,
            _stat(sdf, i, s, "neutral"),
            _stat(sdf, i, s, "typical_human"),
        )
        for i, s, b, name, sub in DECISION_MEASURES
    ]
    n = len(rows)
    pitch, y0 = ROW_LAYOUT[n]
    L, R = 300, 820
    cols = [(874, "PEOPLE"), (922, "NO INSTR."), (970, "AS PERSON")]

    def px(v: float) -> float:
        return L + v * (R - L)

    out: list[str] = []
    for i in range(6):
        t = i * 0.2
        x = px(t)
        if i:
            out.append(
                f'<line x1="{x:g}" y1="56" x2="{x:g}" y2="408" stroke="{ink(0.08)}" stroke-width="0.8"/>'
            )
        out.append(
            _t(x, 440, f"{t:.2f}", anchor="middle", extra=f' data-tick="x" data-value="{t:g}"')
        )
    out.append(f'<line x1="{L}" y1="40" x2="{L}" y2="420" stroke="{ink(0.25)}" stroke-width="1"/>')
    out.append(
        _t(
            (L + R) / 2,
            456,
            "SHARE OF ANSWERS THAT ARE THE ONE NAMED UNDER EACH TEST",
            size=7,
            anchor="middle",
            spacing="0.14em",
        )
    )
    # Column heads are the series marks themselves, so the table needs no words.
    hy = y0 - 30
    out.append(
        f'<line x1="{cols[0][0] - 8}" y1="{hy - 7}" x2="{cols[0][0] - 8}" y2="{hy + 7}" stroke="{MUTED}" stroke-width="2"/>'
    )
    out.append(
        f'<circle cx="{cols[1][0] - 8}" cy="{hy}" r="5" fill="{JEV_PINK}" stroke="{INK}" stroke-width="1"/>'
    )
    out.append(
        f'<circle cx="{cols[2][0] - 8}" cy="{hy}" r="5" fill="{JEV_PROMPT}" stroke="{INK}" stroke-width="1"/>'
    )
    for k, (name, sub, h, neu, typ) in enumerate(rows):
        y = y0 + k * pitch
        xh, xn, xt = px(h), px(neu), px(typ)
        # Each Jev condition sits on its own line just above or below the row, joined
        # to the people tick, so its hairline is its gap from people and no two
        # dots can cover each other however close the values are.
        for xv, dy in ((xn, -7), (xt, 7)):
            out.append(
                f'<line x1="{xh:.1f}" y1="{y + dy}" x2="{xv:.1f}" y2="{y + dy}" stroke="{ink(0.35)}" stroke-width="1"/>'
            )
        out.append(
            f'<line data-series="people" data-value="{h:.4f}" x1="{xh:.1f}" y1="{y - 14}" x2="{xh:.1f}" y2="{y + 14}" stroke="{MUTED}" stroke-width="2"/>'
        )
        out.append(
            f'<circle data-series="neutral" data-value="{neu:.4f}" cx="{xn:.1f}" cy="{y - 7}" r="5" fill="{JEV_PINK}" stroke="{INK}" stroke-width="1"/>'
        )
        out.append(
            f'<circle data-series="typical" data-value="{typ:.4f}" cx="{xt:.1f}" cy="{y + 7}" r="5" fill="{JEV_PROMPT}" stroke="{INK}" stroke-width="1"/>'
        )
        for (x, _h), v in zip(cols, (h, neu, typ), strict=True):
            out.append(_t(x, y + 4, f"{v:.2f}", anchor="end", fill=INK))
        out.append(
            _t(L - 12, y - 1, name, size=11, fill=INK, family=SANS, anchor="end", weight=600)
        )
        out.append(_t(L - 12, y + 12, sub, size=9, fill=MUTED, family=SANS, anchor="end"))
    out.append(_legend(1000, 462, []))
    keys = [
        ("Published human result", f'fill="{PAPER}" stroke="{MUTED}" stroke-width="1.5"'),
        ("Jev 1.13, no instruction", f'fill="{JEV_PINK}" stroke="{INK}" stroke-width="1"'),
        (
            "Jev 1.13, told to answer like a typical person",
            f'fill="{JEV_PROMPT}" stroke="{INK}" stroke-width="1"',
        ),
    ]
    x = 104
    for i, (label, style) in enumerate(keys):
        if i == 0:
            out.append(
                f'<line x1="{x}" y1="486" x2="{x}" y2="500" stroke="{MUTED}" stroke-width="2"/>'
            )
        else:
            out.append(f'<circle cx="{x}" cy="493" r="5" {style}/>')
        out.append(_t(x + 12, 497, label, size=9, family=SANS, fill=INK))
        x += int(12 + text_width(label, 9) + 36)
    out.append(_t(970, 497, "ROWS IN BATTERY ORDER", anchor="end"))
    return Figure(
        slug="jev-decisions",
        eyebrow="Decision-making tests · Jev 1.13",
        title="Jev 1.13 vs. published human results on seven decision-making tests",
        subtitle=(
            "Classic problems from behavioural economics, each asked two ways: with no instruction, and with this "
            f"sentence added first: \u201c{_prompt('typical_human')}\u201d Each row says what was asked and which "
            "answer is counted; some rows count the correct answer, others the typical human error. Jev's value is "
            "the probability it puts on that answer."
        ),
        desc="Dot chart of seven decision-making tests comparing the published human result with Jev 1.13 asked with no instruction and told to answer like a typical person.",
        width=1000,
        height=510,
        body="\n".join(out),
        source="Jev: mean of the probability distributions returned over 10 repeats, run of 18 Sep 2026. "
        "Human results: published studies or meta-analyses, listed in docs/BENCHMARKS.md; different people, "
        "decades and stakes, so a gap of a few points is not meaningful.",
    )


def fig_antisocial(sdf: pd.DataFrame) -> Figure:
    rows = [
        (name, sub, _stat(sdf, i, s, "neutral"), _stat(sdf, i, s, "antisocial"))
        for i, s, _b, name, sub in GAME_MEASURES
    ]
    dt_n = _stat(sdf, "dirty_dozen", "overall", "neutral")
    dt_a = _stat(sdf, "dirty_dozen", "overall", "antisocial")
    body = dumbbell(
        rows,
        ref_name="Jev 1.13, no instruction",
        focal_name="Jev 1.13, antisocial persona",
        ref_fill=JEV_PINK,
        focal_fill=JEV_PROMPT,
        axis_title="share of answers, or share of the money",
        step=0.2,
        domain=(0.0, 1.0),
        order_note="ROWS IN BATTERY ORDER",
    )
    return Figure(
        slug="persona-antisocial",
        eyebrow="Economic games · antisocial persona",
        title="Jev 1.13 in five economic games: no instruction vs. an antisocial persona",
        subtitle=(
            f"The same games, with this sentence added before each: \u201c{_prompt('antisocial')}\u201d "
            f"As a check that the persona took hold, Jev's score on the Dark Triad questionnaire rose from "
            f"{dt_n:.1f} to {dt_a:.1f} out of 9."
        ),
        desc="Dumbbell chart of Jev 1.13's choices in five economic games with no instruction and with an antisocial persona.",
        width=1000,
        height=510,
        body=body,
        source="Mean of returned distributions over 10 repeats, run of 18 Sep 2026. The persona is a prompt: it shows "
        "what the model can be made to output, not a trait it has.",
    )


def fig_dictator(df: pd.DataFrame) -> Figure:
    from .analysis import distributions

    d = distributions(df).get(("dictator_allocation", "neutral", "jev"), {})
    cats = [
        ("$0", ["$0"]),
        ("$1", ["$1"]),
        ("$2", ["$2"]),
        ("$3", ["$3"]),
        ("$4", ["$4"]),
        ("$5", ["$5"]),
        ("$6–10", [f"${v}" for v in range(6, 11)]),
    ]
    vals = [(name, sum(d.get(k, 0.0) for k in keys)) for name, keys in cats]
    focal_i = max(range(len(vals)), key=lambda i: vals[i][1])
    floor, ceil = 0.0, 0.8

    def y(v: float) -> float:
        return 420 - (v - floor) / (ceil - floor) * 380

    pitch, bar = 120, 72
    x0 = 80 + (880 - pitch * len(vals)) / 2
    out: list[str] = []
    for t in [0.0, 0.2, 0.4, 0.6, 0.8]:
        if t > 0:
            out.append(
                f'<line x1="80" y1="{y(t):g}" x2="960" y2="{y(t):g}" stroke="{ink(0.08)}" stroke-width="0.8"/>'
            )
        out.append(
            _t(72, y(t) + 3, f"{t:.1f}", anchor="end", extra=f' data-tick="y" data-value="{t:g}"')
        )
    out.append(f'<line x1="80" y1="420" x2="960" y2="420" stroke="{ink(0.25)}" stroke-width="1"/>')
    out.append(f'<line x1="80" y1="40" x2="80" y2="420" stroke="{ink(0.25)}" stroke-width="1"/>')
    for i, (name, v) in enumerate(vals):
        cx = x0 + i * pitch + pitch / 2
        bx, by, bh = cx - bar / 2, y(v), 420 - y(v)
        focal = i == focal_i
        out.append(
            f'<rect x="{bx:g}" y="{by:.1f}" width="{bar}" height="{bh:.1f}" fill="{PAPER}"/>'
        )
        out.append(
            f'<rect data-value="{v:.4f}" x="{bx:g}" y="{by:.1f}" width="{bar}" height="{bh:.1f}" '
            f'fill="{JEV_PINK}" fill-opacity="{0.75 if focal else 0.4}" stroke="{JEV_PINK_EDGE}" stroke-width="1"/>'
        )
        out.append(
            _t(cx, by - 8, f"{v:.2f}", anchor="middle", fill=JEV_PINK_EDGE if focal else INK)
        )
        out.append(_t(cx, 440, name, size=11, family=SANS, fill=INK, anchor="middle", weight=600))
    out.append(
        _t(
            24,
            230,
            "PROBABILITY",
            size=7,
            spacing="0.14em",
            anchor="middle",
            extra=' transform="rotate(-90 24 230)"',
        )
    )
    out.append(_t(520, 458, "AMOUNT GIVEN OUT OF $10", size=7, spacing="0.14em", anchor="middle"))
    # Two editorial callouts carry the human comparison.
    h0 = BENCHMARKS["dictator_share_zero"].value
    h5 = BENCHMARKS["dictator_share_half"].value
    c0 = x0 + pitch / 2
    c5 = x0 + 5 * pitch + pitch / 2
    out.append(
        _t(
            c0 + 52,
            y(0.62) + 24,
            f"people: {h0:.0%} give nothing",
            size=15,
            family=SERIF,
            fill=INK,
            extra=' font-style="italic"',
        )
    )
    out.append(
        _t(
            c5,
            y(vals[5][1]) - 30,
            f"people: {h5:.0%} split evenly",
            size=15,
            family=SERIF,
            fill=INK,
            anchor="middle",
            extra=' font-style="italic"',
        )
    )
    return Figure(
        slug="dictator-distribution",
        eyebrow="Dictator game · no instruction",
        title="Jev 1.13's answer distribution in the dictator game",
        subtitle=(
            "The game: you are given $10 and decide how much to give an anonymous stranger, who cannot respond. "
            "Each call to Jev returns a probability for every amount from $0 to $10; the bars average 10 calls. "
            "A chat model gives one amount per call, so it would have to be asked many times and its answers "
            "counted to estimate the same shape."
        ),
        desc="Bar chart of Jev's returned probability of giving each amount out of ten dollars in the dictator game; most mass on giving nothing, a second peak at an even split.",
        width=1000,
        height=480,
        body="\n".join(out),
        source="Mean of 10 returned distributions, run of 18 Sep 2026. $6 to $10 are pooled into one bar. "
        "Human shares: Engel (2011) meta-analysis of dictator-game experiments.",
    )


def fig_order_effects(odf: pd.DataFrame) -> Figure:
    """Shuffled multiple-choice cells against the unshuffled floor, as shares of each group."""
    edges = [0.0, 0.025, 0.05, 0.10, 0.15, 0.20]
    names = ["< 0.025", "0.025–0.05", "0.05–0.10", "0.10–0.15", "0.15–0.20", "≥ 0.20"]

    def shares(tv: pd.Series) -> list[float]:
        n = len(tv)
        bands = [((tv >= lo) & (tv < hi)).sum() for lo, hi in itertools.pairwise(edges)]
        bands.append((tv >= edges[-1]).sum())
        return [float(b) / n for b in bands]

    sh = odf[odf["shuffled"]]["mean_tv_distance"]
    un = odf[~odf["shuffled"]]["mean_tv_distance"]
    s_sh, s_un = shares(sh), shares(un)
    ceil = 0.6

    def y(v: float) -> float:
        return 420 - v / ceil * 380

    pitch, bar, gap = 140, 48, 4
    x0 = 80 + (880 - pitch * len(names)) / 2
    out: list[str] = []
    for t in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6]:
        if t:
            out.append(
                f'<line x1="80" y1="{y(t):g}" x2="960" y2="{y(t):g}" stroke="{ink(0.08)}" stroke-width="0.8"/>'
            )
        out.append(
            _t(72, y(t) + 3, f"{t:.0%}", anchor="end", extra=f' data-tick="y" data-value="{t:g}"')
        )
    out.append(f'<line x1="80" y1="420" x2="960" y2="420" stroke="{ink(0.25)}" stroke-width="1"/>')
    out.append(f'<line x1="80" y1="40" x2="80" y2="420" stroke="{ink(0.25)}" stroke-width="1"/>')
    for i, name in enumerate(names):
        cx = x0 + i * pitch + pitch / 2
        for v, bx, fill, stroke, label_fill in (
            (s_sh[i], cx - bar - gap / 2, accent(0.12), ACCENT, ACCENT),
            (s_un[i], cx + gap / 2, muted(0.15), MUTED, MUTED),
        ):
            by = y(v)
            out.append(
                f'<rect x="{bx:g}" y="{by:.1f}" width="{bar}" height="{420 - by:.1f}" fill="{PAPER}"/>'
            )
            out.append(
                f'<rect data-value="{v:.4f}" x="{bx:g}" y="{by:.1f}" width="{bar}" height="{420 - by:.1f}" '
                f'fill="{fill}" stroke="{stroke}" stroke-width="1"/>'
            )
            out.append(
                _t(bx + bar / 2, by - 6, f"{v:.0%}", anchor="middle", fill=label_fill, halo=True)
            )
        out.append(_t(cx, 440, name, size=11, family=SANS, fill=INK, anchor="middle", weight=600))
    out.append(
        _t(
            24,
            230,
            "SHARE OF CELLS IN EACH GROUP",
            size=7,
            spacing="0.14em",
            anchor="middle",
            extra=' transform="rotate(-90 24 230)"',
        )
    )
    out.append(
        _t(
            520,
            458,
            "HOW MUCH THE ANSWER DISTRIBUTION CHANGED BETWEEN REPEATS",
            size=7,
            spacing="0.14em",
            anchor="middle",
        )
    )
    out.append(_legend(1000, 470, []))
    k1 = f"Multiple-choice, options shuffled ({len(sh)} cells, mean {sh.mean():.3f})"
    k2 = f"Likert and yes/no, never shuffled ({len(un)} cells, mean {un.mean():.3f})"
    out.append(
        f'<rect x="104" y="496" width="16" height="10" rx="2" fill="{accent(0.12)}" stroke="{ACCENT}" stroke-width="1"/>'
    )
    out.append(_t(128, 505, k1, size=9, family=SANS, fill=INK))
    x2 = 128 + text_width(k1, 9) + 40
    out.append(
        f'<rect x="{x2:g}" y="496" width="16" height="10" rx="2" fill="{muted(0.15)}" stroke="{MUTED}" stroke-width="1"/>'
    )
    out.append(_t(x2 + 24, 505, k2, size=9, family=SANS, fill=INK))
    return Figure(
        slug="order-effects",
        eyebrow="Option order · all four prompts",
        title="How much Jev 1.13's answers change when the order of the options is shuffled",
        subtitle=(
            "Each item was asked 10 times. For multiple-choice items the options were put in a new random order "
            "every time; Likert and yes/no items were left as they were, so they show how much the answers vary "
            "with nothing changed. The measure is total-variation distance between two answer distributions: "
            "0 means identical, 1 means no overlap at all."
        ),
        desc="Grouped bar chart comparing how much Jev 1.13's answers changed between repeats for multiple-choice items with shuffled options and for unshuffled Likert and yes/no items.",
        width=1000,
        height=520,
        body="\n".join(out),
        source="Mean distance over all pairs of the 10 repeats, per item and prompt; run of 18 Sep 2026. "
        "Bands are unequal: finer near zero, where most cells sit.",
    )


SHORT = {
    "typesafe/jev-1.13-20260917": "Jev 1.13",
    "openai/gpt-6-luna-decisions-20261006": "GPT-6 Luna Decisions",
    "microsoft/microsoft-decision-1-20261009": "Microsoft-Decision-1",
    "perplexity/pplx-decider-v1.1-27b-20261006": "Decider v1.1 27B",
    "inception/mercury-decide-20260930": "Mercury Decide",
    "liquid/d1-20260930": "d1",
    "upstage/solar-decide-20260928": "Solar Decide",
    "upstage/solar-decide-flash-20261008": "Solar Decide Flash",
    "nace-ai/drex-v1.5-20261009": "Drex 1.5",
    "cloudflare/clef-flash": "Clef Flash",
    "anthropic/claude-sonnet-5": "Claude Sonnet 5",
    "anthropic/claude-haiku-5.5": "Claude Haiku 5.5",
}


MAKER = {
    "typesafe": "TypeSafe",
    "openai": "OpenAI",
    "microsoft": "Microsoft",
    "perplexity": "Perplexity",
    "inception": "Inception",
    "liquid": "Liquid AI",
    "upstage": "Upstage",
    "nace-ai": "Nace AI",
    "cloudflare": "Cloudflare",
    "anthropic": "Anthropic",
}

Box = tuple[float, float, float, float]  # x0, y0, x1, y1


def _overlaps(a: Box, b: Box, pad: float = 0.0) -> bool:
    return not (
        a[2] + pad <= b[0] or b[2] + pad <= a[0] or a[3] + pad <= b[1] or b[3] + pad <= a[1]
    )


def _segment_hits(x0: float, y0: float, x1: float, y1: float, box: Box) -> bool:
    for i in range(1, 40):
        t = i / 40
        x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
        if box[0] <= x <= box[2] and box[1] <= y <= box[3]:
            return True
    return False


def _segments_cross(
    a: tuple[float, float, float, float], b: tuple[float, float, float, float]
) -> bool:
    def orient(px: float, py: float, qx: float, qy: float, rx: float, ry: float) -> float:
        return (qx - px) * (ry - py) - (qy - py) * (rx - px)

    d1 = orient(b[0], b[1], b[2], b[3], a[0], a[1])
    d2 = orient(b[0], b[1], b[2], b[3], a[2], a[3])
    d3 = orient(a[0], a[1], a[2], a[3], b[0], b[1])
    d4 = orient(a[0], a[1], a[2], a[3], b[2], b[3])
    return (d1 * d2 < 0) and (d3 * d4 < 0)


def _box_distance(box: Box, x: float, y: float) -> float:
    dx = max(box[0] - x, 0.0, x - box[2])
    dy = max(box[1] - y, 0.0, y - box[3])
    return math.hypot(dx, dy)


def place_labels(
    points: list[tuple[str, float, float, float]],
    *,
    size: float,
    bounds: Box,
    reserved: list[Box],
) -> dict[str, tuple[float, float, str, Box, tuple[float, float, float, float] | None]]:
    """Put a label on every point with no label touching a point, a label or a leader.

    Greedy, most crowded point first: try positions round the point at growing
    distances, take the nearest that collides with nothing, and draw a hairline
    leader whenever the label had to move away from its point.
    """
    h = size + 5
    marks: list[Box] = [(x - r - 3, y - r - 3, x + r + 3, y + r + 3) for _, x, y, r in points]
    placed: list[Box] = list(reserved)
    leaders: list[tuple[float, float, float, float]] = []
    out: dict[str, tuple[float, float, str, Box, tuple[float, float, float, float] | None]] = {}

    def crowd(p: tuple[str, float, float, float]) -> int:
        return sum(
            1 for o in points if o is not p and abs(o[1] - p[1]) < 90 and abs(o[2] - p[2]) < 40
        )

    for name, cx, cy, r in sorted(points, key=lambda p: -crowd(p)):
        w = text_width(name, size) + 6
        best = None
        for d in (
            r + 6,
            r + 18,
            r + 32,
            r + 48,
            r + 66,
            r + 88,
            r + 112,
            r + 140,
            r + 172,
            r + 210,
        ):
            for ux, uy in ((1, 0), (-1, 0), (0, -1), (0, 1), (1, -1), (-1, -1), (1, 1), (-1, 1)):
                lx = cx + ux * d
                ly = cy + uy * d
                if ux > 0:
                    box = (lx, ly - h / 2, lx + w, ly + h / 2)
                    anchor = "start"
                elif ux < 0:
                    box = (lx - w, ly - h / 2, lx, ly + h / 2)
                    anchor = "end"
                else:
                    box = (lx - w / 2, ly - h / 2, lx + w / 2, ly + h / 2)
                    anchor = "middle"
                if (
                    box[0] < bounds[0]
                    or box[2] > bounds[2]
                    or box[1] < bounds[1]
                    or box[3] > bounds[3]
                ):
                    continue
                if any(_overlaps(box, m) for m in marks) or any(
                    _overlaps(box, q, 3) for q in placed
                ):
                    continue
                leader = None
                if d > r + 10:
                    # The leader runs from the point's edge to the nearest edge of the label.
                    tx = min(max(cx, box[0]), box[2])
                    ty = min(max(cy, box[1]), box[3])
                    dist = math.hypot(tx - cx, ty - cy) or 1.0
                    sx, sy = cx + (tx - cx) / dist * (r + 1), cy + (ty - cy) / dist * (r + 1)
                    leader = (sx, sy, tx, ty)
                    others = [m for m, p in zip(marks, points, strict=True) if p[0] != name]
                    if any(_segment_hits(*leader, m) for m in others + placed):
                        continue
                    if any(_segments_cross(leader, q) for q in leaders):
                        continue
                # A label without a leader must read as its own point's: nearer to
                # it than to any other point. A leader makes the pairing explicit.
                own = _box_distance(box, cx, cy)
                if leader is None and any(
                    _box_distance(box, ox, oy) < own + 6 for on, ox, oy, _r in points if on != name
                ):
                    continue
                if best is None or d < best[0]:
                    best = (d, lx, ly, anchor, box, leader)
            if best is not None:
                break
        if best is None:
            raise ValueError(f"no room to label {name!r}")
        _, lx, ly, anchor, box, leader = best
        placed.append(box)
        if leader:
            leaders.append(leader)
        out[name] = (lx, ly + size * 0.35, anchor, box, leader)
    return out


def fig_models_scatter(fdf: pd.DataFrame) -> Figure:
    piv = fdf.pivot(index="model", columns="persona", values="mae")
    types = {str(m): str(t) for m, t in zip(fdf["model"], fdf["type"], strict=False)}
    pts = [
        (SHORT.get(str(m), str(m)), float(r["neutral"]), float(r["typical_human"]), types[str(m)])
        for m, r in piv.iterrows()
    ]
    if len(pts) > 30:
        raise ValueError("scatter caps at 30 points")
    # The axes are zoomed to where the models are, so every one can be named;
    # the source line states the bounds, as the scatter honesty rule asks.
    x0, x1, y0, y1 = 0.15, 0.55, 0.05, 0.35
    left, right, top, bottom = 80, 960, 40, 520

    def X(v: float) -> float:
        return left + (v - x0) / (x1 - x0) * (right - left)

    def Y(v: float) -> float:
        return bottom - (v - y0) / (y1 - y0) * (bottom - top)

    focal = max(pts, key=lambda p: p[2] - p[1])  # the one that moved least (or moved away)
    out: list[str] = []
    for i in range(9):
        t = round(x0 + i * 0.05, 2)
        if i:
            out.append(
                f'<line x1="{X(t):g}" y1="{top}" x2="{X(t):g}" y2="{bottom}" stroke="{ink(0.08)}" stroke-width="0.8"/>'
            )
        out.append(
            _t(
                X(t),
                bottom + 20,
                f"{t:.2f}",
                anchor="middle",
                extra=f' data-tick="x" data-value="{t:g}"',
            )
        )
    for i in range(7):
        t = round(y0 + i * 0.05, 2)
        if i:
            out.append(
                f'<line x1="{left}" y1="{Y(t):g}" x2="{right}" y2="{Y(t):g}" stroke="{ink(0.08)}" stroke-width="0.8"/>'
            )
        out.append(
            _t(
                left - 8,
                Y(t) + 3,
                f"{t:.2f}",
                anchor="end",
                extra=f' data-tick="y" data-value="{t:g}"',
            )
        )
    out.append(
        f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" stroke="{ink(0.25)}" stroke-width="1"/>'
    )
    out.append(
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" stroke="{ink(0.25)}" stroke-width="1"/>'
    )
    # The no-change diagonal: below it, asking for a typical person brought the model closer to people.
    out.append(
        f'<line x1="{X(0.15):g}" y1="{Y(0.15):g}" x2="{X(0.35):g}" y2="{Y(0.35):g}" stroke="{ink(0.35)}" stroke-width="1" stroke-dasharray="4,3"/>'
    )
    tag = "NO CHANGE"
    tw = text_width(tag, 8, True) + 8
    # Beside the line where it meets the top of the plot, below and right of it.
    nx, ny = X(0.335) + 8, Y(0.335) + 6
    tag_box = (nx, ny - 9, nx + tw, ny + 3)
    out.append(
        f'<rect x="{tag_box[0]:g}" y="{tag_box[1]:g}" width="{tw:g}" height="12" rx="2" fill="{PAPER}"/>'
    )
    out.append(_t(nx + 4, ny, tag, spacing="0.06em"))
    note = "below the line: closer to people when told"
    note_x, note_y = X(0.53), Y(0.075)
    note_box = (note_x - text_width(note, 15) * 0.8, note_y - 16, note_x, note_y + 4)
    out.append(
        _t(
            note_x,
            note_y,
            note,
            size=15,
            family=SERIF,
            fill=INK,
            anchor="end",
            extra=' font-style="italic"',
        )
    )

    size = 10.0
    marks = [(n, X(xn), Y(yt), 6.0 if n == focal[0] else 5.0) for n, xn, yt, _ in pts]
    labels = place_labels(
        marks,
        size=size,
        bounds=(left + 4, top + 4, right - 4, bottom - 4),
        reserved=[tag_box, note_box],
    )
    for _lx, _ly, _anchor, _box, leader in labels.values():
        if leader:
            out.append(
                f'<line x1="{leader[0]:.1f}" y1="{leader[1]:.1f}" x2="{leader[2]:.1f}" y2="{leader[3]:.1f}" stroke="{ink(0.45)}" stroke-width="0.8"/>'
            )
    for name, xn, yt, typ in sorted(pts, key=lambda p: p[0] == focal[0]):
        cx, cy = X(xn), Y(yt)
        is_focal = name == focal[0]
        r = 6 if is_focal else 5
        out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="{PAPER}"/>')
        if is_focal:
            mark = f'fill="{accent(0.15)}" stroke="{ACCENT}" stroke-width="1.2"'
        elif name == "Jev 1.13":
            mark = f'fill="{JEV_PINK}" stroke="{INK}" stroke-width="1"'
        elif name == "Claude Haiku 5.5":
            mark = f'fill="{ANTHROPIC_ORANGE}" stroke="{INK}" stroke-width="1"'
        elif typ != "System One":
            mark = f'fill="{PAPER}" stroke="{MUTED}" stroke-width="1.5"'
        else:
            mark = f'fill="{muted(0.20)}" stroke="{MUTED}" stroke-width="1"'
        out.append(
            f'<circle data-name="{esc(name)}" data-x="{xn:.4f}" data-y="{yt:.4f}" cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" {mark}/>'
        )
    for name, (lx, ly, anchor, box, _leader) in labels.items():
        out.append(
            f'<rect x="{box[0]:.1f}" y="{box[1]:.1f}" width="{box[2] - box[0]:.1f}" height="{box[3] - box[1]:.1f}" rx="2" fill="{PAPER}"/>'
        )
        out.append(
            _t(
                round(lx + (3 if anchor == "start" else -3 if anchor == "end" else 0), 1),
                round(ly, 1),
                name,
                size=size,
                family=SANS,
                fill=INK,
                weight=500,
                anchor=anchor,
                extra=f' data-name="{esc(name)}" data-role="label"',
            )
        )
    mid_y = (top + bottom) / 2
    out.append(
        _t(
            24,
            mid_y,
            "AS A TYPICAL PERSON",
            size=7,
            spacing="0.14em",
            anchor="middle",
            extra=f' transform="rotate(-90 24 {mid_y:g})"',
        )
    )
    out.append(
        _t(
            (left + right) / 2,
            bottom + 38,
            "ANSWERING NEUTRALLY",
            size=7,
            spacing="0.14em",
            anchor="middle",
        )
    )
    ly0 = bottom + 50
    out.append(_legend(1000, ly0, []))
    out.append(
        f'<circle cx="104" cy="{ly0 + 31}" r="5" fill="{muted(0.20)}" stroke="{MUTED}" stroke-width="1"/>'
    )
    out.append(_t(116, ly0 + 35, "System One model", size=9, family=SANS, fill=INK))
    out.append(
        f'<circle cx="244" cy="{ly0 + 31}" r="5" fill="{PAPER}" stroke="{MUTED}" stroke-width="1.5"/>'
    )
    out.append(_t(256, ly0 + 35, "Chat model, resampled", size=9, family=SANS, fill=INK))
    out.append(
        f'<circle cx="412" cy="{ly0 + 31}" r="6" fill="{accent(0.15)}" stroke="{ACCENT}" stroke-width="1.2"/>'
    )
    out.append(
        _t(
            424,
            ly0 + 35,
            f"{focal[0]}: the only model above the line",
            size=9,
            family=SANS,
            fill=INK,
        )
    )
    jx = int(424 + text_width(f"{focal[0]}: the only model above the line", 9) + 40)
    out.append(
        f'<circle cx="{jx}" cy="{ly0 + 31}" r="5" fill="{JEV_PINK}" stroke="{INK}" stroke-width="1"/>'
    )
    out.append(_t(jx + 12, ly0 + 35, "Jev 1.13", size=9, family=SANS, fill=INK))
    hx = int(jx + 12 + text_width("Jev 1.13", 9) + 36)
    out.append(
        f'<circle cx="{hx}" cy="{ly0 + 31}" r="5" fill="{ANTHROPIC_ORANGE}" stroke="{INK}" stroke-width="1"/>'
    )
    out.append(_t(hx + 12, ly0 + 35, "Claude Haiku 5.5", size=9, family=SANS, fill=INK))
    return Figure(
        slug="models-scatter",
        eyebrow="Eleven models · no instruction vs. told to answer like a typical person",
        title="Distance from published human results, with and without the \u2018typical person\u2019 instruction",
        subtitle=(
            "Each point is one model. Distance is the mean absolute difference from the published human result "
            "over the 14 measures in the decision-making and economic-game charts, each on a 0\u20131 scale, so 0 "
            "would mean identical to people. Across: no instruction. Up: told to answer like a typical person. "
            "Points below the dashed line moved closer to people when told."
        ),
        desc="Scatter of eleven models' mean distance from human values answering neutrally versus as a typical person; all but Drex 1.5 fall below the no-change line.",
        width=1000,
        height=ly0 + 50,
        body="\n".join(out),
        source="Axes zoomed to the data: 0.15–0.55 across, 0.05–0.35 up, not from zero. Jev and Claude Sonnet 5 "
        "run 18 Sep 2026, all others 12 Oct 2026; 14 measures on a shared 0–1 scale, 10 replicates or samples "
        "per cell. Distance alone is not a ranking: see the framing figure.",
    )


def _cell(df: pd.DataFrame, row: str, col: str) -> float:
    return float(str(df.at[row, col]))


def fig_framing(mdf: pd.DataFrame) -> Figure:
    s = {p: mdf[mdf.persona == p].set_index("measure") for p in ("neutral", "typical_human")}

    def contrast(model: str, p: str) -> float:
        t = s[p]
        gain = _cell(t, "Framing: certain (gain)", model)
        loss = _cell(t, "Framing: certain (loss)", model)
        return (gain - loss) * 100

    human = (
        float(
            _cell(s["neutral"], "Framing: certain (gain)", "human")
            - _cell(s["neutral"], "Framing: certain (loss)", "human")
        )
        * 100
    )
    keep = [m for m in mdf.columns if m in SHORT and "anthropic" not in m and "mercury" not in m]
    rows = sorted(
        [
            (
                SHORT[m],
                f"{MAKER[m.split('/')[0]]} · System One model",
                contrast(m, "neutral"),
                contrast(m, "typical_human"),
            )
            for m in keep
        ],
        key=lambda r: -r[3],
    )
    body = dumbbell(
        rows,
        ref_name="No instruction",
        focal_name="Told to answer like a typical person",
        row_ref_fill={"Jev 1.13": (JEV_PINK, "Jev 1.13, no instruction")},
        row_focal_fill={"Jev 1.13": (JEV_PROMPT, "Jev 1.13, told")},
        axis_title="gain-frame minus loss-frame rate of picking the sure option, in points",
        step=20,
        fmt="{:.0f}",
        order_note="ROWS BY THE AS-A-PERSON VALUE",
        reference_line=(human, f"PEOPLE {human:.0f}"),
    )
    return Figure(
        slug="framing-contrast",
        eyebrow="Framing effect · eight System One models",
        title="Size of the framing effect by model, in the disease problem",
        subtitle=(
            "The same choice between a sure and a risky programme against a disease, worded once as lives saved "
            "and once as lives lost. People pick the sure option 72% of the time in the gain wording and 22% in "
            "the loss wording, a 50-point swing. Each row is a model's swing in points; below zero, it picks the "
            "sure option more often in the loss wording, the reverse of people. Solar Decide Flash, which has the "
            "smallest overall distance from human results in the scatter, swings 9 points with no "
            "instruction and 4 when told to answer like a typical person."
        ),
        desc="Dumbbell chart of eight System One models' framing reversal in points, answering neutrally and as a typical person, against the human value of 50.",
        width=1000,
        height=510,
        body=body,
        source="The chart holds eight rows, so Mercury Decide (19 with no instruction, 34 as a typical person) is "
        "given here. The two chat models swing all or nothing: Claude Sonnet 5 100 and 100, Claude Haiku 5.5 0 and "
        "100. Human rates: Tversky & Kahneman (1981). Jev run 18 Sep 2026, others 12 Oct 2026.",
    )


# -- schematics ----------------------------------------------------------------


def _node(
    x: int, y: int, w: int, h: int, name: str, sub: str, *, kind: str = "backend", tag: str = ""
) -> str:
    fill, stroke = {
        "backend": (WHITE, INK),
        "focal": (accent(0.08), ACCENT),
        "external": (ink(0.03), ink(0.30)),
        "store": (ink(0.05), MUTED),
    }[kind]
    if text_width(name, 12) > w - 16 or text_width(sub, 9, True) > w - 16:
        raise ValueError(f"label does not fit its node: {name!r} / {sub!r}")
    cx = x + w / 2
    parts = [
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{PAPER}"/>',
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" stroke="{stroke}" stroke-width="1"/>',
    ]
    ty = y + h / 2 + (4 if not tag else 8)
    if tag:
        tw = max(28, int(text_width(tag, 7, True)) + 12)
        tw += (-tw) % 4
        tag_stroke = accent(0.4) if kind == "focal" else ink(0.4)
        tag_fill = ACCENT if kind == "focal" else MUTED
        parts.append(
            f'<rect x="{x + 8}" y="{y + 6}" width="{tw}" height="12" rx="2" fill="transparent" stroke="{tag_stroke}" stroke-width="0.8"/>'
        )
        parts.append(
            _t(
                x + 8 + tw / 2,
                y + 15,
                tag,
                size=7,
                fill=tag_fill,
                anchor="middle",
                spacing="0.08em",
            )
        )
    parts.append(_t(cx, ty, name, size=12, family=SANS, fill=INK, anchor="middle", weight=600))
    parts.append(_t(cx, ty + 16, sub, size=9, fill=MUTED, anchor="middle"))
    return "\n".join(parts)


def fig_process() -> Figure:
    W, H = 960, 660
    w, h = 160, 64
    cols = [24, 212, 400, 588, 776]
    mid, top, bot = 200, 104, 296  # connector y-levels
    a: list[str] = []
    # Arrows first, so nodes sit on top of them.
    a.append(
        f'<line x1="{cols[0] + w}" y1="{mid}" x2="{cols[1]}" y2="{mid}" stroke="{MUTED}" stroke-width="1" marker-end="url(#arrow)"/>'
    )
    gx = cols[1] + w + 14  # vertical channel between columns 2 and 3
    a.append(
        f'<path d="M{cols[1] + w} 188 H{gx - 8} Q{gx} 188 {gx} 180 V{top + 8} Q{gx} {top} {gx + 8} {top} H{cols[2]}" fill="none" stroke="{ACCENT}" stroke-width="1.2" marker-end="url(#arrow-accent)"/>'
    )
    a.append(
        f'<path d="M{cols[1] + w} 212 H{gx - 8} Q{gx} 212 {gx} 220 V{bot - 8} Q{gx} {bot} {gx + 8} {bot} H{cols[2]}" fill="none" stroke="{MUTED}" stroke-width="1" marker-end="url(#arrow)"/>'
    )
    hx = cols[2] + w + 14
    a.append(
        f'<path d="M{cols[2] + w} {top} H{hx - 8} Q{hx} {top} {hx} {top + 8} V180 Q{hx} 188 {hx + 8} 188 H{cols[3]}" fill="none" stroke="{ACCENT}" stroke-width="1.2" marker-end="url(#arrow-accent)"/>'
    )
    a.append(
        f'<path d="M{cols[2] + w} {bot} H{hx - 8} Q{hx} {bot} {hx} {bot - 8} V220 Q{hx} 212 {hx + 8} 212 H{cols[3]}" fill="none" stroke="{MUTED}" stroke-width="1" marker-end="url(#arrow)"/>'
    )
    a.append(
        f'<line x1="{cols[3] + w}" y1="{mid}" x2="{cols[4]}" y2="{mid}" stroke="{MUTED}" stroke-width="1" marker-end="url(#arrow)"/>'
    )
    a.append(
        f'<line x1="{cols[4] + w // 2}" y1="328" x2="{cols[4] + w // 2}" y2="232" stroke="{LINK}" stroke-width="1" stroke-dasharray="5,4" marker-end="url(#arrow-link)"/>'
    )
    # Nodes.
    a.append(_node(cols[0], mid - h // 2, w, h, "One test item", "e.g. bat and ball", tag="ITEM"))
    a.append(_node(cols[1], mid - h // 2, w, h, "Four prompts", "listed above", tag="PROMPT"))
    a.append(
        _node(
            cols[2],
            top - h // 2,
            w,
            h,
            "System One model",
            "10 × full distribution",
            kind="focal",
            tag="SYSTEM ONE",
        )
    )
    a.append(_node(cols[2], bot - h // 2, w, h, "Chat model", "10 × one answer", tag="CHAT"))
    a.append(
        _node(
            cols[3],
            mid - h // 2,
            w,
            h,
            "One distribution",
            "per item and prompt",
            kind="store",
            tag="CELL",
        )
    )
    a.append(
        _node(
            cols[4],
            mid - h // 2,
            w,
            h,
            "Compared with people",
            "distance · correlation",
            tag="RESULT",
        )
    )
    a.append(
        _node(cols[4], 328, w, h, "Human result", "published study", kind="external", tag="DATA")
    )
    # Two callouts carry the cost asymmetry.
    a.append(
        _t(
            cols[2] + w / 2,
            top - h // 2 - 16,
            "distributions averaged: $0.09 for the run",
            size=15,
            family=SERIF,
            fill=INK,
            anchor="middle",
            extra=' font-style="italic"',
        )
    )
    a.append(
        _t(
            cols[2] + w / 2,
            bot + h // 2 + 26,
            "answers counted: $2.74 for the same run",
            size=15,
            family=SERIF,
            fill=INK,
            anchor="middle",
            extra=' font-style="italic"',
        )
    )
    # The chat path in detail: a chat model answers in free text, so how a reply
    # becomes an answer (and what happens when it cannot) is part of the method.
    sy, sh = 384, 160  # strip container
    sx, sw = cols[0] - 8, cols[3] + w + 8 - (cols[0] - 8)
    a.append(
        f'<rect x="{sx}" y="{sy}" width="{sw}" height="{sh}" rx="8" fill="{ink(0.02)}" stroke="{ink(0.18)}" stroke-width="0.8" stroke-dasharray="4,3"/>'
    )
    a.append(
        _t(
            sx + 12,
            sy + 18,
            "CHAT MODEL PATH IN DETAIL: HOW A REPLY BECOMES AN ANSWER",
            size=7,
            spacing="0.14em",
        )
    )
    by = sy + 30
    steps = [
        ("Options listed", "'reply with one key'", "ASK"),
        ("Room to reason", "512 tokens; Haiku 4,096", "CAP"),
        ("Reply read", "exact key in 94–99%", "PARSE"),
        ("Unreadable: dropped", "counted, not guessed", "GAP"),
    ]
    for i, (name, sub, tag) in enumerate(steps):
        if i:
            a.append(
                f'<line x1="{cols[i - 1] + w}" y1="{by + h // 2}" x2="{cols[i]}" y2="{by + h // 2}" stroke="{MUTED}" stroke-width="1" marker-end="url(#arrow)"/>'
            )
        a.append(_node(cols[i], by, w, h, name, sub, tag=tag))
    notes = [
        "Not exactly a key? The last option the reply names counts, and a leading key wins: \u201c$1: Offer $1, keep $9\u201d is $1.",
        "Unreadable (empty, cut off, no option named): Claude Sonnet 5, 9 of 4,680 replies; Claude Haiku 5.5, 3 of 5,440.",
        "The 11 items asking what proportion of people said yes get no chat score: ten true/false replies are a vote.",
    ]
    for j, line in enumerate(notes):
        a.append(_t(sx + 12, by + h + 22 + 15 * j, line, size=10, family=SANS, fill=INK))
    a.append(_legend(W, 576, []))
    legend = [
        (accent(0.08), ACCENT, "System One model path", 0),
        (WHITE, INK, "Step", 1),
        (ink(0.05), MUTED, "Stored result", 0),
        (ink(0.03), ink(0.30), "External data", 0),
    ]
    x = 104
    for fill, stroke, label, _ in legend:
        a.append(
            f'<rect x="{x}" y="606" width="16" height="10" rx="2" fill="{fill}" stroke="{stroke}" stroke-width="1"/>'
        )
        a.append(_t(x + 24, 615, label, size=9, family=SANS, fill=INK))
        x += int(24 + text_width(label, 9) + 40)
    return Figure(
        slug="how-it-works",
        eyebrow="Method",
        title="How each test item is run and scored",
        subtitle=(
            "Each item is asked under four prompts: no instruction, \u2018answer like a typical person\u2019, "
            "\u2018answer like a rational agent\u2019 and an antisocial persona. Each model is asked "
            "every item ten times under each prompt. A System One model returns a probability for every possible "
            "answer on each call, and the ten distributions are averaged. A chat model returns one answer per call as text, "
            "which is read for the option it names, and the ten answers are counted. Either way the result is one distribution per item and prompt, "
            "compared with the published human result for that test."
        ),
        desc="Process diagram: a battery item is framed four ways, asked ten times of either a System One model or a chat model, whose text replies are read for an option key with unreadable ones dropped and counted, reduced to one distribution per cell, and compared with a published human rate.",
        width=W,
        height=H,
        body="\n".join(a),
        source="Costs are for the same 4,680 questions on 18 Sep 2026 (117 items × 4 prompts × 10): Jev 1.13 "
        "$0.09, Claude Sonnet 5 $2.74. The battery has 147 items since 30 follow-up items were added.",
    )


def fig_health() -> Figure:
    W, H = 960, 440
    w, h = 280, 64
    cols = [24, 340, 656]
    rows = [
        (
            "GPT-6 Luna refused 4%",
            "240 calls → HTTP 502",
            "Refusals reported as a 502",
            "client retried them 5 times",
            "Counted as refusals",
            "never retried; in health.csv",
            "focal",
        ),
        (
            "Both Solar models lost an item",
            "p-beauty contest, 40 calls",
            "Route caps Choice at 26",
            "the item has 101 options",
            "Disclosed, not imputed",
            "one item fewer, stated",
            "backend",
        ),
        (
            "Haiku 5.5 replied with nothing",
            "183 calls, finish = length",
            "Reasoning used the cap",
            "all 512 tokens, no answer",
            "Cap raised and recorded",
            "4,096 → 3 unresolved",
            "focal",
        ),
    ]
    a: list[str] = []
    ys = [64, 164, 264]
    for y in ys:
        cy = y + h // 2
        a.append(
            f'<line x1="{cols[0] + w}" y1="{cy}" x2="{cols[1]}" y2="{cy}" stroke="{MUTED}" stroke-width="1" marker-end="url(#arrow)"/>'
        )
        a.append(
            f'<line x1="{cols[1] + w}" y1="{cy}" x2="{cols[2]}" y2="{cy}" stroke="{MUTED}" stroke-width="1" marker-end="url(#arrow)"/>'
        )
    for x, head in zip(cols, ["WHAT THE COUNTS SHOWED", "WHY", "WHAT CHANGED"], strict=True):
        a.append(_t(x, 44, head, size=7, spacing="0.14em"))
    for y, (n1, s1, n2, s2, n3, s3, kind3) in zip(ys, rows, strict=True):
        a.append(_node(cols[0], y, w, h, n1, s1))
        a.append(_node(cols[1], y, w, h, n2, s2, kind="external"))
        a.append(_node(cols[2], y, w, h, n3, s3, kind=kind3))
    a.append(_legend(W, 372, []))
    x = 104
    for fill, stroke, label in [
        (accent(0.08), ACCENT, "A bug in this repository, fixed"),
        (WHITE, INK, "Outcome"),
        (ink(0.03), ink(0.30), "Cause outside the repository's control"),
    ]:
        a.append(
            f'<rect x="{x}" y="402" width="16" height="10" rx="2" fill="{fill}" stroke="{stroke}" stroke-width="1"/>'
        )
        a.append(_t(x + 24, 411, label, size=9, family=SANS, fill=INK))
        x += int(24 + text_width(label, 9) + 40)
    return Figure(
        slug="health-checks",
        eyebrow="Data quality · 12 Oct multi-model run",
        title="Three problems found by the per-model error checks, and what was done",
        subtitle=(
            "For each model the comparison counts errors, refusals, replies that could not be matched to an answer, "
            "and items left with no usable answer (results/comparison/health.csv). A reply that arrives but cannot "
            "be used is not a network error, so nothing would flag it without these counts. Two of the three "
            "problems were bugs in this repository."
        ),
        desc="Process diagram of three problems the health table caught: GPT-6 Luna Decisions refusals, the Solar models' option cap, and Claude Haiku 5.5 truncating on reasoning, each with its cause and fix.",
        width=W,
        height=H,
        body="\n".join(a),
        source="results/comparison/health.csv. The truncated Haiku run was discarded and re-run, not mixed in.",
    )


# -- build and export ----------------------------------------------------------------


def build_diagrams(
    run_path: Path, tables_dir: Path, comparison_dir: Path, out_dir: Path
) -> list[Path]:
    from .analysis import load_records

    sdf = pd.read_csv(tables_dir / "statistics.csv")
    odf = pd.read_csv(tables_dir / "order_effects.csv")
    fdf = pd.read_csv(comparison_dir / "fidelity.csv")
    mdf = pd.read_csv(comparison_dir / "measures.csv")
    df = load_records(run_path)

    figures = [
        fig_process(),
        fig_jev_decisions(sdf),
        fig_jev_vs_people(sdf, "games", "neutral"),
        fig_antisocial(sdf),
        fig_dictator(df),
        fig_order_effects(odf),
        fig_models_scatter(fdf),
        fig_framing(mdf),
        fig_health(),
    ]
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for f in figures:
        p = out_dir / f"{f.slug}.html"
        p.write_text(f.html(), encoding="utf-8")
        paths.append(p)
    return paths


def export_pngs(html_paths: list[Path], out_dir: Path, scale: int = 2) -> list[Path]:
    """Render each page's diagram, with its title and source line, to PNG."""
    from playwright.sync_api import sync_playwright

    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    with sync_playwright() as pw:
        # A pinned Chromium (e.g. one preinstalled for a different Playwright
        # version) can be named with JEVBENCH_CHROMIUM instead of downloading.
        exe = os.environ.get("JEVBENCH_CHROMIUM")
        browser = pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()
        page = browser.new_page(device_scale_factor=scale, viewport={"width": 1280, "height": 900})
        for path in html_paths:
            page.goto(path.resolve().as_uri())
            page.wait_for_load_state("networkidle")
            page.evaluate("document.fonts.ready")
            target = out_dir / f"{path.stem}.png"
            page.locator(".frame").screenshot(path=str(target))
            written.append(target)
        browser.close()
    return written


def main(argv: Any = None) -> int:
    import argparse

    from .config import RAW_DIR, REPO_ROOT, TABLES_DIR

    ap = argparse.ArgumentParser(description="build the editorial figures")
    ap.add_argument("--run", default=str(RAW_DIR / "run_live_20260918T230710Z.jsonl"))
    ap.add_argument("--no-png", action="store_true")
    args = ap.parse_args(argv)
    html_dir = REPO_ROOT / "docs" / "diagrams"
    paths = build_diagrams(
        Path(args.run), TABLES_DIR, REPO_ROOT / "results" / "comparison", html_dir
    )
    for p in paths:
        print(f"wrote {p.relative_to(REPO_ROOT)}")
    if not args.no_png:
        for p in export_pngs(paths, REPO_ROOT / "results" / "figures"):
            print(f"wrote {p.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
