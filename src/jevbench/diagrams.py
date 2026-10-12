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
ACCENT = "#bf4520"
LINK = "#2e5aa8"
WHITE = "#ffffff"


def ink(a: float) -> str:
    return f"rgba(45,49,66,{a})"


def accent(a: float) -> str:
    return f"rgba(191,69,32,{a})"


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
    rows: list[tuple[str, float, float]],
    *,
    ref_name: str,
    focal_name: str,
    axis_title: str,
    step: float,
    fmt: str = "{:.2f}",
    domain: tuple[float, float] | None = None,
    order_note: str,
    reference_line: tuple[float, str] | None = None,
) -> str:
    """Rows of (label, reference value, focal value) inside `0 0 1000 500`."""
    n = len(rows)
    if not 4 <= n <= 8:
        raise ValueError(f"dumbbell takes 4-8 rows, got {n}")
    pitch, y0 = ROW_LAYOUT[n]
    vals = [v for _, a, b in rows for v in (a, b)]
    if reference_line:
        vals.append(reference_line[0])
    floor, ceil = domain or _domain(vals, step)

    def px(v: float) -> int:
        return round(200 + (v - floor) / (ceil - floor) * 760)

    out: list[str] = []
    ticks = [floor + i * step for i in range(round((ceil - floor) / step) + 1)]
    for t in ticks:
        x = px(t)
        is_axis = abs(t - floor) < 1e-9
        if not is_axis:
            out.append(
                f'<line x1="{x}" y1="56" x2="{x}" y2="408" stroke="{ink(0.08)}" stroke-width="0.8"/>'
            )
        out.append(
            _t(x, 440, fmt.format(t), anchor="middle", extra=f' data-tick="x" data-value="{t:g}"')
        )
    out.append(f'<line x1="200" y1="40" x2="200" y2="420" stroke="{ink(0.25)}" stroke-width="1"/>')
    if floor < 0 < ceil:
        out.append(
            f'<line x1="{px(0)}" y1="40" x2="{px(0)}" y2="420" stroke="{ink(0.25)}" stroke-width="1"/>'
        )
    out.append(_t(580, 456, axis_title.upper(), size=7, anchor="middle", spacing="0.14em"))

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

    for i, (label, a, b) in enumerate(rows):
        y = y0 + i * pitch
        xa, xb = px(a), px(b)
        close = abs(xa - xb) < 16
        r = 4 if close else 6
        out.append(
            f'<line x1="{xa}" y1="{y}" x2="{xb}" y2="{y}" stroke="{ink(0.55)}" stroke-width="1"/>'
        )
        out.append(
            f'<circle data-series="reference" data-value="{a:.4f}" cx="{xa}" cy="{y}" r="{r}" fill="{PAPER}" stroke="{MUTED}" stroke-width="1.5"/>'
        )
        out.append(
            f'<circle data-series="focal" data-value="{b:.4f}" cx="{xb}" cy="{y}" r="{r}" fill="{ACCENT}" stroke="{INK}" stroke-width="1"/>'
        )
        left, right = (a, b) if xa <= xb else (b, a)
        xl, xr = min(xa, xb), max(xa, xb)
        if close:
            # Too close to separate two labels: print both above the pair.
            out.append(
                _t(
                    (xa + xb) / 2,
                    y - 10,
                    f"{fmt.format(a)} · {fmt.format(b)}",
                    anchor="middle",
                    halo=True,
                )
            )
        else:
            # The floor exception, by drawn width rather than anchor: a left label
            # that would reach into the row-label column goes above its dot.
            if xl - 12 - text_width(fmt.format(left), 8, mono=True) < 196:
                out.append(_t(xl, y - 10, fmt.format(left), anchor="middle", halo=True))
            else:
                out.append(_t(xl - 12, y + 4, fmt.format(left), anchor="end", halo=True))
            out.append(_t(xr + 12, y + 4, fmt.format(right), halo=True))
        out.append(_t(188, y + 4, label, size=11, fill=INK, family=SANS, anchor="end", weight=600))

    keys = [
        f'<circle cx="104" cy="493" r="5" fill="{PAPER}" stroke="{MUTED}" stroke-width="1.5"/>',
        _t(116, 497, ref_name, size=9, family=SANS, fill=INK),
        f'<circle cx="{132 + text_width(ref_name, 9) + 24:g}" cy="493" r="5" fill="{ACCENT}" stroke="{INK}" stroke-width="1"/>',
        _t(132 + text_width(ref_name, 9) + 36, 497, focal_name, size=9, family=SANS, fill=INK),
    ]
    out.append(_legend(1000, 462, [], ""))
    out.extend(keys)
    out.append(_t(970, 497, order_note, anchor="end"))
    return "\n".join(out)


