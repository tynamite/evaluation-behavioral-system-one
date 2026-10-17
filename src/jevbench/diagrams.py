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
import math
import os
import sys
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
ACCENT = "#157a6e"  # teal, for the schematics' System One path only (4.8:1 on paper)
LINK = "#2e5aa8"
WHITE = "#ffffff"
# One rule in every chart: colour (with shape, where marks share a row) says
# which model; hollow against filled says which condition (no instruction
# against a prompt, one pick per call against the full distribution). People
# are always slate.
#
# Jev 1.13 is hot pink, Jev 1.14 the deeper magenta of the same family, so
# both read as Jev and still tell apart. The pink is too light to be a mark's
# only edge (2.4:1 on paper), so it takes JEV_PINK_EDGE (4.6:1) as its edge.
JEV_PINK = "#ff69b4"
JEV_PINK_EDGE = "#d6126f"
JEV_114 = "#a3195b"
# Claude Haiku 5.5 is the one chat model with its own colour: Anthropic orange.
# Too light to be its own edge (2.9:1), so it keeps an ink outline.
ANTHROPIC_ORANGE = "#d97757"


def ink(a: float) -> str:
    return f"rgba(45,49,66,{a})"


def accent(a: float) -> str:
    return f"rgba(21,122,110,{a})"


def muted(a: float) -> str:
    return f"rgba(79,93,117,{a})"


# The small credit in each figure's bottom-right corner, inside the PNG export.
WATERMARK = "github.com/tynamite"

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

    @property
    def top(self) -> int:
        """Where the drawing starts: charts lay out from y=0 but rarely draw there,
        and the empty band would otherwise sit between the subtitle and the plot."""
        return max(0, int(_content_top(self.body)) - 12)

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
    .frame {{ max-width: {self.width + 80}px; width: 100%; padding: 32px 40px; background: var(--color-paper);
      position: relative; }}
    .mark {{ position: absolute; right: 40px; bottom: 12px; font-family: var(--font-mono); font-size: 0.6rem;
      letter-spacing: 0.14em; color: var(--color-muted); opacity: 0.55; }}
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
      max-width: 60rem; margin-bottom: 1rem; }}
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
      <svg viewBox="0 {self.top} {self.width} {self.height - self.top}" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="{self.slug}-title {self.slug}-desc">
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
    <p class="mark" aria-hidden="true">{WATERMARK}</p>
  </div>
</body>
</html>
"""


# -- shared chart pieces -----------------------------------------------------


def _content_top(body: str) -> float:
    """The smallest y any element of `body` reaches, ignoring rotated text.

    Text is measured from its baseline up by its font size; paths from the y
    coordinates in their data. It need only be close: `Figure.top` adds a margin.
    """
    import re

    tops: list[float] = []
    for tag, attrs in re.findall(r"<(\w+)\s([^>]*)>", body):
        if "transform=" in attrs:
            continue
        a = dict(re.findall(r'([\w-]+)="([^"]*)"', attrs))

        def num(k: str, a: dict[str, str] = a) -> float | None:
            try:
                return float(a[k])
            except (KeyError, ValueError):
                return None

        if tag == "text" and num("y") is not None:
            tops.append(float(a["y"]) - float(a.get("font-size", 8)))
        elif tag == "rect" and num("y") is not None:
            tops.append(float(a["y"]))
        elif tag == "line":
            tops += [v for v in (num("y1"), num("y2")) if v is not None]
        elif tag == "circle" and num("cy") is not None:
            tops.append(float(a["cy"]) - (num("r") or 0))
        elif tag == "path" and "d" in a:
            # Pairs after M/L/Q/C/T commands are (x, y); V takes a bare y.
            for cmd, args in re.findall(r"([MLQCTVHZ])([^MLQCTVHZ]*)", a["d"]):
                vals = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", args)]
                if cmd == "V":
                    tops += vals
                elif cmd != "H":
                    tops += vals[1::2]
    return min(tops) if tops else 0.0


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
    row_colour: dict[str, str] | None = None,
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

    Each row is drawn in its model's colour (`row_colour`, by row name; slate
    for a row not named): the reference end hollow, the focal end filled, as
    in every other chart.
    """
    n = len(rows)
    if not 4 <= n <= 8:
        raise ValueError(f"dumbbell takes 4-8 rows, got {n}")
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
        c = (row_colour or {}).get(name, MUTED)
        row_style = f'fill="{PAPER}" stroke="{edge(c)}" stroke-width="1.5"'
        # A pair too close to separate horizontally is split vertically instead,
        # one dot just above the row and one just below, so neither hides the
        # other; the positions along the axis stay exact.
        r = 5 if close else 6
        ya, yb = (y - 6, y + 6) if close else (y, y)
        out.append(
            f'<line x1="{xa}" y1="{ya}" x2="{xb}" y2="{yb}" stroke="{ink(0.55)}" stroke-width="1"/>'
        )
        shape = shape_of(name)
        out.append(
            _mark(shape, xa, ya, r, f'data-series="reference" data-value="{a:.4f}" {row_style}')
        )
        out.append(
            _mark(
                shape,
                xb,
                yb,
                r,
                f'data-series="focal" data-value="{b:.4f}" fill="{c}" stroke="{edge(c)}" stroke-width="1"',
            )
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
        f'<circle cx="104" cy="493" r="5" fill="{PAPER}" stroke="{MUTED}" stroke-width="1.5"/>',
        _t(116, 497, ref_name, size=9, family=SANS, fill=INK),
        f'<circle cx="{132 + text_width(ref_name, 9) + 24:g}" cy="493" r="5" fill="{MUTED}" stroke="{MUTED}" stroke-width="1"/>',
        _t(132 + text_width(ref_name, 9) + 36, 497, focal_name, size=9, family=SANS, fill=INK),
    ]
    out.append(_legend(1000, 462, [], ""))
    out.extend(keys)
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
        "Frederick's 3 trick questions (bat and ball) · correct",
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
        "Radar-blank plane 90% built, rival's is better · finishes it",
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
        "Offered $1 of $10 · rejects",
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


SHORT = {
    "typesafe/jev-1.13-20260917": "Jev 1.13",
    "typesafe/jev-1.14.0": "Jev 1.14",
    "openai/gpt-6-luna-decisions-20261006": "GPT-6 Luna Decisions",
    "microsoft/microsoft-decision-1-20261009": "Microsoft-Decision-1",
    "perplexity/pplx-decider-v1.1-27b-20261006": "Decider v1.1 27B",
    "inception/mercury-decide-20260930": "Mercury Decide",
    "liquid/d1-20260930": "d1",
    "upstage/solar-decide-20260928": "Solar Decide",
    "upstage/solar-decide-flash-20261008": "Solar Decide Flash",
    "nace-ai/drex-v1.5-20261009": "Drex 1.5",
    "nace-ai/drex-v2.0-20261009": "Drex 2.0",
    "cloudflare/clef-flash": "Clef Flash",
    "cloudflare/clef": "Clef",
    "anthropic/claude-sonnet-5": "Claude Sonnet 5",
    "anthropic/claude-sonnet-5.5": "Claude Sonnet 5.5",
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


def _count(n: int) -> str:
    words = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen"
    return words.split()[n] if n < 16 else str(n)


RERUN_NOTE = " Allais and Holt\u2013Laury items re-asked 17 Oct 2026."


def _runs_when(run_files: dict[str, str] | None, models: list[str]) -> str:
    """When the plotted models were run, from their run files' names.

    The main comparison's runs began on 12 Oct 2026 and finished on the 13th;
    a model run on another day is named with its date.
    """
    from datetime import date

    if not run_files:
        return "All models run 12\u201313 Oct 2026." + RERUN_NOTE
    started = {m: Path(run_files[m]).name[9:17] for m in models if m in run_files}
    later: dict[str, list[str]] = {}
    for m, d in started.items():
        if d != "20261012":
            later.setdefault(d, []).append(SHORT.get(m, m))
    if not later:
        return "All models run 12\u201313 Oct 2026." + RERUN_NOTE
    parts = []
    for d, names in sorted(later.items()):
        x = date(int(d[:4]), int(d[4:6]), int(d[6:8]))
        joined = ", ".join(names[:-1]) + " and " + names[-1] if len(names) > 1 else names[0]
        parts.append(f"{joined} on {x.day} {x:%b %Y}")
    return f"Models run 12\u201313 Oct 2026, except {'; '.join(parts)}.{RERUN_NOTE}"


def _backend(run_file: str) -> str:
    """The backend a run file records, read from its first record.

    `run_file` is a full path, or one relative to the default raw directory.
    """
    import json

    from .config import RAW_DIR

    with (RAW_DIR / run_file).open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                return str(json.loads(line).get("backend", ""))
    return ""


def _route(models: list[str], run_files: dict[str, str] | None) -> str:
    """Which models went to TypeSafe's API directly, as their run files record it."""
    if not run_files:
        return ""
    direct = [m for m in models if m in run_files and _backend(run_files[m]) == "typesafe"]
    if not direct:
        return ""
    names = " and ".join(SHORT.get(m, m) for m in direct)
    verb = "were" if len(direct) > 1 else "was"
    rest = ", the rest through OpenRouter" if len(direct) < len(models) else ""
    return f"{names} {verb} called through TypeSafe's API directly{rest}. "


def _main_when(run_files: dict[str, str] | None) -> str:
    models = [m for m, _c in MAIN_MODELS]
    return f"{_runs_when(run_files, models)} {_route(models, run_files)}".strip()


def fig_models_scatter(fdf: pd.DataFrame, run_files: dict[str, str] | None = None) -> Figure:
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

    # A model above the line (told to answer like a person, it moved away from
    # people) is the one result this chart exists to catch, so it gets a ring
    # and a legend line; with none above the line nothing is singled out.
    above = sorted((p for p in pts if p[2] > p[1]), key=lambda p: p[1] - p[2])
    focal_name = above[0][0] if above else ""
    focal_note = (
        ""
        if not above
        else f"{focal_name}: the only model above the line"
        if len(above) == 1
        else f"{focal_name}: furthest above the line"
    )
    # The README's main models keep their colour and shape here too.
    main = {SHORT[m]: (m, c) for m, c in MAIN_MODELS}
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
    marks = [(n, X(xn), Y(yt), 7.0 if n == focal_name else 6.0) for n, xn, yt, _ in pts]
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
    for name, xn, yt, typ in sorted(pts, key=lambda p: p[0] in main):
        cx, cy = X(xn), Y(yt)
        shape = "circle"
        if name in main:
            model, colour = main[name]
            shape, mark = MAIN_SHAPES[model], _model_style(model, colour)
        elif name == "Claude Haiku 5.5":
            # A chat model, so hollow like Sonnet; its orange tells it apart.
            mark = f'fill="{PAPER}" stroke="{ANTHROPIC_ORANGE}" stroke-width="2"'
        elif typ != "System One":
            mark = f'fill="{PAPER}" stroke="{MUTED}" stroke-width="1.5"'
        else:
            mark = f'fill="{OTHER_MODEL}" stroke="{OTHER_MODEL}" stroke-width="1"'
        if name == focal_name:
            out.append(
                f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="10" fill="none" stroke="{INK}" stroke-width="1.5"/>'
            )
        out.append(
            _mark(
                shape,
                cx,
                cy,
                5,
                f'data-name="{esc(name)}" data-x="{xn:.4f}" data-y="{yt:.4f}" ' + mark,
                title=f"{name} · {xn:.2f} with no instruction · {yt:.2f} as a typical person",
            )
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
    ky = ly0 + 31
    # Two key lines: the main models by name, then everything else.
    x: float = 104
    for model, colour in MAIN_MODELS:
        x = _model_key(out, x, ky, model, colour) - 4
    ky += 22
    out.append(
        f'<circle cx="104" cy="{ky}" r="5" fill="{OTHER_MODEL}" stroke="{OTHER_MODEL}" stroke-width="1"/>'
    )
    out.append(_t(116, ky + 4, "Other System One model", size=9, family=SANS, fill=INK))
    x = 116 + text_width("Other System One model", 9) + 30
    out.append(
        f'<circle cx="{x:g}" cy="{ky}" r="5" fill="{PAPER}" stroke="{MUTED}" stroke-width="1.5"/>'
    )
    out.append(_t(x + 12, ky + 4, "Chat model, resampled", size=9, family=SANS, fill=INK))
    x += 12 + text_width("Chat model, resampled", 9) + 30
    out.append(
        f'<circle cx="{x:g}" cy="{ky}" r="5" fill="{PAPER}" stroke="{ANTHROPIC_ORANGE}" stroke-width="2"/>'
    )
    out.append(_t(x + 12, ky + 4, "Claude Haiku 5.5", size=9, family=SANS, fill=INK))
    if focal_note:
        out.append(
            f'<circle cx="104" cy="{ky + 22}" r="8" fill="none" stroke="{INK}" stroke-width="1.5"/>'
        )
        out.append(_t(116, ky + 26, focal_note, size=9, family=SANS, fill=INK))
    return Figure(
        slug="models-scatter",
        eyebrow=f"{_count(len(pts)).capitalize()} models · no instruction vs. told to answer like a typical person",
        title="Distance from published human results, with and without the \u2018typical person\u2019 instruction",
        subtitle=(
            "Each point is one model. Distance is the mean absolute difference from the published human result "
            "over the 14 measures in the decision-making and economic-game charts, each on a 0\u20131 scale, so 0 "
            "would mean identical to people. Across: no instruction. Up: told to answer like a typical person. "
            "Points below the dashed line moved closer to people when told."
        ),
        desc=f"Scatter of {_count(len(pts))} models' mean distance from human values answering neutrally versus as a "
        f"typical person; {len([p for p in pts if p[2] < p[1]])} fall below the no-change line.",
        width=1000,
        height=ly0 + 72 + (22 if focal_note else 0),
        body="\n".join(out),
        source="Axes zoomed to the data: 0.15–0.55 across, 0.05–0.35 up, not from zero. "
        f"{_runs_when(run_files, sorted(set(fdf['model'].astype(str))))} "
        f"{_route(sorted(set(fdf['model'].astype(str))), run_files)}14 probability-scale measures (each "
        "0–1), 10 replicates or samples per cell. Distance alone is not a ranking: see the framing figure.",
    )


def _cell(df: pd.DataFrame, row: str, col: str) -> float:
    return float(str(df.at[row, col]))


def fig_framing(mdf: pd.DataFrame, run_files: dict[str, str] | None = None) -> Figure:
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
    # Eight rows fit: both Jev versions, and the six other System One models with
    # the largest swing under either prompt. The rest, and the chat models, go in the source line.
    system_one = [m for m in mdf.columns if m in SHORT and "anthropic" not in m]
    jev = [m for m in system_one if m.startswith("typesafe/")]
    others = sorted(
        (m for m in system_one if m not in jev),
        key=lambda m: -max(abs(contrast(m, "neutral")), abs(contrast(m, "typical_human"))),
    )
    keep = jev + others[: 8 - len(jev)]
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
        row_colour={SHORT[m]: model_colour(m) for m in keep},
        axis_title="gain-frame minus loss-frame rate of picking the sure option, in points",
        step=20,
        fmt="{:.0f}",
        order_note="ROWS BY THE AS-A-PERSON VALUE",
        reference_line=(human, f"PEOPLE {human:.0f}"),
    )
    return Figure(
        slug="framing-contrast",
        eyebrow=f"Framing effect · {_count(len(keep))} System One models",
        title="Size of the framing effect by model, in the disease problem",
        subtitle=(
            "The same choice between a sure and a risky programme against a disease, worded once as lives saved "
            "and once as lives lost. People pick the sure option 72% of the time in the gain wording and 22% in "
            "the loss wording, a 50-point swing. Each row is a model's swing in points; below zero, it picks the "
            "sure option more often in the loss wording, the reverse of people."
        ),
        desc=f"Dumbbell chart of {_count(len(keep))} System One models' framing reversal in points, answering neutrally and as a typical person, against the human value of 50.",
        width=1000,
        height=510,
        body=body,
        source="The chart holds eight rows, so the rest are given here, with no instruction and as a typical "
        "person: "
        + "; ".join(
            f"{SHORT[m]} {round(contrast(m, 'neutral'))} and {round(contrast(m, 'typical_human'))}"
            for m in mdf.columns
            if m in SHORT and m not in keep
        )
        + f". Human rates: Tversky & Kahneman (1981). {_runs_when(run_files, list(mdf.columns))}",
    )


# -- schematics ----------------------------------------------------------------


def _node(
    x: int, y: int, w: int, h: int, name: str, sub: str, *, kind: str = "backend", tag: str = ""
) -> str:
    # Teal marks the System One path in the method schematic and nothing else;
    # a fixed bug in the health schematic is a heavier ink outline.
    fill, stroke, width = {
        "backend": (WHITE, INK, 1),
        "focal": (accent(0.08), ACCENT, 1),
        "fixed": (WHITE, INK, 2.5),
        "external": (ink(0.03), ink(0.30), 1),
        "store": (ink(0.05), MUTED, 1),
    }[kind]
    if text_width(name, 12) > w - 16 or text_width(sub, 9, True) > w - 16:
        raise ValueError(f"label does not fit its node: {name!r} / {sub!r}")
    cx = x + w / 2
    parts = [
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{PAPER}"/>',
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" stroke="{stroke}" stroke-width="{width:g}"/>',
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
    a.append(_node(cols[1], mid - h // 2, w, h, "Five prompts", "listed above", tag="PROMPT"))
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
            "distributions averaged: $0.14 for the run",
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
            "answers counted: $8.84 for the same run",
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
        ("Room to reason", "up to 4,096 tokens", "CAP"),
        ("Reply read", "exact key in 91–99%", "PARSE"),
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
        "Unreadable (empty, cut off, no option named): Claude Sonnet 5.5, 3 of 6,800 replies; Claude Haiku 5.5, 16 of 6,800.",
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
            "Each item is asked under five prompts: no instruction, \u2018answer like a typical person\u2019 "
            "with and without \u2018not the textbook-correct answer\u2019, \u2018answer like a rational "
            "agent\u2019 and an antisocial persona. Each model is asked "
            "every item ten times under each prompt. A System One model returns a probability for every possible "
            "answer on each call, and the ten distributions are averaged. A chat model returns one answer per call as text, "
            "which is read for the option it names, and the ten answers are counted. Either way the result is one distribution per item and prompt, "
            "compared with the published human result for that test."
        ),
        desc="Process diagram: a battery item is framed five ways, asked ten times of either a System One model or a chat model, whose text replies are read for an option key with unreadable ones dropped and counted, reduced to one distribution per cell, and compared with a published human rate.",
        width=W,
        height=H,
        body="\n".join(a),
        source="Costs are for the same 7,350 questions on 12\u201313 Oct 2026 (147 items \u00d7 5 prompts \u00d7 "
        "10): Jev 1.13 $0.14, Claude Sonnet 5.5 $8.84.",
    )


def fig_health(run_files: dict[str, str] | None = None) -> Figure:
    W, H = 960, 440
    w, h = 280, 64
    cols = [24, 340, 656]
    rows = [
        (
            "GPT-6 Luna refused 4%",
            "300 calls → HTTP 502",
            "Refusals reported as a 502",
            "client tried each 5 times",
            "Counted as refusals",
            "never retried; in health.csv",
            "fixed",
        ),
        (
            "Both Solar models lost an item",
            "p-beauty contest, 50 calls",
            "Route caps Choice at 26",
            "the item has 101 options",
            "Disclosed, not imputed",
            "one item fewer, stated",
            "backend",
        ),
        (
            "Haiku 5.5 replied with nothing",
            "183 calls in an early run",
            "Reasoning used the cap",
            "all 512 tokens, no answer",
            "Cap raised and recorded",
            "4,096 → 16 unresolved",
            "fixed",
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
    for fill, stroke, width, label in [
        (WHITE, INK, 2.5, "A bug in this repository, fixed"),
        (WHITE, INK, 1, "Outcome"),
        (ink(0.03), ink(0.30), 1, "Cause outside the repository's control"),
    ]:
        a.append(
            f'<rect x="{x}" y="402" width="16" height="10" rx="2" fill="{fill}" stroke="{stroke}" stroke-width="{width:g}"/>'
        )
        a.append(_t(x + 24, 411, label, size=9, family=SANS, fill=INK))
        x += int(24 + text_width(label, 9) + 40)
    return Figure(
        slug="health-checks",
        eyebrow="Data quality · all models",
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
        source=f"results/comparison/health.csv. {_runs_when(run_files, sorted(run_files or {}))} The "
        "truncated Haiku run was discarded, not mixed in.",
    )


# -- build and export ----------------------------------------------------------------


# -- main charts, several models ------------------------------------------------

# The models the README's main charts carry, each in its own colour and shape:
# both Jev versions, newest first, then the three other System One models the
# comparison started with. Everything else is in the scatter and docs/MODELS.md.
JEV_113 = "typesafe/jev-1.13-20260917"
JEV_114_ID = "typesafe/jev-1.14.0"
MAIN_MODELS = [
    (JEV_114_ID, JEV_114),
    (JEV_113, JEV_PINK),
    ("openai/gpt-6-luna-decisions-20261006", "#2e5aa8"),
    ("cloudflare/clef", "#8e7c0b"),
    ("liquid/d1-20260930", "#7911d4"),
]
# Checked with the dataviz palette validator on paper: every pair clears the
# normal-vision floor; the closest pair for colour-blind readers (d1's violet
# and GPT-6's blue, 6.8 for deuteranopes) is in the band that is legal only
# with a second encoding, which the shapes are. None is teal or slate.
MAIN_SHAPES = {
    JEV_114_ID: "hexagon",
    JEV_113: "circle",
    "openai/gpt-6-luna-decisions-20261006": "square",
    "cloudflare/clef": "diamond",
    "liquid/d1-20260930": "triangle",
}
# Every other System One model shares one sienna: not slate (people), not teal,
# and none of the main five's colours; the validator finds no failing pair.
OTHER_MODEL = "#a0522d"


def shape_of(name: str) -> str:
    """A model's marker shape, by its display name; circle for any model outside the main five."""
    return next((MAIN_SHAPES[m] for m, _c in MAIN_MODELS if SHORT[m] == name), "circle")


def model_colour(model: str) -> str:
    """A model's colour in every chart: its own if it is one of the main five."""
    return dict(MAIN_MODELS).get(model, OTHER_MODEL)


def edge(colour: str) -> str:
    """The stroke for a mark of this colour: Jev 1.13's pink is too light to be its own."""
    return JEV_PINK_EDGE if colour == JEV_PINK else colour


def _mark(shape: str, x: float, y: float, r: float, attrs: str, title: str = "") -> str:
    """One marker of the given shape centred on (x, y), at roughly equal visual weight.

    `attrs` goes first so data attributes keep their order; `title` becomes a
    hover label in the HTML version.
    """
    if shape == "circle":
        tag, geo = "circle", f'cx="{x:.1f}" cy="{y:.1f}" r="{r:g}"'
    elif shape == "square":
        side = r * 1.75
        tag, geo = (
            "rect",
            (
                f'x="{x - side / 2:.1f}" y="{y - side / 2:.1f}" width="{side:.1f}" height="{side:.1f}"'
            ),
        )
    elif shape == "diamond":
        d = r * 1.35
        tag, geo = (
            "path",
            (
                f'd="M{x:.1f} {y - d:.1f} L{x + d:.1f} {y:.1f} L{x:.1f} {y + d:.1f} L{x - d:.1f} {y:.1f} Z"'
            ),
        )
    elif shape == "triangle":
        t = r * 1.4
        tag, geo = (
            "path",
            (
                f'd="M{x:.1f} {y - t:.1f} L{x + t * 0.9:.1f} {y + t * 0.6:.1f} '
                f'L{x - t * 0.9:.1f} {y + t * 0.6:.1f} Z"'
            ),
        )
    elif shape == "hexagon":
        h = r * 1.2
        pts = " ".join(
            f"{x + h * math.cos(math.radians(a)):.1f},{y + h * math.sin(math.radians(a)):.1f}"
            for a in range(30, 390, 60)
        )
        tag, geo = "polygon", f'points="{pts}"'
    else:
        raise ValueError(f"unknown marker shape {shape!r}")
    if title:
        return f"<{tag} {attrs} {geo}><title>{esc(title)}</title></{tag}>"
    return f"<{tag} {attrs} {geo}/>"


def _model_style(model: str, colour: str) -> str:
    return f'fill="{colour}" stroke="{edge(colour)}" stroke-width="1"'


def _mstat(cdf: pd.DataFrame, inst: str, stat: str, persona: str, model: str) -> float:
    sel = cdf[
        (cdf.instrument == inst)
        & (cdf.statistic == stat)
        & (cdf.persona == persona)
        & (cdf.model == model)
    ]
    if not len(sel):
        raise KeyError(f"{inst}/{stat}/{persona}/{model} not in the comparison statistics")
    return float(sel["value"].iloc[0])


def _model_key(out: list[str], x: float, y: float, model: str, colour: str) -> float:
    label = SHORT[model]
    out.append(_mark(MAIN_SHAPES[model], x, y, 4.5, _model_style(model, colour)))
    out.append(_t(x + 10, y + 4, label, size=9, family=SANS, fill=INK))
    return x + 10 + text_width(label, 9) + 32


def _model_dots(
    rows: list[tuple[str, str, float, dict[str, dict[str, float]]]],
    panels: list[tuple[str, str]],
    axis_title: str,
) -> str:
    """Rows of tests, one panel per prompt; in each, a tick for people and a dot per model.

    Each model keeps its own line within the row, in a fixed order, so dots
    never cover one another however close the values; a hairline from the
    people tick to each dot is that model's gap from people.
    """
    n = len(rows)
    pitch, y0 = 52, 96
    spans = [(312, 612), (648, 948)][: len(panels)]
    panel_names = {key: header.lower() for key, header in panels}
    # One line per model inside the row, top to bottom in legend order.
    k = len(MAIN_MODELS)
    offsets = [(i - (k - 1) / 2) * 6 for i in range(k)]
    last = y0 + (n - 1) * pitch
    out: list[str] = []
    for (key, header), (a, b) in zip(panels, spans, strict=True):
        out.append(_t((a + b) / 2, 52, header, size=7, spacing="0.14em", anchor="middle", fill=INK))
        for i in range(5):
            t = i * 0.25
            x = a + t * (b - a)
            out.append(
                f'<line x1="{x:g}" y1="66" x2="{x:g}" y2="{last + 22}" stroke="{ink(0.25 if i == 0 else 0.08)}" stroke-width="{1 if i == 0 else 0.8}"/>'
            )
            out.append(
                _t(
                    x,
                    last + 38,
                    f"{t:.2f}",
                    anchor="middle",
                    extra=f' data-tick="x" data-value="{t:g}"',
                )
            )
        for k, (_name, _sub, human, vals) in enumerate(rows):
            y = y0 + k * pitch
            xh = a + human * (b - a)
            for (model, _colour), dy in zip(MAIN_MODELS, offsets, strict=True):
                v = vals[key][model]
                xv = a + v * (b - a)
                out.append(
                    f'<line x1="{xh:.1f}" y1="{y + dy}" x2="{xv:.1f}" y2="{y + dy}" stroke="{ink(0.25)}" stroke-width="0.8"/>'
                )
            out.append(
                f'<line data-series="people" data-value="{human:.4f}" x1="{xh:.1f}" y1="{y - 16}" x2="{xh:.1f}" y2="{y + 16}" stroke="{MUTED}" stroke-width="2"/>'
            )
            for (model, colour), dy in zip(MAIN_MODELS, offsets, strict=True):
                v = vals[key][model]
                out.append(
                    _mark(
                        MAIN_SHAPES[model],
                        a + v * (b - a),
                        y + dy,
                        3.5,
                        f'data-series="{esc(SHORT[model])}" data-panel="{key}" data-value="{v:.4f}" '
                        + _model_style(model, colour),
                        title=f"{SHORT[model]} · {panel_names[key]} · {v:.2f} (people {human:.2f})",
                    )
                )
    for k, (name, sub, _h, _v) in enumerate(rows):
        y = y0 + k * pitch
        out.append(_t(288, y - 1, name, size=11, fill=INK, family=SANS, anchor="end", weight=600))
        out.append(_t(288, y + 12, sub, size=9, fill=MUTED, family=SANS, anchor="end"))
    out.append(
        _t(
            (spans[0][0] + spans[-1][1]) / 2,
            last + 54,
            axis_title,
            size=7,
            anchor="middle",
            spacing="0.14em",
        )
    )
    ly = last + 66
    out.append(_legend(1000, ly, []))
    out.append(
        f'<line x1="104" y1="{ly + 24}" x2="104" y2="{ly + 38}" stroke="{MUTED}" stroke-width="2"/>'
    )
    out.append(_t(116, ly + 35, "Published human result", size=9, family=SANS, fill=INK))
    x = 116 + text_width("Published human result", 9) + 40
    for model, colour in MAIN_MODELS:
        x = _model_key(out, x, ly + 31, model, colour)
    out.append(_t(970, ly + 35, "MARKS TOP TO BOTTOM IN LEGEND ORDER", anchor="end"))
    return "\n".join(out)


# How the main charts name their models: both Jev versions, then the rest.
MAIN_WHO = "Jev 1.14, Jev 1.13 and three other System One models"


def _models_source(cdf: pd.DataFrame, run_files: dict[str, str] | None = None) -> str:
    """The main charts' source line; the rest of the comparison is counted, not assumed."""
    more = cdf["model"].nunique() - len(MAIN_MODELS)
    return (
        f"Each model: mean of the probability distributions returned over 10 repeats. {_main_when(run_files)} "
        "Human results: published studies or meta-analyses, listed in docs/BENCHMARKS.md. "
        f"{_count(more).capitalize()} more models are in the scatter and docs/MODELS.md."
    )


def fig_models_tests(
    cdf: pd.DataFrame, which: str, run_files: dict[str, str] | None = None
) -> Figure:
    measures = DECISION_MEASURES if which == "decisions" else GAME_MEASURES
    panels = [
        ("neutral", "NO INSTRUCTION"),
        ("typical_human", "TOLD TO ANSWER LIKE A TYPICAL PERSON"),
    ]
    rows = [
        (
            name,
            sub,
            BENCHMARKS[b].value,
            {p: {m: _mstat(cdf, i, s, p, m) for m, _c in MAIN_MODELS} for p, _h in panels},
        )
        for i, s, b, name, sub in measures
    ]
    names = ", ".join(SHORT[m] for m, _c in MAIN_MODELS[:-1]) + f" and {SHORT[MAIN_MODELS[-1][0]]}"
    if which == "decisions":
        title = f"{MAIN_WHO} vs. people on seven decision-making tests"
        what = (
            "Classic problems from behavioural economics. Each row says what was asked and which answer is "
            "counted; some rows count the correct answer, others the typical human error."
        )
    else:
        title = f"{MAIN_WHO} vs. people in five economic games"
        what = (
            "One-shot, anonymous games for a hypothetical $10. Each row says what the player could do and what "
            "the number measures."
        )
    if which == "games":
        grid = [
            (
                name,
                sub,
                BENCHMARKS[b].value,
                {
                    m: (_mstat(cdf, i, s, "neutral", m), _mstat(cdf, i, s, "typical_human", m))
                    for m, _c in MAIN_MODELS
                },
            )
            for i, s, b, name, sub in measures
        ]
        return Figure(
            slug="models-games",
            eyebrow=f"Economic games · {_count(len(MAIN_MODELS))} models",
            title="Five economic games, before and after being told to answer like a person",
            subtitle=(
                f"{what} Each line runs from a model's choice with no instruction (hollow) to its choice "
                f"(filled) with this instruction added first: \u201c{_prompt('typical_human')}\u201d The tick "
                "is people."
            ),
            desc="Small multiples, one column per System One model and one row per economic-game measure, each a "
            "line from the model's value with no instruction to its value when told to answer like a typical "
            "person, over the published human result.",
            width=1000,
            height=y_end(len(grid)),
            body=_model_shift_grid(
                grid,
                "SHARE OF ANSWERS, OR SHARE OF THE MONEY",
                ("typical_human", "told to answer like a typical person"),
            ),
            source=_models_source(cdf, run_files),
        )
    return Figure(
        slug=f"models-{which}",
        eyebrow=f"{'Decision-making tests' if which == 'decisions' else 'Economic games'} · "
        f"{_count(len(MAIN_MODELS))} models",
        title=title,
        subtitle=(
            f"{what} Left, asked with no instruction; right, with this instruction added first: "
            f"\u201c{_prompt('typical_human')}\u201d The tick is people; each mark is a model's probability on "
            "that answer, or its expected share."
        ),
        desc=f"Dot chart of {len(rows)} {which} measures in two panels, no instruction and told to answer like a "
        f"typical person, comparing {names} with the published human result.",
        width=1000,
        height=y_end(len(rows)),
        body=_model_dots(rows, panels, "SHARE OF ANSWERS, OR SHARE OF THE MONEY"),
        source=_models_source(cdf, run_files),
    )


def y_end(n: int) -> int:
    """Height of a `_model_dots` chart with n rows: rows, axis, legend."""
    return 96 + (n - 1) * 52 + 66 + 48


def _model_shift_grid(
    rows: list[tuple[str, str, float, dict[str, tuple[float, float]]]],
    axis_title: str,
    to: tuple[str, str] = ("antisocial", "antisocial persona"),
    models: list[tuple[str, str]] | None = None,
    start: tuple[str, str] = ("neutral", "No instruction"),
) -> str:
    """Small multiples: one column per model, one row per test.

    Each cell is that model's own move, a line from its value with no
    instruction (hollow) to its value under the prompt (filled), over a tick
    for people. Read down a column for one model, across a row for one test;
    no line ever has to be matched between panels.
    """
    models = models or MAIN_MODELS
    n = len(rows)
    pitch, y0 = 52, 96
    # The columns share the plot width: 128 wide with 46 between for up to
    # four models, narrower for five.
    x_start = 320
    w, gap = {1: (280, 60), 2: (280, 60), 3: (180, 50), 4: (128, 46)}.get(len(models), (104, 26))
    last = y0 + (n - 1) * pitch
    out: list[str] = []
    for c, (model, colour) in enumerate(models):
        a = x_start + c * (w + gap)
        shape = MAIN_SHAPES[model]
        name = SHORT[model]
        out.append(_mark(shape, a + 5, 48, 4.5, _model_style(model, colour)))
        # A name wider than its column goes on two lines.
        if text_width(name, 10) + 14 > w + gap - 8 and " " in name:
            head, tail = name.rsplit(" ", 1)
            out.append(_t(a + 14, 52, head, size=10, family=SANS, fill=INK, weight=600))
            out.append(_t(a + 14, 64, tail, size=10, family=SANS, fill=INK, weight=600))
        else:
            out.append(_t(a + 14, 52, name, size=10, family=SANS, fill=INK, weight=600))
        for t in (0.0, 0.5, 1.0):
            x = a + t * w
            out.append(
                f'<line x1="{x:g}" y1="72" x2="{x:g}" y2="{last + 22}" stroke="{ink(0.25 if t == 0 else 0.08)}" stroke-width="{1 if t == 0 else 0.8}"/>'
            )
            out.append(
                _t(
                    x,
                    last + 38,
                    f"{t:.1f}",
                    anchor="middle",
                    extra=f' data-tick="x" data-value="{t:g}"',
                )
            )
        for k, (_name, _sub, human, vals) in enumerate(rows):
            y = y0 + k * pitch
            before, after = vals[model]
            xh, xb, xa = a + human * w, a + before * w, a + after * w
            out.append(
                f'<line data-series="people" data-value="{human:.4f}" x1="{xh:.1f}" y1="{y - 13}" x2="{xh:.1f}" y2="{y + 13}" stroke="{MUTED}" stroke-width="2"/>'
            )
            # The line stops short of the filled mark so it never shows through it.
            if abs(xa - xb) > 9:
                step = 7 if xa > xb else -7
                out.append(
                    f'<line x1="{xb:.1f}" y1="{y}" x2="{xa - step:.1f}" y2="{y}" stroke="{edge(colour)}" stroke-width="1.5"/>'
                )
            out.append(
                _mark(
                    shape,
                    xb,
                    y,
                    4,
                    f'data-series="{esc(name)}" data-panel="{start[0]}" data-value="{before:.4f}" '
                    f'fill="{PAPER}" stroke="{edge(colour)}" stroke-width="1.5"',
                    title=f"{name} · {start[1].lower()} · {before:.2f} (people {human:.2f})",
                )
            )
            out.append(
                _mark(
                    shape,
                    xa,
                    y,
                    4.5,
                    f'data-series="{esc(name)}" data-panel="{to[0]}" data-value="{after:.4f}" '
                    + _model_style(model, colour),
                    title=f"{name} · {to[1]} · {after:.2f} (people {human:.2f})",
                )
            )
    for k, (name, sub, _h, _v) in enumerate(rows):
        y = y0 + k * pitch
        out.append(_t(296, y - 1, name, size=11, fill=INK, family=SANS, anchor="end", weight=600))
        out.append(_t(296, y + 12, sub, size=9, fill=MUTED, family=SANS, anchor="end"))
    right = x_start + (len(models) - 1) * (w + gap) + w
    out.append(
        _t((x_start + right) / 2, last + 54, axis_title, size=7, anchor="middle", spacing="0.14em")
    )
    ly = last + 66
    out.append(_legend(1000, ly, []))
    out.append(
        f'<line x1="104" y1="{ly + 24}" x2="104" y2="{ly + 38}" stroke="{MUTED}" stroke-width="2"/>'
    )
    x = 116
    out.append(_t(x, ly + 35, "Published human result", size=9, family=SANS, fill=INK))
    x += text_width("Published human result", 9) + 40
    out.append(
        f'<circle cx="{x}" cy="{ly + 31}" r="4" fill="{PAPER}" stroke="{MUTED}" stroke-width="1.5"/>'
    )
    out.append(_t(x + 10, ly + 35, start[1], size=9, family=SANS, fill=INK))
    x += 10 + text_width(start[1], 9) + 40
    out.append(
        f'<circle cx="{x}" cy="{ly + 31}" r="4.5" fill="{MUTED}" stroke="{MUTED}" stroke-width="1"/>'
    )
    out.append(
        _t(
            x + 10,
            ly + 35,
            f"{to[1][0].upper()}{to[1][1:]}, where the line ends",
            size=9,
            family=SANS,
            fill=INK,
        )
    )
    out.append(_t(970, ly + 35, "ONE COLUMN PER MODEL", anchor="end"))
    return "\n".join(out)


def fig_models_antisocial(cdf: pd.DataFrame, run_files: dict[str, str] | None = None) -> Figure:
    rows = [
        (
            name,
            sub,
            BENCHMARKS[b].value,
            {
                m: (_mstat(cdf, i, s, "neutral", m), _mstat(cdf, i, s, "antisocial", m))
                for m, _c in MAIN_MODELS
            },
        )
        for i, s, b, name, sub in GAME_MEASURES
    ]
    dd = "; ".join(
        f"{SHORT[m]} {_mstat(cdf, 'dirty_dozen', 'overall', 'neutral', m):.1f} to "
        f"{_mstat(cdf, 'dirty_dozen', 'overall', 'antisocial', m):.1f}"
        for m, _c in MAIN_MODELS
    )
    return Figure(
        slug="models-antisocial",
        eyebrow=f"Economic games · antisocial persona · {_count(len(MAIN_MODELS))} models",
        title="What an antisocial persona does to choices in five economic games",
        subtitle=(
            f"Each line runs from a model's choice with no instruction (hollow) to its choice (filled) with this instruction "
            f"added first: \u201c{_prompt('antisocial')}\u201d As a check that the persona took hold, the Dark "
            f"Triad score out of 9 rose: {dd}."
        ),
        desc="Small multiples, one column per System One model and one row per economic-game measure, each an "
        "line from the model's value with no instruction to its value with an antisocial persona, over the "
        "published human result.",
        width=1000,
        height=y_end(len(rows)),
        body=_model_shift_grid(rows, "SHARE OF ANSWERS, OR SHARE OF THE MONEY"),
        source=f"Mean of returned distributions over 10 repeats. {_main_when(run_files)} The tick is "
        "people with no persona, for scale. A persona is a prompt: it shows what a model can be made to output, "
        "not a trait it has.",
    )


def fig_jev_steer(cdf: pd.DataFrame, run_files: dict[str, str] | None = None) -> Figure:
    """Both Jev versions under the typical-person prompt, without and with its steer."""
    jevs = [(m, c) for m, c in MAIN_MODELS if m.startswith("typesafe/")]
    rows = [
        (
            name,
            sub,
            BENCHMARKS[b].value,
            {
                m: (
                    _mstat(cdf, i, s, "typical_human_plain", m),
                    _mstat(cdf, i, s, "typical_human", m),
                )
                for m, _c in jevs
            },
        )
        for i, s, b, name, sub in DECISION_MEASURES
    ]
    return Figure(
        slug="jev-steer",
        eyebrow="Decision-making tests · Jev 1.14 and 1.13 · the steer",
        title="How much of the move toward people comes from \u2018not the textbook-correct answer\u2019",
        subtitle=(
            "The typical-person instruction asks for a typical answer and also says \u201cnot the "
            "textbook-correct answer\u201d. Hollow: Jev's answer to the plain version, which drops that clause: "
            f"\u201c{_prompt('typical_human_plain')}\u201d Filled: its answer with the clause. A long line means "
            "the clause, not the model's picture of people, did the work."
        ),
        desc="Small multiples, one column per Jev version and one row per decision-making test, each a line "
        "from the value under the plain typical-person instruction to the value with the clause steering away "
        "from the textbook-correct answer, over the published human result.",
        width=1000,
        height=y_end(len(rows)),
        body=_model_shift_grid(
            rows,
            "SHARE OF ANSWERS THAT ARE THE ONE NAMED UNDER EACH TEST",
            ("typical_human", "with \u2018not the textbook-correct answer\u2019"),
            models=jevs,
            start=("typical_human_plain", "Plain typical-person instruction"),
        ),
        source="Each version: mean of the probability distributions returned over 10 repeats. "
        f"{_runs_when(run_files, [m for m, _c in jevs])} {_route([m for m, _c in jevs], run_files)}"
        "Human results: published studies or meta-analyses, listed in docs/BENCHMARKS.md.",
    )


def fig_models_dictator(
    runs: dict[str, pd.DataFrame], run_files: dict[str, str] | None = None
) -> Figure:
    """People's distribution of giving behind each model's, one small panel per model."""
    from .analysis import distributions
    from .benchmarks import DICTATOR_HUMAN_DISTRIBUTION, DICTATOR_HUMAN_SOURCE

    amounts = [f"${v}" for v in range(11)]
    people = [DICTATOR_HUMAN_DISTRIBUTION[a] for a in amounts]
    dists = {
        m: [
            distributions(runs[m]).get(("dictator_allocation", "neutral", "jev"), {}).get(a, 0.0)
            for a in amounts
        ]
        for m, _c in MAIN_MODELS
    }
    top = max(max(people), *(max(v) for v in dists.values()))
    # The scale ends just above the tallest bar, so no panel carries an empty
    # band above its top gridline; gridlines stay on round 20s.
    ceil = max(0.4, top + 0.04)
    # Three panels to a row; two rows hold the five models.
    cells = [(70 + 310 * (k % 3), 60 + 220 * (k // 3)) for k in range(len(MAIN_MODELS))]
    w, h = 260, 150
    out: list[str] = []
    for (model, colour), (x0, y0) in zip(MAIN_MODELS, cells, strict=True):
        base = y0 + h

        def y(v: float, base: float = base) -> float:
            return base - v / ceil * h

        out.append(_mark(MAIN_SHAPES[model], x0 + 5, y0 - 18, 4.5, _model_style(model, colour)))
        out.append(_t(x0 + 16, y0 - 14, SHORT[model], size=12, family=SANS, fill=INK, weight=600))
        for t in [i * 0.2 for i in range(int(ceil / 0.2 + 1e-9) + 1)]:
            if t:
                out.append(
                    f'<line x1="{x0}" y1="{y(t):.1f}" x2="{x0 + w}" y2="{y(t):.1f}" stroke="{ink(0.08)}" stroke-width="0.8"/>'
                )
            out.append(
                _t(
                    x0 - 6,
                    y(t) + 3,
                    f"{t:.0%}",
                    anchor="end",
                    extra=f' data-tick="y" data-value="{t:g}"',
                )
            )
        out.append(
            f'<line x1="{x0}" y1="{base}" x2="{x0 + w}" y2="{base}" stroke="{ink(0.25)}" stroke-width="1"/>'
        )
        pitch = w / len(amounts)
        bar = 9
        edge = JEV_PINK_EDGE if colour == JEV_PINK else colour
        for i, a in enumerate(amounts):
            cx = x0 + pitch * (i + 0.5)
            for series, v, bx, style in (
                ("people", people[i], cx - bar - 1, f'fill="{muted(0.18)}" stroke="{MUTED}"'),
                (
                    SHORT[model],
                    dists[model][i],
                    cx + 1,
                    f'fill="{colour}" fill-opacity="0.75" stroke="{edge}"',
                ),
            ):
                by = y(v)
                who = "people" if series == "people" else SHORT[model]
                out.append(
                    f'<rect data-series="{esc(series)}" data-value="{v:.4f}" x="{bx:.1f}" y="{by:.1f}" '
                    f'width="{bar}" height="{base - by:.1f}" {style} stroke-width="1">'
                    f"<title>{esc(who)} · gives {a} · {v:.0%}</title></rect>"
                )
            out.append(_t(cx, base + 14, a, size=8, anchor="middle"))
    out.append(
        _t(
            520,
            466,
            "AMOUNT GIVEN TO THE STRANGER, OUT OF $10",
            size=7,
            spacing="0.14em",
            anchor="middle",
        )
    )
    out.append(_legend(1000, 476, []))
    out.append(
        f'<rect x="104" y="500" width="16" height="10" rx="2" fill="{muted(0.18)}" stroke="{MUTED}" stroke-width="1"/>'
    )
    label = "People: share of 20,813 dictators in 328 treatments"
    out.append(_t(128, 509, label, size=9, family=SANS, fill=INK))
    sx = 128 + text_width(label, 9) + 40
    for _m, colour in MAIN_MODELS:
        edge = JEV_PINK_EDGE if colour == JEV_PINK else colour
        out.append(
            f'<rect x="{sx:g}" y="500" width="10" height="10" rx="2" fill="{colour}" fill-opacity="0.75" stroke="{edge}" stroke-width="1"/>'
        )
        sx += 13
    out.append(
        _t(
            sx + 8,
            509,
            "The model's returned probability, no instruction",
            size=9,
            family=SANS,
            fill=INK,
        )
    )
    return Figure(
        slug="models-dictator",
        eyebrow=f"Dictator game · no instruction · {_count(len(MAIN_MODELS))} models",
        title="What one call returns in the dictator game, against what people give",
        subtitle=(
            "You are given $10 and decide how much to give an anonymous stranger, who cannot respond. Grey: the "
            "share of people giving each amount. Coloured: the probability each model returns for that amount, "
            "averaged over 10 calls. People have three peaks, at nothing, half and everything."
        ),
        desc=f"{_count(len(MAIN_MODELS)).capitalize()} small bar charts, one per System One model, each showing the model's probability of giving "
        "each amount from $0 to $10 next to the share of people who give it.",
        width=1000,
        height=520,
        body="\n".join(out),
        source=f"Same scale in every panel. Models: mean of 10 returned distributions. {_main_when(run_files)} "
        f"People: {DICTATOR_HUMAN_SOURCE}.",
    )


H4_SLUG = "followup-h4"

# Follow-up H4 rows: (instrument, statistic) -> what the statistic counts.
H4_LABELS = {
    ("allais", "prob_certain_pair1"): "Allais: the certain $3,000",
    ("allais", "prob_safer_pair2"): "Allais: the 25% chance of $3,000",
    ("base_rate", "prob_correct_band"): "Base rate: answer in the 0–10% band",
    ("categorization", "prob_rule_based"): "Categorisation: the rule-based group",
    ("choosing_rejecting", "prob_award_extreme"): "Custody: award the extreme parent",
    ("choosing_rejecting", "prob_deny_extreme"): "Custody: deny the extreme parent",
    ("conjunction", "prob_fallacy_forced_choice"): "Linda: the conjunction",
    ("crt", "proportion_correct"): "CRT: correct, Frederick's three items",
    ("false_consensus", "nonwearer_predicts_wear"): "False consensus: refusers' guess",
    ("false_consensus", "wearer_predicts_wear"): "False consensus: wearers' guess",
    ("framing", "prob_certain_gain_frame"): "Framing: certain programme, gains",
    ("framing", "prob_certain_loss_frame"): "Framing: certain programme, losses",
    ("incidental_anchors", "estimate_p17"): "Incidental anchor: low (17)",
    ("incidental_anchors", "estimate_p97"): "Incidental anchor: high (97)",
    ("knobe", "prob_harm_intentional"): "Knobe: harming was intentional",
    ("knobe", "prob_help_intentional"): "Knobe: helping was intentional",
    ("moral_typecasting", "responsibility_baby"): "Moral typecasting: baby harmed",
    ("moral_typecasting", "responsibility_man"): "Moral typecasting: man harmed",
    ("position_power", "power_long_line"): "Power: the long line",
    ("position_power", "power_short_line"): "Power: the short line",
    ("sunk_cost", "prob_continue"): "Sunk cost: finish the plane",
    ("trolley", "prob_push_permissible"): "Trolley: pushing is permissible",
    ("trolley", "prob_switch_permissible"): "Trolley: switching is permissible",
}


def fig_h4(panels: list[tuple[str, pd.DataFrame]], run_name: str = "the run shown") -> Figure:
    """Follow-up H4, one panel per Jev version: each statistic's error simulated and estimated.

    `panels` is (model, H4 table) per version, drawn left to right. Rows keep
    one order across panels (by how much estimating helps, averaged over the
    versions), so a statistic reads straight across. Hollow is simulate, filled
    is estimate, both in the version's colour. Errors are divided by each
    scale's range so proportions, 1-7 ratings and percentage bands can share
    one axis; the registered test uses the raw errors, and both p values are
    quoted.
    """
    from .analysis import h4_summary

    def _p(v: float | None) -> str:
        # No test: every pair tied, or too few pairs to rank.
        if v is None:
            return "n/a"
        return "< 0.001" if v < 0.0005 else f"{v:.3f}"

    def key(r: pd.Series) -> tuple[str, str]:
        return (str(r["instrument"]), str(r["statistic"]))

    tables = [
        (model, t.assign(gain=t["scaled_error_simulate"] - t["scaled_error_estimate"]))
        for model, t in panels
    ]
    gains: dict[tuple[str, str], list[float]] = {}
    for _m, t in tables:
        for _, r in t.iterrows():
            gains.setdefault(key(r), []).append(float(r["gain"]))
    order = sorted(gains, key=lambda k: -sum(gains[k]) / len(gains[k]))
    vals = [
        v for _m, t in tables for v in (*t["scaled_error_simulate"], *t["scaled_error_estimate"])
    ]
    floor, ceil = _domain(vals, 0.1)
    L, pitch, y0 = 300, 22, 92
    n = len(tables)
    gap = 40
    w = (960 - L - 20 - gap * (n - 1)) / n
    last = y0 + (len(order) - 1) * pitch
    out: list[str] = []
    heads = []
    for c, (model, t) in enumerate(tables):
        a = L + 20 + c * (w + gap)
        colour = model_colour(model)
        stroke = edge(colour)
        name = SHORT.get(model, model)
        summary = h4_summary(t)
        closer, tied = int((t["gain"] > 0).sum()), int((t["gain"] == 0).sum())
        heads.append((name, closer, len(t), summary))

        def px(v: float, a: float = a) -> float:
            return a + (v - floor) / (ceil - floor) * w

        out.append(
            _mark(MAIN_SHAPES.get(model, "circle"), a + 5, 36, 4.5, _model_style(model, colour))
        )
        out.append(_t(a + 16, 40, name, size=11, family=SANS, fill=INK, weight=600))
        tie = f" · TIED {tied}" if tied else ""
        out.append(
            _t(
                a,
                56,
                f"ESTIMATE CLOSER ON {closer} OF {len(t)}{tie}",
                size=7,
                spacing="0.12em",
                fill=INK,
            )
        )
        out.append(
            _t(
                a,
                68,
                f"P = {_p(summary.get('wilcoxon_p_one_sided'))} RAW · {_p(summary.get('wilcoxon_p_scaled'))} SCALED",
                size=7,
                spacing="0.12em",
            )
        )
        ticks = [floor + i * 0.1 for i in range(round((ceil - floor) / 0.1) + 1)]
        for v in ticks:
            x = px(v)
            out.append(
                f'<line x1="{x:.1f}" y1="{y0 - 12}" x2="{x:.1f}" y2="{last + 12}" '
                f'stroke="{ink(0.25 if v == floor else 0.08)}" stroke-width="{1 if v == floor else 0.8}"/>'
            )
            if round(v * 10) % 2 == 0:
                out.append(
                    _t(
                        x,
                        last + 28,
                        f"{v:.1f}",
                        anchor="middle",
                        extra=f' data-tick="x" data-value="{v:g}"',
                    )
                )
        rows = {key(r): r for _, r in t.iterrows()}
        for i, k in enumerate(order):
            if k not in rows:
                continue
            r = rows[k]
            y = y0 + i * pitch
            se, ee = float(r["scaled_error_simulate"]), float(r["scaled_error_estimate"])
            xs, xe = px(se), px(ee)
            # A pair too close to tell apart is split vertically, so neither
            # mark hides the other; x stays exact.
            ys, ye = (y - 4, y + 4) if abs(xs - xe) < 9 else (y, y)
            out.append(
                f'<line x1="{xs:.1f}" y1="{ys}" x2="{xe:.1f}" y2="{ye}" stroke="{stroke}" stroke-width="1.5"/>'
            )
            label = H4_LABELS.get(k, f"{k[0]}: {k[1]}")
            shape = MAIN_SHAPES.get(model, "circle")
            out.append(
                _mark(
                    shape,
                    xs,
                    ys,
                    4,
                    f'data-series="simulate" data-panel="{esc(name)}" data-value="{se:.4f}" '
                    f'fill="{PAPER}" stroke="{stroke}" stroke-width="1.5"',
                    title=f"{name} · {label} · simulate {se:.2f}",
                )
            )
            out.append(
                _mark(
                    shape,
                    xe,
                    ye,
                    4,
                    f'data-series="estimate" data-panel="{esc(name)}" data-value="{ee:.4f}" '
                    + _model_style(model, colour),
                    title=f"{name} · {label} · estimate {ee:.2f}",
                )
            )
    for i, k in enumerate(order):
        label = H4_LABELS.get(k, f"{k[0]}: {k[1]}")
        if text_width(label, 10) > L - 24:
            raise ValueError(f"row label does not fit the label column: {label!r}")
        out.append(
            _t(L - 12, y0 + i * pitch + 4, label, size=10, fill=INK, family=SANS, anchor="end")
        )
    out.append(
        _t(
            (L + 960) / 2,
            last + 44,
            "DISTANCE FROM THE PUBLISHED VALUE, AS A SHARE OF THE SCALE (LEFT IS CLOSER)",
            size=7,
            anchor="middle",
            spacing="0.14em",
        )
    )
    rule = int(last + 56)
    out.append(_legend(1000, rule, []))
    ky = rule + 31
    k1, k2 = "Simulate: answers as a typical person", "Estimate: predicts the population's answer"
    out.append(
        f'<circle cx="104" cy="{ky - 4}" r="5" fill="{PAPER}" stroke="{MUTED}" stroke-width="1.5"/>'
    )
    out.append(_t(116, ky, k1, size=9, family=SANS, fill=INK))
    x2 = 116 + text_width(k1, 9) + 32
    out.append(
        f'<circle cx="{x2:g}" cy="{ky - 4}" r="5" fill="{MUTED}" stroke="{MUTED}" stroke-width="1"/>'
    )
    out.append(_t(x2 + 12, ky, k2, size=9, family=SANS, fill=INK))
    out.append(_t(970, ky, "ROWS BY HOW MUCH ESTIMATING HELPS", anchor="end"))
    names = [h[0] for h in heads]
    who = " and ".join(names)
    counts = "; ".join(f"{nm}: {c} of {m}" for nm, c, m, _s in heads)
    preregistered = next((h for h in heads if h[0] == "Jev 1.13"), heads[0])
    return Figure(
        slug=H4_SLUG,
        eyebrow=f"Follow-up study · H4 · {who}",
        title="Predicting how people answer beats playing one, a little, "
        + ("in both versions" if n > 1 else f"for {names[0]}"),
        subtitle=(
            "Each statistic was measured two ways: the item asked under the typical-person prompt "
            "(simulate, hollow), and a question with no persona asking for the population's answer "
            "itself: the share who chose an option, or the average rating, percentage or prediction "
            f"(estimate, filled). Estimating came closer to the original study's value on {counts}. "
            f"The preregistered test, a one-sided Wilcoxon test on the absolute errors, was written for "
            f"{preregistered[0]}: p = {_p(preregistered[3].get('wilcoxon_p_one_sided'))}."
            + (" Jev 1.14's is a description, not a test." if n > 1 else "")
        ),
        desc=(
            f"Dot chart in {n} panel{'s' if n > 1 else ''}, {who}, with one row per statistic, showing how "
            "far the simulated answer and the population estimate land from the published human value."
        ),
        width=1000,
        height=int(ky + 18),
        body="\n".join(out),
        source=(
            f"Jev 1.13: {run_name}, 12–13 Oct 2026. "
            + ("Jev 1.14: its 14 Oct 2026 run, through TypeSafe's API directly. " if n > 1 else "")
            + "FOLLOWUP_PREREGISTRATION.md, H4. Human values are the original studies' published ones "
            "(Many Labs 2 reports only effect sizes). Errors are divided by each scale's range (1 for "
            "proportions, 6 for 1–7 ratings, 100 for percentage bands) so they share an axis; the "
            "scaled p values are a check chosen after seeing the data."
        ),
    )


def fig_models_order(
    runs: dict[str, pd.DataFrame], run_files: dict[str, str] | None = None
) -> Figure:
    from .analysis import core_order_cells, order_effects

    odfs = {m: core_order_cells(order_effects(runs[m])) for m, _c in MAIN_MODELS}

    # A refusal can drop a single cell (GPT-6 Luna Decisions refuses some
    # follow-up items), so average every model over the same (item, prompt) cells.
    def cells(o: pd.DataFrame) -> set[tuple[str, str]]:
        return set(zip(o["probe_id"], o["persona"], strict=True))

    common = set.intersection(*(cells(o) for o in odfs.values()))
    items = {pid for pid, _p in common}
    rows = []
    for m, _c in MAIN_MODELS:
        o = odfs[m]
        o = o[[k in common for k in zip(o["probe_id"], o["persona"], strict=True)]]
        sh, un = o[o["shuffled"]]["mean_tv_distance"], o[~o["shuffled"]]["mean_tv_distance"]
        rows.append(
            (
                SHORT[m],
                f"{len(sh)} shuffled cells · {len(un)} unshuffled",
                float(un.mean()),
                float(sh.mean()),
            )
        )
    rows.sort(key=lambda r: r[3])
    body = dumbbell(
        rows,
        ref_name="Never shuffled: the floor",
        focal_name="Options shuffled",
        row_colour={SHORT[m]: c for m, c in MAIN_MODELS},
        axis_title="mean change in the answer distribution between repeats (total-variation distance)",
        step=0.05,
        fmt="{:.3f}",
        order_note="ROWS BY THE SHUFFLED VALUE",
    )
    return Figure(
        slug="models-order-effects",
        eyebrow=f"Option order · {_count(len(MAIN_MODELS))} models",
        title=f"How much {_count(len(MAIN_MODELS))} System One models' answers change when the options are shuffled",
        subtitle=(
            "Each item was asked 10 times. Multiple-choice options were put in a new random order every time; "
            "Likert and yes/no items were left as they were, so they show how much the answers move with nothing "
            "changed. The gap between the two is the order effect. 0 means identical distributions, 1 no overlap."
        ),
        desc=f"Dumbbell chart of {_count(len(MAIN_MODELS))} System One models' mean answer change between repeats, for shuffled "
        "multiple-choice items and for never-shuffled items.",
        width=1000,
        height=510,
        body=body,
        source=f"Mean distance over all pairs of the 10 repeats, per item and prompt, on the {len(common)} item-and-"
        f"prompt cells ({len(items)} items) all {_count(len(MAIN_MODELS))} runs share; the follow-up items are left "
        f"out, as for H6. {_order_notes(rows)}{_main_when(run_files)}",
    )


def _order_notes(rows: list[tuple[str, str, float, float]]) -> str:
    """Say why a row looks odd before a reader takes it for a bug."""
    notes = []
    for name, _sub, floor, shuffled in rows:
        if floor < 0.0005:
            whose = f"{name}'" if name.endswith("s") else f"{name}'s"
            notes.append(
                f"{whose} floor is 0 because it returns the identical distribution on every repeat "
                "when nothing is shuffled."
            )
        elif shuffled < floor:
            notes.append(
                f"{name} varies slightly less with shuffled options than without, so it shows no "
                "order effect beyond its repeat-to-repeat noise."
            )
    return " ".join(notes) + (" " if notes else "")


def _shown_path(path: Path) -> str:
    """A run's path as a reader can find it: repo-relative when inside the repo."""
    from .config import REPO_ROOT

    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(path.resolve())


# -- the option-order addendum ---------------------------------------------------

ORDER_STUDY_NAMES = {
    "crt": "CRT",
    "holt_laury": "Holt\u2013Laury",
    "prisoners_dilemma": "Prisoner's dilemma",
    "public_goods_conditional": "Public goods (conditional)",
}


def fig_order_study(inst: pd.DataFrame) -> Figure | None:
    """The option-order addendum (ORDER_PREREGISTRATION.md), one row per instrument.

    Left: how much more the answers move when the options are shuffled than
    when the same request is repeated (O1; O2 is the gap between the two
    versions). Right: the slot slope, the change in an option's probability
    from first place to last (O3). Both Jev versions on every row, in their
    colours and shapes from the main charts.
    """
    need = {"O1 1.13", "O1 1.14", "O3 1.13", "O3 1.14"}
    if inst.empty or not need <= set(inst["test"]):
        return None
    wide = inst.pivot_table(index="instrument", columns="test", values="value")
    wide = wide.sort_values("O1 1.13", ascending=False)
    names = [ORDER_STUDY_NAMES.get(n, n.replace("_", " ").capitalize()) for n in wide.index]
    versions = [("1.14", JEV_114_ID, JEV_114), ("1.13", JEV_113, JEV_PINK)]
    n = len(wide)
    pitch, y0 = 22, 96
    last = y0 + (n - 1) * pitch
    panels = [
        ("O1", 320, 610, _domain([*wide["O1 1.13"], *wide["O1 1.14"]], 0.05), 0.05, "{:.2f}",
         "EXTRA MOVEMENT WHEN SHUFFLED (TOTAL VARIATION)"),
        ("O3", 660, 960, _domain([*wide["O3 1.13"], *wide["O3 1.14"]], 0.1), 0.1, "{:+.1f}",
         "SLOT SLOPE: PROBABILITY, FIRST PLACE TO LAST"),
    ]  # fmt: skip
    out: list[str] = []
    for test, a, b, (lo, hi), step, fmt, title in panels:

        def px(v: float, a: int = a, b: int = b, lo: float = lo, hi: float = hi) -> float:
            return a + (v - lo) / (hi - lo) * (b - a)

        for i in range(round((hi - lo) / step) + 1):
            t = lo + i * step
            x = px(t)
            zero = abs(t) < 1e-9
            out.append(
                f'<line x1="{x:.1f}" y1="{y0 - 14}" x2="{x:.1f}" y2="{last + 14}" '
                f'stroke="{ink(0.25 if zero else 0.08)}" stroke-width="{1 if zero else 0.8}"/>'
            )
            label = "0" if zero else fmt.format(t)
            out.append(
                _t(x, last + 30, label, anchor="middle", extra=f' data-tick="x" data-value="{t:g}"')
            )
        out.append(_t((a + b) / 2, last + 46, title, size=7, anchor="middle", spacing="0.14em"))
        if test == "O3":
            out.append(_t(a, y0 - 30, "\u2190 FIRST OPTION GAINS", size=7, spacing="0.1em"))
            out.append(
                _t(b, y0 - 30, "LATER OPTIONS GAIN \u2192", size=7, spacing="0.1em", anchor="end")
            )
        else:
            out.append(_t(a, y0 - 30, "MORE THAN REPEAT NOISE \u2192", size=7, spacing="0.1em"))
        for k, inst_name in enumerate(wide.index):
            y = y0 + k * pitch
            v13, v14 = (
                float(str(wide.at[inst_name, f"{test} 1.13"])),
                float(str(wide.at[inst_name, f"{test} 1.14"])),
            )
            out.append(
                f'<line x1="{px(v13):.1f}" y1="{y}" x2="{px(v14):.1f}" y2="{y}" stroke="{ink(0.3)}" stroke-width="1"/>'
            )
            for v, (ver, model, colour) in zip((v14, v13), versions, strict=True):
                out.append(
                    _mark(
                        MAIN_SHAPES[model],
                        px(v),
                        y,
                        4,
                        f'data-series="Jev {ver}" data-panel="{test}" data-value="{v:.4f}" '
                        + _model_style(model, colour),
                        title=f"Jev {ver} · {names[k]} · {v:.3f}",
                    )
                )
    for k, name in enumerate(names):
        out.append(_t(296, y0 + k * pitch + 4, name, size=10, fill=INK, family=SANS, anchor="end"))
    ly = last + 58
    out.append(_legend(1000, ly, []))
    x = 104
    for _ver, model, colour in versions:
        x = _model_key(out, x, ly + 31, model, colour)
    out.append(_t(970, ly + 35, "ROWS BY JEV 1.13'S EXTRA MOVEMENT", anchor="end"))
    return Figure(
        slug="order-study",
        eyebrow="Option order · Jev 1.14 and 1.13 · preregistered addendum",
        title="Shuffling the options moves Jev's answers, in both versions, by about the same",
        subtitle=(
            "Each row is one instrument. Left: how much more the answers move between repeats when the options "
            "are put in a new order each time than when the same request is repeated; above 0 is an order "
            "effect. Right: how an option's probability changes as it moves from first place to last, with each "
            "option's own pull removed."
        ),
        desc=f"Two-panel dot chart of {n} instruments: for Jev 1.13 and Jev 1.14, the extra answer movement "
        "when options are shuffled, and the change in an option's probability from first place to last.",
        width=1000,
        height=ly + 50,
        body="\n".join(out),
        source="Both versions called through TypeSafe's API directly on 14 Oct 2026, 10 repeats of each item "
        "under each of five prompts. Tests and their preregistration: ORDER_PREREGISTRATION.md; tables in "
        "results/order_study/.",
    )


# -- pick a number between 1 and 10 (exploratory) -----------------------------

PICK_NUMBERS = [str(i) for i in range(1, 11)]
PICK_PROMPTS = [("neutral", "asked plainly"), ("typical_human", "as a typical person")]


def _pick_cell(table: pd.DataFrame, model: str, persona: str, kind: str) -> pd.Series:
    rows = table[
        (table["arm"] == "jev")
        & (table["model"] == model)
        & (table["persona"] == persona)
        & table["source"].str.endswith(kind)
    ]
    if len(rows) != 1:
        raise KeyError(f"{model}/{persona}/{kind}: {len(rows)} rows in the pick-number table")
    return rows.iloc[0]


def _pick_groups(table: pd.DataFrame) -> list[tuple[str, list[str]]]:
    """The System One models in groups of at most eight rows.

    Models that fit in one chart form one group. Past eight they split into
    Jev with the main comparison's three other models, then the rest; a part
    still over eight is cut into balanced chunks (nine becomes five and four),
    so every dumbbell keeps to its 4-8 rows wherever the counts allow.
    """
    from .pick_number import is_jev, system_one_name

    models = sorted(
        {str(m) for m in table.loc[table["arm"] == "jev", "model"]}, key=system_one_name
    )
    if len(models) <= 8:
        return [("the System One models", models)]
    main_ids = {m for m, _c in MAIN_MODELS}
    # The main charts' models, in the main charts' order (newest Jev first).
    order = [SHORT[m] for m, _c in MAIN_MODELS]
    first = sorted(
        (m for m in models if is_jev(m) or m in main_ids),
        key=lambda m: (
            order.index(system_one_name(m)) if system_one_name(m) in order else len(order)
        ),
    )
    rest = [m for m in models if m not in first]
    groups: list[tuple[str, list[str]]] = []
    for label, ms in (("Jev and the main comparison's models", first),
                      ("the other System One models", rest)):  # fmt: skip
        if not ms:
            continue
        k = -(-len(ms) // 8)
        size = -(-len(ms) // k)
        chunks = [ms[i : i + size] for i in range(0, len(ms), size)]
        for i, chunk in enumerate(chunks):
            groups.append((label if k == 1 else f"{label} ({i + 1} of {k})", chunk))
    return groups


def _pick_colour(model: str) -> tuple[str, str]:
    """(fill, edge) for a model's marks, in its colour from the main comparison."""
    from .pick_number import is_jev, system_one_name

    if is_jev(model):
        colour = JEV_114 if system_one_name(model) == "Jev 1.14" else JEV_PINK
    else:
        colour = model_colour(model)
    return colour, edge(colour)


def _pick_one_pick(table: pd.DataFrame, model: str, persona: str) -> str:
    """'7 in 100 of 100 calls': what reading one pick per call gives."""
    row = _pick_cell(table, model, persona, "one pick per call")
    top = max(PICK_NUMBERS, key=lambda k: float(row[k]))
    n = int(row["n"])
    return f"{top} in {round(float(row[top]) * n)} of {n} calls"


def _pick_bars(
    out: list[str],
    x0: float,
    y0: float,
    w: float,
    h: float,
    ceil: float,
    people: list[float],
    values: list[float],
    who: str,
    fill: str,
    edge: str,
    step: float = 0.2,
) -> None:
    """People's share (slate) beside the model's probability, one pair per number."""
    _pick_bar_groups(
        out, x0, y0, w, h, ceil,
        [("people", people, f'fill="{muted(0.18)}" stroke="{MUTED}"'),
         (who, values, f'fill="{fill}" fill-opacity="0.75" stroke="{edge}"')],
        step,
    )  # fmt: skip


def _pick_bar_groups(
    out: list[str],
    x0: float,
    y0: float,
    w: float,
    h: float,
    ceil: float,
    series: list[tuple[str, list[float], str]],
    step: float = 0.2,
) -> None:
    """One group of bars per number, one bar per series, on a shared scale."""
    base = y0 + h

    def y(v: float) -> float:
        return base - v / ceil * h

    for t in [i * step for i in range(int(ceil / step + 1e-9) + 1)]:
        if t:
            out.append(
                f'<line x1="{x0}" y1="{y(t):.1f}" x2="{x0 + w}" y2="{y(t):.1f}" stroke="{ink(0.08)}" stroke-width="0.8"/>'
            )
        out.append(
            _t(
                x0 - 6,
                y(t) + 3,
                f"{t:.0%}",
                anchor="end",
                extra=f' data-tick="y" data-value="{t:g}"',
            )
        )
    out.append(
        f'<line x1="{x0}" y1="{base}" x2="{x0 + w}" y2="{base}" stroke="{ink(0.25)}" stroke-width="1"/>'
    )
    pitch = w / len(PICK_NUMBERS)
    k = len(series)
    gap = 2.0
    bar = min(14.0, (pitch - 6) / k - gap)
    span = k * bar + (k - 1) * gap
    for i, n in enumerate(PICK_NUMBERS):
        cx = x0 + pitch * (i + 0.5)
        for j, (name, values, style) in enumerate(series):
            v = values[i]
            bx = cx - span / 2 + j * (bar + gap)
            by = y(v)
            out.append(
                f'<rect data-series="{esc(name)}" data-value="{v:.4f}" x="{bx:.1f}" y="{by:.1f}" '
                f'width="{bar:g}" height="{base - by:.1f}" {style} stroke-width="1">'
                f"<title>{esc(name)} · {n} · {v:.0%}</title></rect>"
            )
        out.append(_t(cx, base + 14, n, size=8, anchor="middle"))


def _pick_chat_line(table: pd.DataFrame) -> str:
    """What the chat model said, counted per prompt from the table, never assumed."""
    chat = table[table["arm"] == "baseline"]
    name = str(chat["source"].iloc[0]).split(",")[0]
    parts = []
    for persona, prompt in PICK_PROMPTS:
        row = chat[chat["persona"] == persona].iloc[0]
        top = max(PICK_NUMBERS, key=lambda k: float(row[k]))
        n = int(row["n"])
        parts.append((top, round(float(row[top]) * n), n, prompt))
    if all(k == parts[0][0] and c == n for k, c, n, _p in parts):
        return (
            f"{name}, asked {sum(n for *_, n, _p in parts)} times, said {parts[0][0]} every time."
        )
    said = "; ".join(f"{prompt}, {k} in {c} of {n} calls" for k, c, n, prompt in parts)
    return f"{name}'s most common answer: {said}."


def _pick_calls(table: pd.DataFrame, models: list[str] | None = None) -> str:
    """How many calls each plotted cell holds, from the table: "100", or "50 to 100"."""
    if models:
        # The plotted rows only: a reply can keep its distribution but lose its
        # single pick, so the one-pick rows may count fewer.
        rows = table[
            (table["arm"] == "jev")
            & table["model"].isin(models)
            & table["source"].str.endswith("its distribution")
        ]
    else:
        rows = table[table["arm"] == "baseline"]
    ns = sorted({int(n) for n in rows["n"]})
    return str(ns[0]) if len(ns) == 1 else f"{ns[0]} to {ns[-1]}"


def _pick_dates(table: pd.DataFrame, models: list[str] | None = None) -> str:
    """When the plotted runs were made, from the table: "on 15 Oct 2026", or a range."""
    from datetime import date

    rows = table[table["arm"] != "people"]
    if models is not None:
        rows = rows[rows["model"].isin(models)]
    col = rows["run_dates"] if "run_dates" in rows.columns else pd.Series(dtype=str)
    days = sorted({d for v in col.dropna().astype(str) for d in v.split(" to ") if d})
    if not days:
        return "on dates not recorded"

    def fmt(d: str) -> str:
        x = date.fromisoformat(d)
        return f"{x.day} {x:%b %Y}"

    return f"on {fmt(days[0])}" if len(days) == 1 else f"between {fmt(days[0])} and {fmt(days[-1])}"


def _pick_ceil(top: float) -> float:
    """The scale ends just above the tallest bar, on a 20% gridline."""
    return max(0.4, math.ceil((top + 0.02) / 0.2) * 0.2)


PICK_PEOPLE_KEY = "People: share of 2,241 British adults (YouGov)"


PICK_JEV_PER_FIGURE = 2


def _pick_jevs(table: pd.DataFrame) -> list[str]:
    from .pick_number import is_jev, system_one_name

    # Newest version first, as in every other chart.
    return sorted(
        {str(m) for m in table.loc[table["arm"] == "jev", "model"] if is_jev(str(m))},
        key=system_one_name,
        reverse=True,
    )


def _pick_people7(table: pd.DataFrame) -> float:
    return float(table.loc[table["arm"] == "people", "share_7"].iloc[0])


def _of(n: int, m: int, noun: str) -> str:
    """'all 4 panels', 'none of the 4 panels', '3 of the 4 panels'."""
    if n == m:
        return f"all {m} {noun}"
    return f"none of the {m} {noun}" if n == 0 else f"{n} of the {m} {noun}"


def _pick_jev_claim(table: pd.DataFrame, jevs: list[str]) -> str:
    """What the panels show, counted from them rather than assumed."""
    cells = [(m, p) for m in jevs for p, _l in PICK_PROMPTS]
    picks7 = [float(_pick_cell(table, m, p, "one pick per call")["7"]) for m, p in cells]
    closer = sum(
        float(_pick_cell(table, m, p, "its distribution")["tv_from_people"])
        < float(_pick_cell(table, m, p, "one pick per call")["tv_from_people"])
        for m, p in cells
    )
    lo, hi = min(picks7), max(picks7)
    span = f"{lo:.0%}" if f"{lo:.0%}" == f"{hi:.0%}" else f"{lo:.0%} to {hi:.0%}"
    return (
        f"The single answers put {span} of calls on 7. The distribution is the closer of the two "
        f"to people in {_of(closer, len(cells), 'panels')}."
    )


def _pick_reading_claim(rows: list[tuple[str, str, float, float]]) -> str:
    """rows: (name, sub, one-pick distance, distribution distance)."""
    n = sum(dist < pick for _n, _s, pick, dist in rows)
    return f"The distribution is closer to people than the single picks for {_of(n, len(rows), 'models')}."


def _pick_prompt_claim(rows: list[tuple[str, str, float, float]], people: float) -> str:
    """rows: (name, sub, share on 7 plainly, as a typical person)."""
    up = sum(typ > plain for _n, _s, plain, typ in rows)
    past = sum(typ > people for _n, _s, _p, typ in rows)
    m = len(rows)
    return (
        f"As a typical person, {_of(up, m, 'models')} put more on 7 than when asked plainly, and "
        f"{_of(past, m, 'models')} put more on 7 than people do."
    )


def fig_pick_number_jev(
    table: pd.DataFrame, jevs: list[str] | None = None, slug: str = "pick-number-jev"
) -> Figure:
    """Up to three Jev versions' distributions against people's, under each prompt.

    Ten numbers break the bar type's eight-bar cap on purpose, as in the
    dictator chart: pooling them would hide the shape that is the finding.
    More versions go to further figures, so no panel narrows past legibility.
    """
    from .pick_number import system_one_name

    jevs = jevs if jevs is not None else _pick_jevs(table)
    if not 1 <= len(jevs) <= PICK_JEV_PER_FIGURE:
        raise ValueError(f"one Jev figure takes 1 to {PICK_JEV_PER_FIGURE} versions, got {jevs}")
    people_row = table[table["arm"] == "people"].iloc[0]
    people = [float(people_row[n]) for n in PICK_NUMBERS]

    def cell(m: str, p: str, kind: str) -> list[float]:
        return [float(_pick_cell(table, m, p, kind)[n]) for n in PICK_NUMBERS]

    chat = table[table["arm"] == "baseline"]
    chat_name = str(chat["source"].iloc[0]).split(",")[0]
    chat_rows = {p: chat[chat["persona"] == p].iloc[0] for p, _l in PICK_PROMPTS}
    # Single answers reach 100%, so the scale always runs to the top.
    ceil = 1.0
    gap = 80
    w = (880 - gap * (len(jevs) - 1)) // len(jevs)
    h = 150
    out: list[str] = []
    for col, model in enumerate(jevs):
        name = system_one_name(model)
        for row, (persona, prompt) in enumerate(PICK_PROMPTS):
            x0, y0 = 70 + col * (w + gap), 60 + row * 230
            fill, stroke = _pick_colour(model)
            dist = _pick_cell(table, model, persona, "its distribution")
            pick = _pick_cell(table, model, persona, "one pick per call")
            out.append(
                _mark(
                    shape_of(name),
                    x0 + 5,
                    y0 - 28,
                    4.5,
                    f'fill="{fill}" stroke="{stroke}" stroke-width="1"',
                )
            )
            out.append(
                _t(
                    x0 + 16,
                    y0 - 24,
                    f"{name} · {prompt}",
                    size=12,
                    family=SANS,
                    fill=INK,
                    weight=600,
                )
            )
            out.append(
                _t(x0, y0 - 10, f"Distance from people: distribution {float(dist['tv_from_people']):.2f} · "
                   f"single answers {float(pick['tv_from_people']):.2f}", size=9, family=SANS)
            )  # fmt: skip
            chat_row = chat_rows[persona]
            _pick_bar_groups(
                out, x0, y0, w, h, ceil,
                [("people", people, f'fill="{muted(0.18)}" stroke="{MUTED}"'),
                 (f"{name}, returned distribution", cell(model, persona, "its distribution"),
                  f'fill="{fill}" fill-opacity="0.75" stroke="{stroke}"'),
                 (f"{name}, single answer counted over calls", cell(model, persona, "one pick per call"),
                  f'fill="{PAPER}" stroke="{stroke}"')],
            )  # fmt: skip
            # The chat model's single answers are a level, not a fourth bar: an
            # orange rule across each number's group at its share (all on 7).
            pitch = w / len(PICK_NUMBERS)
            for i, n in enumerate(PICK_NUMBERS):
                v = float(chat_row[n])
                if v <= 0:
                    continue
                cx, ly = x0 + pitch * (i + 0.5), y0 + h - v / ceil * h
                out.append(
                    f'<line data-series="{esc(chat_name)}" data-value="{v:.4f}" '
                    f'x1="{cx - pitch / 2 + 2:.1f}" y1="{ly:.1f}" x2="{cx + pitch / 2 - 2:.1f}" '
                    f'y2="{ly:.1f}" stroke="{ANTHROPIC_ORANGE}" stroke-width="2.5" stroke-linecap="round">'
                    f"<title>{esc(chat_name)} · {n} · {v:.0%} of calls</title></line>"
                )
                out.append(_t(cx + pitch / 2 + 4, ly + 3, chat_name, size=8, family=SANS, fill=INK))
    out.append(_t(510, 470, "NUMBER PICKED", size=7, spacing="0.14em", anchor="middle"))
    out.append(_legend(1000, 480, []))
    keys: list[tuple[list[str], str]] = [
        ([f'fill="{muted(0.18)}" stroke="{MUTED}"'], PICK_PEOPLE_KEY),
        ([f'fill="{_pick_colour(m)[0]}" fill-opacity="0.75" stroke="{_pick_colour(m)[1]}"' for m in jevs],
         "Jev's returned distribution: the probability it gives each number, averaged over calls"),
        ([f'fill="{PAPER}" stroke="{_pick_colour(m)[1]}"' for m in jevs],
         "Jev's single answer: the one number each call picks, counted over calls"),
        (["chat"],
         f"{chat_name}'s single answer, counted over calls (a chat model gives nothing else)"),
    ]  # fmt: skip
    for i, (styles, label) in enumerate(keys):
        kx, ky = (104, 504) if i % 2 == 0 else (560, 504)
        ky += (i // 2) * 20
        for st in styles:
            if st == "chat":
                out.append(
                    f'<line x1="{kx}" y1="{ky + 5}" x2="{kx + 14}" y2="{ky + 5}" '
                    f'stroke="{ANTHROPIC_ORANGE}" stroke-width="2.5" stroke-linecap="round"/>'
                )
            else:
                out.append(
                    f'<rect x="{kx}" y="{ky}" width="12" height="10" rx="2" {st} stroke-width="1"/>'
                )
            kx += 15
        out.append(_t(kx + 6, ky + 9, label, size=9, family=SANS, fill=INK))
    versions = " and ".join(system_one_name(m) for m in jevs)
    calls = sorted(
        {
            int(_pick_cell(table, m, p, "its distribution")["n"])
            for m in jevs
            for p, _ in PICK_PROMPTS
        }
    )
    return Figure(
        slug=slug,
        eyebrow="Pick a number · exploratory",
        title=f"{versions}: the distribution Jev returns against its single answer",
        subtitle=(
            f"Asked for a random number from 1 to 10, {people[PICK_NUMBERS.index('7')]:.0%} of people say 7. "
            "Each Jev call returns a probability for every number (filled) and also picks one (hollow); "
            "counting the single picks is how a chat model has to be read. "
            f"{_pick_jev_claim(table, jevs)} {_pick_chat_line(table)}"
        ),
        desc=f"Four small bar charts: {versions}, asked plainly and asked to answer as a typical person. For "
        "each number from 1 to 10 they show the share of people who pick it, the probability Jev returns, the "
        f"share of calls whose single answer is that number, and the same share for {chat_name}.",
        width=1000,
        height=550,
        body="\n".join(out),
        source=f"Same scale in every panel. Jev: {' or '.join(map(str, calls))} calls per prompt, run "
        f"{_pick_dates(table, jevs)}, options shuffled per call. {chat_name}: {_pick_calls(table)} calls per "
        f"prompt at temperature 1, run {_pick_dates(table, sorted(set(chat['model'].astype(str))))}. "
        "People: YouGov, 12–13 Sep 2024, open text box; published percentages normalised. Distance: total "
        "variation, 0 (the same) to 1 (no overlap).",
    )


def _pick_name_list(models: list[str]) -> str:
    from .pick_number import system_one_name

    names = [system_one_name(m) for m in models]
    return ", ".join(names[:-1]) + " and " + names[-1] if len(names) > 1 else names[0]


def fig_pick_number_reading(
    table: pd.DataFrame, group: str, models: list[str], part: str
) -> Figure:
    """Distance from people, read one pick per call and read as the model's own distribution."""
    from .pick_number import system_one_name

    rows = []
    for m in models:
        pick = _pick_cell(table, m, "neutral", "one pick per call")
        dist = _pick_cell(table, m, "neutral", "its distribution")
        rows.append(
            (
                system_one_name(m),
                f"one pick per call: {_pick_one_pick(table, m, 'neutral')}",
                float(pick["tv_from_people"]),
                float(dist["tv_from_people"]),
            )
        )
    rows.sort(key=lambda r: r[3])
    chat = table[(table["arm"] == "baseline") & (table["persona"] == "neutral")].iloc[0]
    chat_name = str(chat["source"]).split(",")[0]
    body = dumbbell(
        rows,
        ref_name="One pick per call",
        focal_name="The model's own distribution",
        row_colour={system_one_name(m): _pick_colour(m)[0] for m in models},
        axis_title="distance from people's distribution (total variation, 0 = the same)",
        step=0.2,
        fmt="{:.2f}",
        domain=(0.0, 1.0),
        order_note="ROWS BY THE DISTRIBUTION'S DISTANCE",
        reference_line=(float(chat["tv_from_people"]), f"{chat_name.upper()}, ONE PICK PER CALL"),
    )
    return Figure(
        slug=f"pick-number-reading-{part}",
        eyebrow="Pick a number · asked plainly · exploratory",
        title=f"One pick per call against the full distribution: {group}",
        subtitle=(
            "How far each model's answers are from people's when it is asked for a random number from 1 to 10. "
            "Hollow: counting the single number each call picks, as a chat model has to be read. Filled: the "
            f"probabilities the model returns. {_pick_reading_claim(rows)} Putting everything on 7 scores "
            f"{1 - _pick_people7(table):.2f}."
        ),
        desc=f"Dumbbell chart of {_pick_name_list(models)}: each model's distance from people's distribution "
        "of picks, counted one pick per call and taken from its returned probabilities.",
        width=1000,
        height=510,
        body=body,
        source="Total-variation distance from YouGov's 2,241 British adults, 12–13 Sep 2024. Each model: "
        f"{_pick_calls(table, models)} calls, run {_pick_dates(table, models)}, options shuffled per call. Dashed line: the "
        f"chat model, {_pick_calls(table)} calls at temperature 1.",
    )


def fig_pick_number_prompt(table: pd.DataFrame, group: str, models: list[str], part: str) -> Figure:
    """Share on 7 in each model's distribution, asked plainly and as a typical person."""
    from .pick_number import system_one_name

    people = float(table.loc[table["arm"] == "people", "share_7"].iloc[0])
    rows = []
    for m in models:
        plain = _pick_cell(table, m, "neutral", "its distribution")
        typical = _pick_cell(table, m, "typical_human", "its distribution")
        peaks = [str(plain["top"]), str(typical["top"])]
        sub = (
            "peaks on 7 both times"
            if peaks == ["7", "7"]
            else f"peaks on {peaks[0]} plainly, {peaks[1]} as a typical person"
        )
        rows.append((system_one_name(m), sub, float(plain["share_7"]), float(typical["share_7"])))
    rows.sort(key=lambda r: r[3])
    body = dumbbell(
        rows,
        ref_name="Asked plainly",
        focal_name="Asked to answer as a typical person",
        row_colour={system_one_name(m): _pick_colour(m)[0] for m in models},
        axis_title="share of the model's probability on 7",
        step=0.2,
        fmt="{:.0%}",
        domain=(0.0, 1.0),
        order_note="ROWS BY THE TYPICAL-PERSON SHARE",
        reference_line=(people, f"PEOPLE {people:.0%}"),
    )
    return Figure(
        slug=f"pick-number-prompt-{part}",
        eyebrow="Pick a number · two prompts · exploratory",
        title=f"Share on 7, asked plainly and as a typical person: {group}",
        subtitle=(
            f"The share of each model's returned probability on 7, the number {people:.0%} of people pick. Asked "
            "to answer as a typical person, a model that knew people's answers would move towards the dashed "
            f"line. {_pick_prompt_claim(rows, people)}"
        ),
        desc=f"Dumbbell chart of {_pick_name_list(models)}: the share of each model's distribution on 7 when "
        "asked plainly and when asked to answer as a typical person, against people's 33%.",
        width=1000,
        height=510,
        body=body,
        source=f"Each model: mean of {_pick_calls(table, models)} returned distributions per prompt, run "
        f"{_pick_dates(table, models)}, options shuffled per "
        "call. People: YouGov, 2,241 British adults, 12–13 Sep 2024.",
    )


def fig_pick_number_models(table: pd.DataFrame, group: str, models: list[str], part: str) -> Figure:
    """Each model's distribution, asked plainly, against people's: one small panel per model."""
    from .pick_number import system_one_name

    people_row = table[table["arm"] == "people"].iloc[0]
    people = [float(people_row[n]) for n in PICK_NUMBERS]
    dists = {
        m: [float(_pick_cell(table, m, "neutral", "its distribution")[n]) for n in PICK_NUMBERS]
        for m in models
    }
    ceil = _pick_ceil(max(max(people), *(max(v) for v in dists.values())))
    w, h = 250, 140
    out: list[str] = []
    for i, m in enumerate(models):
        x0, y0 = 70 + (i % 3) * 320, 60 + (i // 3) * 220
        fill, edge = _pick_colour(m)
        name = system_one_name(m)
        dist = _pick_cell(table, m, "neutral", "its distribution")
        out.append(
            _mark(
                shape_of(name),
                x0 + 5,
                y0 - 28,
                4.5,
                f'fill="{fill}" stroke="{edge}" stroke-width="1"',
            )
        )
        out.append(_t(x0 + 16, y0 - 24, name, size=12, family=SANS, fill=INK, weight=600))
        out.append(
            _t(x0, y0 - 10, f"on 7: {float(dist['share_7']):.0%} · distance from people "
               f"{float(dist['tv_from_people']):.2f}", size=9, family=SANS)
        )  # fmt: skip
        _pick_bars(out, x0, y0, w, h, ceil, people, dists[m], name, fill, edge)
    rows = -(-len(models) // 3)
    axis_y = 60 + rows * 220 - 40
    out.append(_t(510, axis_y, "NUMBER PICKED", size=7, spacing="0.14em", anchor="middle"))
    rule = axis_y + 10
    out.append(_legend(1000, rule, []))
    out.append(
        f'<rect x="104" y="{rule + 24}" width="16" height="10" rx="2" fill="{muted(0.18)}" stroke="{MUTED}" stroke-width="1"/>'
    )
    out.append(_t(128, rule + 33, PICK_PEOPLE_KEY, size=9, family=SANS, fill=INK))
    sx = 128 + text_width(PICK_PEOPLE_KEY, 9) + 40
    for fill, edge in dict.fromkeys(_pick_colour(m) for m in models):
        out.append(
            f'<rect x="{sx:g}" y="{rule + 24}" width="10" height="10" rx="2" fill="{fill}" fill-opacity="0.75" stroke="{edge}" stroke-width="1"/>'
        )
        sx += 13
    out.append(
        _t(sx + 8, rule + 33, f"The model's returned probability, mean of {_pick_calls(table, models)} calls", size=9,
           family=SANS, fill=INK)
    )  # fmt: skip
    return Figure(
        slug=f"pick-number-models-{part}",
        eyebrow="Pick a number · asked plainly · exploratory",
        title=f"Pick a number between 1 and 10: {group}' returned distributions against people",
        subtitle=(
            "Slate: the share of people picking each number. Coloured: the probability each model returns for "
            "it. Distance is total variation from people's distribution, 0 (the same) to 1 (no overlap)."
        ),
        desc=f"Small bar charts, one per model ({_pick_name_list(models)}), each showing the probability the "
        "model returns for each number from 1 to 10 next to the share of people who pick it.",
        width=1000,
        height=rule + 50,
        body="\n".join(out),
        source=f"Same scale in every panel. Each model: mean of {_pick_calls(table, models)} returned "
        f"distributions, run {_pick_dates(table, models)}, "
        "options shuffled per call. People: YouGov, 2,241 British adults, 12–13 Sep 2024.",
    )


def _part(i: int) -> str:
    """Group suffixes without end: a, b, ..., z, aa, ab, ..."""
    out = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        out = chr(97 + r) + out
    return out


def pick_number_figures(table: pd.DataFrame) -> list[Figure]:
    """Every pick-number figure the run set supports.

    A dumbbell takes 4 to 8 rows; `_pick_groups` keeps every group to eight.
    A group under four models gets the small multiples, which take any
    number, but no dumbbells.
    """
    jevs = _pick_jevs(table)
    k = -(-len(jevs) // PICK_JEV_PER_FIGURE)
    size = -(-len(jevs) // k)
    figures = [
        fig_pick_number_jev(
            table, jevs[i : i + size], "pick-number-jev" + (f"-{i // size + 1}" if i else "")
        )
        for i in range(0, len(jevs), size)
    ]
    for i, (group, models) in enumerate(_pick_groups(table)):
        part = _part(i)
        if len(models) >= 4:
            figures += [
                fig_pick_number_reading(table, group, models, part),
                fig_pick_number_prompt(table, group, models, part),
            ]
        figures.append(fig_pick_number_models(table, group, models, part))
    return figures


def build_pick_number_diagrams(
    table: pd.DataFrame, out_dir: Path, png_dir: Path | None = None
) -> list[Path]:
    """Write every pick-number figure, and remove any an earlier build left that
    this one does not draw (a second model group that no longer exists), so no
    stale figure can be linked or embedded."""
    out_dir.mkdir(parents=True, exist_ok=True)
    figures = pick_number_figures(table)
    slugs = {f.slug for f in figures}
    for d, ext in ((out_dir, "html"), (png_dir, "png")):
        for old in d.glob(f"pick-number-*.{ext}") if d else []:
            if old.stem not in slugs:
                old.unlink()
    paths = []
    for f in figures:
        p = out_dir / f"{f.slug}.html"
        p.write_text(f.html(), encoding="utf-8")
        paths.append(p)
    return paths


def build_diagrams(
    run_path: Path,
    tables_dir: Path,
    comparison_dir: Path,
    out_dir: Path,
    raw_dir: Path | None = None,
) -> list[Path]:
    """Build every figure. `tables_dir` must hold the analysis of `run_path`."""
    from .analysis import load_records

    fdf = pd.read_csv(comparison_dir / "fidelity.csv")
    mdf = pd.read_csv(comparison_dir / "measures.csv")
    # The multi-model charts read each main model's statistics from the
    # comparison, and its run file (named in health.csv) for distributions.
    cdf = pd.read_csv(comparison_dir / "statistics.csv")
    files = dict(
        zip(
            *pd.read_csv(comparison_dir / "health.csv")[["model", "run_file"]].T.values, strict=True
        )
    )
    # health.csv names each run file by basename; they live in the raw-data
    # directory whatever single run `run_path` points at.
    from .config import RAW_DIR

    raw = raw_dir or RAW_DIR
    missing = [m for m, _c in MAIN_MODELS if m not in files]
    if missing:
        raise ValueError(
            f"the comparison has no run for {', '.join(missing)}; rebuild it with every run, "
            "including data/raw/order_study/r1/run_live_20261014T231829Z_jev-1.14.0.jsonl"
        )
    # Every run by its full path under the chosen raw directory, so the source
    # lines read each run's route from the same files the charts are drawn from.
    files = {m: str(raw / f) for m, f in files.items()}
    runs = {m: load_records(Path(files[m])) for m, _c in MAIN_MODELS}

    figures = [
        fig_process(),
        fig_models_tests(cdf, "decisions", files),
        fig_framing(mdf, files),
        fig_models_tests(cdf, "games", files),
        fig_models_scatter(fdf, files),
        fig_jev_steer(cdf, files),
        fig_models_antisocial(cdf, files),
        fig_models_dictator(runs, files),
        fig_models_order(runs, files),
        fig_health(files),
    ]
    # Follow-up H4 is drawn only when the run has paired items to draw.
    h4_path = tables_dir / "followup_h4.csv"
    h4 = pd.read_csv(h4_path) if h4_path.exists() and h4_path.stat().st_size else pd.DataFrame()
    if len(h4):
        from .analysis import simulate_vs_estimate

        # Jev 1.14's table comes from the comparison, beside the run's own 1.13.
        h114 = simulate_vs_estimate(cdf.rename(columns={"model": "arm"}), arm=JEV_114_ID)
        panels = ([(JEV_114_ID, h114)] if len(h114) else []) + [(JEV_113, h4)]
        figures.insert(6, fig_h4(panels, _shown_path(run_path)))
    else:
        # Leave no chart from an earlier run behind.
        (out_dir / f"{H4_SLUG}.html").unlink(missing_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for f in figures:
        p = out_dir / f"{f.slug}.html"
        p.write_text(f.html(), encoding="utf-8")
        paths.append(p)
    return paths


# The editorial figures name the run they show in their titles and source
# lines; a run must match these to be drawn by them.
EDITORIAL_MODEL = "typesafe/jev-1.13-20260917"
EDITORIAL_REPLICATES = 10
EDITORIAL_DATES = frozenset({"2026-10-12", "2026-10-13"})
# The Allais and Holt-Laury items were asked again on this day, without their
# index in the state (data/raw/rerun_state_cues/); the run's records of them
# are the re-run's.
RERUN_DATE = "2026-10-17"


def check_editorial_run(df: pd.DataFrame) -> None:
    """Refuse a run the figures' fixed labels would misdescribe."""
    jev = df[df["arm"] == "jev"]
    problems = []
    models = sorted(set(jev["model"].dropna()))
    if models != [EDITORIAL_MODEL]:
        problems.append(f"model {', '.join(models) or 'none'} (labelled {EDITORIAL_MODEL})")
    dates = set(jev["timestamp"].dropna().astype(str).str[:10]) if "timestamp" in jev else set()
    if dates - {RERUN_DATE} != EDITORIAL_DATES:
        problems.append(f"dates {', '.join(sorted(dates)) or 'none'} (labelled 12-13 Oct 2026)")
    # Every core item under every prompt needs its full set of successful
    # repeats, since the figures say "mean over 10 repeats"; the follow-up
    # battery is optional.
    from .instruments import MODULES, PERSONAS, all_probes

    if missing := sorted(set(PERSONAS) - set(jev["persona"])):
        problems.append(f"no records under {', '.join(missing)}")
    # A repeat counts only with a usable distribution: a reply with no
    # probabilities is skipped by the analysis, so it is not one of the 10.
    usable = jev["probabilities"].map(lambda d: isinstance(d, dict) and bool(d))
    ok = jev[usable & jev["error"].isna()] if "error" in jev else jev[usable]
    cells = ok.groupby(["probe_id", "persona"])["replicate"]
    distinct, rows = cells.nunique(), cells.size()
    core = [p.probe_id for p in all_probes([m for m in MODULES if m != "followup"])]
    off = sum(
        int(
            distinct.get((pid, persona), 0) != EDITORIAL_REPLICATES
            or rows.get((pid, persona), 0) != EDITORIAL_REPLICATES
        )
        for pid in core
        for persona in PERSONAS
    )
    if off:
        problems.append(
            f"{off} of {len(core) * len(PERSONAS)} core item-and-prompt cells do not have exactly "
            f"{EDITORIAL_REPLICATES} successful repeats"
        )
    if problems:
        raise ValueError(
            "the editorial figures are labelled for the committed run and would misdescribe "
            "this one: " + "; ".join(problems) + ". Use `jevbench figures` for other runs."
        )


def build_diagrams_for_run(
    run_path: Path, comparison_dir: Path, out_dir: Path, raw_dir: Path | None = None
) -> list[Path]:
    """Build every figure, the single-model ones from `run_path` analysed afresh.

    Reading saved tables instead would let a figure show another run's numbers
    whenever `--run` names a different run, or the tables were not rebuilt.
    """
    import tempfile

    from .analysis import analyse_run, load_records

    check_editorial_run(load_records(run_path))
    with tempfile.TemporaryDirectory(prefix="jevbench-diagrams-") as tmp:
        tables = Path(tmp)
        analyse_run(run_path, tables)
        return build_diagrams(run_path, tables, comparison_dir, out_dir, raw_dir)


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

    from .analysis import primary_run
    from .config import RAW_DIR, REPO_ROOT

    ap = argparse.ArgumentParser(description="build the editorial figures")
    ap.add_argument("--run", default=None, help="the Jev run (default: the newest run with Jev)")
    ap.add_argument("--no-png", action="store_true")
    args = ap.parse_args(argv)
    run = Path(args.run) if args.run else primary_run(RAW_DIR, live_only=True)
    if run is None:
        print(f"No live run with Jev in {RAW_DIR}.", file=sys.stderr)
        return 1
    html_dir = REPO_ROOT / "docs" / "diagrams"
    try:
        paths = build_diagrams_for_run(run, REPO_ROOT / "results" / "comparison", html_dir)
    except ValueError as e:
        print(f"{run.name}: {e}", file=sys.stderr)
        return 1
    for p in paths:
        print(f"wrote {p.relative_to(REPO_ROOT)}")
    if not args.no_png:
        png_dir = REPO_ROOT / "results" / "figures"
        for p in export_pngs(paths, png_dir):
            print(f"wrote {p.relative_to(REPO_ROOT)}")
        if not (html_dir / f"{H4_SLUG}.html").exists():
            (png_dir / f"{H4_SLUG}.png").unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