# -- figure builders -------------------------------------------------------------

DECISION_MEASURES = [
    ("crt", "proportion_correct", "crt_proportion_correct", "Cognitive reflection"),
    ("framing", "prob_certain_gain_frame", "framing_gain_certain", "Framing: gain"),
    ("framing", "prob_certain_loss_frame", "framing_loss_certain", "Framing: loss"),
    ("allais", "prob_certain_pair1", "allais_p1_certain", "Allais certainty"),
    (
        "conjunction",
        "prob_fallacy_forced_choice",
        "conjunction_fallacy_rate",
        "Conjunction fallacy",
    ),
    ("base_rate", "prob_correct_band", "base_rate_correct_band", "Base rate"),
    ("sunk_cost", "prob_continue", "sunk_cost_continue", "Sunk cost"),
]

GAME_MEASURES = [
    ("dictator", "mean_share", "dictator_mean_share", "Dictator giving"),
    ("ultimatum_proposer", "mean_share", "ultimatum_mean_offer", "Ultimatum offer"),
    (
        "ultimatum_responder",
        "prob_reject_low_offer",
        "ultimatum_rejection_low_offer",
        "Reject low offer",
    ),
    ("trust_sender", "mean_share", "trust_sender_share", "Trust sent"),
    ("trust_trustee", "return_share_sent_5", "trust_return_share", "Trust returned"),
    ("public_goods", "mean_share", "pgg_round1_share", "Public goods"),
    ("prisoners_dilemma", "cooperation_one_shot", "pd_cooperation_oneshot", "PD cooperate"),
]

DECISION_LABELS = {
    "Cognitive reflection": "share correct",
    "Framing: gain": "picks the sure option",
    "Framing: loss": "picks the sure option",
}


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
    rows = [(label, BENCHMARKS[b].value, _stat(sdf, i, s, persona)) for i, s, b, label in measures]
    as_person = persona == "typical_human"
    slug = f"jev-{which}-{'typical' if as_person else 'neutral'}"
    focal = "Jev, as a typical person" if as_person else "Jev, answering neutrally"
    if which == "decisions":
        title = (
            "Asked to answer like a person, it makes people's mistakes"
            if as_person
            else "Left to itself, Jev does not make people's mistakes"
        )
        subtitle = (
            "One added sentence — answer the way a typical participant would — and Jev lands near "
            "the published human rate on almost every classic decision anomaly."
            if as_person
            else "Seven classic decision anomalies. Under neutral framing Jev sits near the normative "
            "answer, far from the published human rate, on all but the framing items."
        )
    else:
        title = "In the money games, it gives less than people do"
        subtitle = (
            "Share given or sent, and rates of rejecting and cooperating, in five economic games. "
            "Positive giving is not equilibrium play: Jev lands nearer people than game theory."
        )
    body = dumbbell(
        rows,
        ref_name="Published human rate",
        focal_name=focal,
        axis_title="probability or share of the endowment",
        step=0.2,
        fmt="{:.2f}",
        domain=(0.0, 1.0),
        order_note="ROWS IN BATTERY ORDER",
    )
    return Figure(
        slug=slug,
        eyebrow="Dumbbell · Jev 1.13 against people",
        title=title,
        subtitle=subtitle,
        desc=f"Dumbbell chart comparing Jev's answers, {'asked to answer as a typical person' if as_person else 'under neutral framing'}, with published human rates on {len(rows)} {'decision anomalies' if which == 'decisions' else 'economic-game measures'}.",
        width=1000,
        height=510,
        body=body,
        source="Jev values: mean of the returned probability distributions over 10 replicates, run of 18 Sep 2026. "
        "Human values: published single studies or meta-analyses (docs/BENCHMARKS.md); separate samples, not a control group.",
    )


def fig_antisocial(sdf: pd.DataFrame) -> Figure:
    rows = [
        (label, _stat(sdf, i, s, "neutral"), _stat(sdf, i, s, "antisocial"))
        for i, s, _b, label in GAME_MEASURES
    ]
    dt_n = _stat(sdf, "dirty_dozen", "overall", "neutral")
    dt_a = _stat(sdf, "dirty_dozen", "overall", "antisocial")
    body = dumbbell(
        rows,
        ref_name="Answering neutrally",
        focal_name="With an antisocial persona",
        axis_title="probability or share of the endowment",
        step=0.2,
        domain=(0.0, 1.0),
        order_note="ROWS IN BATTERY ORDER",
    )
    return Figure(
        slug="persona-antisocial",
        eyebrow="Dumbbell · persona steerability",
        title="A persona reaches the money, not just the self-description",
        subtitle=(
            f"An antisocial persona moved Jev's Dark Triad self-report from {dt_n:.1f} to {dt_a:.1f} on a "
            "9-point scale — the manipulation check. It also collapsed giving in every game."
        ),
        desc="Dumbbell chart of Jev's choices in seven economic-game measures answering neutrally and with an antisocial persona; giving falls in every game.",
        width=1000,
        height=510,
        body=body,
        source="Mean of returned distributions, 10 replicates per cell, run of 18 Sep 2026. The persona is a prompt "
        "manipulation: it shows what the model can be induced to output, not what it is.",
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
            f'fill="{accent(0.12) if focal else muted(0.15)}" stroke="{ACCENT if focal else MUTED}" stroke-width="1"/>'
        )
        out.append(_t(cx, by - 8, f"{v:.2f}", anchor="middle", fill=ACCENT if focal else MUTED))
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
        eyebrow="Bar chart · what a single call returns",
        title="One call returns the whole distribution, not just an answer",
        subtitle=(
            "Jev's probability over every allocation in the dictator game, from a single request. A chat model "
            "has to be asked the same question many times to estimate this, and still mixes in sampling noise."
        ),
        desc="Bar chart of Jev's returned probability of giving each amount out of ten dollars in the dictator game; most mass on giving nothing, a second peak at an even split.",
        width=1000,
        height=480,
        body="\n".join(out),
        source="Neutral framing, mean of 10 returned distributions, run of 18 Sep 2026. $6–10 pooled to keep the chart "
        "to seven bars. Human rates: Engel (2011) meta-analysis.",
    )


def fig_order_effects(odf: pd.DataFrame) -> Figure:
    edges = [0.0, 0.025, 0.05, 0.10, 0.15, 0.20, 0.31]
    names = ["< 0.025", "0.025–0.05", "0.05–0.10", "0.10–0.15", "0.15–0.20", "≥ 0.20"]
    tv = odf["mean_tv_distance"]
    counts = [int(((tv >= lo) & (tv < hi)).sum()) for lo, hi in itertools.pairwise(edges)]
    counts[-1] = int((tv >= 0.20).sum())
    n = len(tv)
    ceil = int(math.ceil(max(counts) / 50) * 50)

    def y(v: float) -> float:
        return 420 - v / ceil * 380

    pitch, bar = 140, 96
    x0 = 80 + (880 - pitch * len(counts)) / 2
    out: list[str] = []
    for t in range(0, ceil + 1, 50):
        if t:
            out.append(
                f'<line x1="80" y1="{y(t):g}" x2="960" y2="{y(t):g}" stroke="{ink(0.08)}" stroke-width="0.8"/>'
            )
        out.append(_t(72, y(t) + 3, str(t), anchor="end", extra=f' data-tick="y" data-value="{t}"'))
    out.append(f'<line x1="80" y1="420" x2="960" y2="420" stroke="{ink(0.25)}" stroke-width="1"/>')
    out.append(f'<line x1="80" y1="40" x2="80" y2="420" stroke="{ink(0.25)}" stroke-width="1"/>')
    for i, (name, c) in enumerate(zip(names, counts, strict=True)):
        cx = x0 + i * pitch + pitch / 2
        bx, by = cx - bar / 2, y(c)
        focal = i == 0
        out.append(
            f'<rect x="{bx:g}" y="{by:.1f}" width="{bar}" height="{420 - by:.1f}" fill="{PAPER}"/>'
        )
        out.append(
            f'<rect data-value="{c}" x="{bx:g}" y="{by:.1f}" width="{bar}" height="{420 - by:.1f}" '
            f'fill="{accent(0.12) if focal else muted(0.15)}" stroke="{ACCENT if focal else MUTED}" stroke-width="1"/>'
        )
        out.append(
            _t(cx, by - 8, f"{c}  ·  {c / n:.0%}", anchor="middle", fill=ACCENT if focal else MUTED)
        )
        out.append(_t(cx, 440, name, size=11, family=SANS, fill=INK, anchor="middle", weight=600))
    out.append(
        _t(
            24,
            230,
            "PROBE × PERSONA CELLS",
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
            "TOTAL-VARIATION DISTANCE BETWEEN ORDERINGS",
            size=7,
            spacing="0.14em",
            anchor="middle",
        )
    )
    return Figure(
        slug="order-effects",
        eyebrow="Bar chart · option-order sensitivity",
        title="Shuffling the options barely moves the answer",
        subtitle=(
            f"How far the returned distribution moved between replicates with the options in a different order, "
            f"for each of {n} probe-and-persona cells. 0 means nothing changed; mean {tv.mean():.3f}, median {tv.median():.3f}."
        ),
        desc="Bar chart of how many probe-and-persona cells fall in each band of total-variation distance between option orderings; most are under 0.05.",
        width=1000,
        height=480,
        body="\n".join(out),
        source="Options independently permuted per replicate, 10 replicates per cell, run of 18 Sep 2026. "
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
    "anthropic/claude-sonnet-5": "Claude Sonnet 5",
    "anthropic/claude-haiku-5.5": "Claude Haiku 5.5",
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
    note = "closer to people when asked"
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
        _t(424, ly0 + 35, f"{focal[0]}: the one that did not move", size=9, family=SANS, fill=INK)
    )
    return Figure(
        slug="models-scatter",
        eyebrow="Scatter · eleven models against people",
        title="Every model but one gets closer to people when asked",
        subtitle=(
            "Each point is a model: mean distance from the published human rate over 14 measures, answering "
            "neutrally (across) and when asked to answer as a typical person (up). Lower is closer to people."
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
        return (
            _cell(t, "Framing: certain (gain)", model)
            - _cell(t, "Framing: certain (loss)", model) * 100
        )

    human = (
        float(
            _cell(s["neutral"], "Framing: certain (gain)", "human")
            - _cell(s["neutral"], "Framing: certain (loss)", "human")
        )
        * 100
    )
    keep = [m for m in mdf.columns if m in SHORT and "anthropic" not in m and "mercury" not in m]
    rows = sorted(
        [(SHORT[m], contrast(m, "neutral"), contrast(m, "typical_human")) for m in keep],
        key=lambda r: -r[2],
    )
    body = dumbbell(
        rows,
        ref_name="Answering neutrally",
        focal_name="As a typical person",
        axis_title="gain-frame minus loss-frame rate of picking the sure option, in points",
        step=20,
        fmt="{:.0f}",
        order_note="ROWS BY THE AS-A-PERSON VALUE",
        reference_line=(human, f"PEOPLE {human:.0f}"),
    )
    return Figure(
        slug="framing-contrast",
        eyebrow="Dumbbell · the effect, not the level",
        title="Being close to people is not the same as behaving like them",
        subtitle=(
            "The framing reversal: people pick the sure option 72% of the time when it is framed as a gain and "
            "22% as a loss. Solar Decide Flash is the model closest to human levels overall, yet shows almost no reversal."
        ),
        desc="Dumbbell chart of eight System One models' framing reversal in points, answering neutrally and as a typical person, against the human value of 50.",
        width=1000,
        height=510,
        body=body,
        source="Eight System One models; the chart holds at most eight rows, so Mercury Decide (19 → 34) is listed here "
        "instead. Chat models saturate: Sonnet 5 100 → 100, Haiku 5.5 0 → 100. Human rates: Tversky & Kahneman (1981).",
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
    W, H = 960, 520
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
    a.append(_node(cols[0], mid - h // 2, w, h, "Battery item", "147 probes", tag="ITEM"))
    a.append(
        _node(cols[1], mid - h // 2, w, h, "Four framings", "4 personas × 10 reps", tag="PROMPT")
    )
    a.append(
        _node(
            cols[2],
            top - h // 2,
            w,
            h,
            "System One model",
            "1 call → probabilities",
            kind="focal",
            tag="TYPED",
        )
    )
    a.append(_node(cols[2], bot - h // 2, w, h, "Chat model", "10 samples → counted", tag="CHAT"))
    a.append(
        _node(
            cols[3],
            mid - h // 2,
            w,
            h,
            "One distribution",
            "per probe × persona",
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
            "Statistic vs people",
            "distance · correlation",
            tag="RESULT",
        )
    )
    a.append(
        _node(cols[4], 328, w, h, "Published rate", "human reference", kind="external", tag="DATA")
    )
    # Two callouts carry the cost asymmetry.
    a.append(
        _t(
            cols[2] + w / 2,
            top - h // 2 - 16,
            "reports its own distribution — $0.09 a grid",
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
            "pays ten times to estimate one — $2.74",
            size=15,
            family=SERIF,
            fill=INK,
            anchor="middle",
            extra=' font-style="italic"',
        )
    )
    a.append(_legend(W, 452, []))
    legend = [
        (accent(0.08), ACCENT, "System One path", 0),
        (WHITE, INK, "Step", 1),
        (ink(0.05), MUTED, "Stored result", 0),
        (ink(0.03), ink(0.30), "External data", 0),
    ]
    x = 104
    for fill, stroke, label, _ in legend:
        a.append(
            f'<rect x="{x}" y="482" width="16" height="10" rx="2" fill="{fill}" stroke="{stroke}" stroke-width="1"/>'
        )
        a.append(_t(x + 24, 491, label, size=9, family=SANS, fill=INK))
        x += int(24 + text_width(label, 9) + 40)
    return Figure(
        slug="how-it-works",
        eyebrow="Process · how one item becomes a number",
        title="Two ways to get a distribution out of a model",
        subtitle=(
            "Every item is asked under four framings. A System One model returns a probability for every answer in "
            "one call; a chat model has to be sampled ten times and its answers counted. Both end as one distribution "
            "per cell, compared with the published human rate."
        ),
        desc="Process diagram: a battery item is framed four ways, answered either by a System One model in one call or by a chat model sampled ten times, reduced to one distribution per cell, and compared with a published human rate.",
        width=W,
        height=H,
        body="\n".join(a),
        source="Costs are for the identical 4,680-call grid on 18 Sep 2026: Jev $0.09, Claude Sonnet 5 resampled $2.74.",
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
            "4,096 → 9 unresolved",
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
    for x, head in zip(cols, ["WHAT HEALTH.CSV SHOWED", "WHY", "WHAT CHANGED"], strict=True):
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
        eyebrow="Process · silent holes caught before they became results",
        title="What the health table caught on the multi-model run",
        subtitle=(
            "A reply that arrives but cannot be used is not a transport error, so it is invisible unless something "
            "counts it. Three such holes turned up on the 12 Oct run; two were bugs in this repository."
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
        fig_jev_vs_people(sdf, "decisions", "neutral"),
        fig_jev_vs_people(sdf, "decisions", "typical_human"),
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
