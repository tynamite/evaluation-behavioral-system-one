"""Figures.

Form follows the question, which here is almost always *comparison against a
reference* or *change between two conditions*. Those are dot-and-whisker,
gap-from-benchmark and dumbbell forms — not grouped bars, which bury a
two-point comparison inside four bars and a legend.

One hard rule throughout: **a single axis carries a single scale.** Measures on
a 0-1 probability scale never share a panel with counts, percentages or
0-100 guesses, because putting them together invents comparisons that do not
exist.

Palette is the validated three-slot categorical set, assigned by entity —
Jev, the autoregressive baseline, the human benchmark — never by rank. The
aqua slot sits below 3:1 contrast on a light surface, so it always carries a
legend entry and a marker shape of its own, and `results/tables/statistics.csv`
is the table view of every number plotted.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Literal

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.lines import Line2D

from .analysis import compute_stats, distributions, load_records, order_effects
from .benchmarks import BENCHMARKS

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
INK_3 = "#8a8983"
GRID = "#e3e2de"
JEV = "#2a78d6"
BASE = "#eb6834"
HUMAN = "#1baf7a"

PERSONA_LABEL = {
    "neutral": "Neutral",
    "typical_human": "As typical human",
    "rational_agent": "As rational agent",
    "antisocial": "Antisocial persona",
}

# Two-line forms for use as x-axis ticks, where the long labels collide.
PERSONA_TICK = {
    "neutral": "Neutral",
    "typical_human": "As typical\nhuman",
    "rational_agent": "As rational\nagent",
    "antisocial": "Antisocial\npersona",
}

# Measures that genuinely share a 0-1 probability scale, so they may share an axis.
PROBABILITY_MEASURES: list[tuple[str, str, str, str]] = [
    ("crt", "proportion_correct", "crt_proportion_correct", "Cognitive reflection: correct"),
    ("dictator", "mean_share", "dictator_mean_share", "Dictator: share given"),
    ("ultimatum_proposer", "mean_share", "ultimatum_mean_offer", "Ultimatum: offer share"),
    (
        "ultimatum_responder",
        "prob_reject_low_offer",
        "ultimatum_rejection_low_offer",
        "Ultimatum: reject a low offer",
    ),
    ("trust_sender", "mean_share", "trust_sender_share", "Trust: share sent"),
    ("trust_trustee", "return_share_sent_5", "trust_return_share", "Trust: share returned"),
    ("public_goods", "mean_share", "pgg_round1_share", "Public goods: contribution"),
    (
        "prisoners_dilemma",
        "cooperation_one_shot",
        "pd_cooperation_oneshot",
        "Prisoner's dilemma: cooperate",
    ),
    ("framing", "prob_certain_gain_frame", "framing_gain_certain", "Framing: certain (gain)"),
    ("framing", "prob_certain_loss_frame", "framing_loss_certain", "Framing: certain (loss)"),
    ("allais", "prob_certain_pair1", "allais_p1_certain", "Allais: certainty effect"),
    (
        "conjunction",
        "prob_fallacy_forced_choice",
        "conjunction_fallacy_rate",
        "Conjunction fallacy",
    ),
    ("base_rate", "prob_correct_band", "base_rate_correct_band", "Base rate: correct"),
    ("sunk_cost", "prob_continue", "sunk_cost_continue", "Sunk cost: continue"),
]

GAME_MEASURES: list[tuple[str, str, str]] = [
    ("dictator", "mean_share", "Dictator giving"),
    ("ultimatum_proposer", "mean_share", "Ultimatum offer"),
    ("trust_sender", "mean_share", "Trust sent"),
    ("trust_trustee", "return_share_sent_5", "Trust returned"),
    ("public_goods", "mean_share", "Public goods"),
    ("prisoners_dilemma", "cooperation_one_shot", "PD cooperate"),
    ("ultimatum_responder", "prob_reject_low_offer", "Reject low offer"),
]


def _grid(ax: Axes, axis: Literal["both", "x", "y"] = "x") -> None:
    ax.set_facecolor(SURFACE)
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.tick_params(colors=INK_2, labelsize=9, length=0)
    ax.grid(axis=axis, color=GRID, linewidth=0.8, linestyle="-")
    ax.set_axisbelow(True)


def _titles(fig: Figure, title: str, subtitle: str, y: float = 0.98) -> None:
    fig.text(0.0, y, title, color=INK, fontsize=14, fontweight="bold", ha="left", va="top")
    fig.text(0.0, y - 0.055, subtitle, color=INK_2, fontsize=9.5, ha="left", va="top")


def _lookup(sdf: pd.DataFrame, inst: str, stat: str, persona: str, arm: str) -> float | None:
    sel = sdf[
        (sdf.instrument == inst)
        & (sdf.statistic == stat)
        & (sdf.persona == persona)
        & (sdf.arm == arm)
    ]
    if not len(sel):
        return None
    v = float(sel.iloc[0]["value"])
    return v if np.isfinite(v) else None


# ---------------------------------------------------------------------------


def fig_vs_human(sdf: pd.DataFrame, out: Path) -> Path:
    """Headline: each measure as a row, model and human on one probability axis.

    Rows are sorted by the size of the Jev-to-human gap, so the reader's eye
    lands on the largest divergences first and the connector length *is* the
    effect size.
    """
    rows = []
    for inst, stat, bench, label in PROBABILITY_MEASURES:
        jev = _lookup(sdf, inst, stat, "neutral", "jev")
        base = _lookup(sdf, inst, stat, "neutral", "baseline")
        human = BENCHMARKS[bench].value
        if jev is None:
            continue
        rows.append((label, jev, base, human, abs(jev - human)))
    rows.sort(key=lambda r: r[4])

    y = np.arange(len(rows))
    fig, ax = plt.subplots(figsize=(10.5, 0.46 * len(rows) + 2.4), dpi=170)
    fig.patch.set_facecolor(SURFACE)

    for i, (_, jev, _b, human, _g) in enumerate(rows):
        ax.plot([human, jev], [i, i], color=GRID, linewidth=2.4, zorder=1, solid_capstyle="round")

    humans = [r[3] for r in rows]
    jevs = [r[1] for r in rows]
    bases = [r[2] if r[2] is not None else np.nan for r in rows]

    ax.plot(
        humans,
        y,
        "D",
        markersize=8,
        color=HUMAN,
        markeredgecolor=SURFACE,
        markeredgewidth=2,
        zorder=3,
        linestyle="none",
        label="Humans (published)",
    )
    ax.plot(
        bases,
        y,
        "o",
        markersize=7,
        color=BASE,
        markeredgecolor=SURFACE,
        markeredgewidth=2,
        zorder=3,
        linestyle="none",
        label="Baseline LLM",
    )
    ax.plot(
        jevs,
        y,
        "o",
        markersize=9,
        color=JEV,
        markeredgecolor=SURFACE,
        markeredgewidth=2,
        zorder=4,
        linestyle="none",
        label="Jev",
    )

    # A numeric effect-size column on the right, as in a forest plot: every row
    # carries its gap without a single label colliding with a mark.
    for i, (_label, jev, _b, human, _g) in enumerate(rows):
        ax.text(
            1.09,
            i,
            f"{jev - human:+.2f}",
            va="center",
            ha="right",
            color=INK_2,
            fontsize=9,
            clip_on=False,
            fontweight="bold" if abs(jev - human) >= 0.25 else "normal",
        )
    ax.text(
        1.09,
        1.012,
        "gap",
        transform=ax.get_xaxis_transform(),
        va="bottom",
        ha="right",
        color=INK_3,
        fontsize=8.5,
        clip_on=False,
        fontweight="bold",
    )

    ax.set_yticks(y, [r[0] for r in rows], fontsize=9.5)
    ax.set_xlim(-0.03, 1.03)
    ax.set_xticks(np.arange(0, 1.01, 0.25))
    ax.set_xlabel("probability / rate", color=INK_2, fontsize=9.5)
    _grid(ax, "x")
    ax.legend(
        frameon=False,
        fontsize=9.5,
        labelcolor=INK_2,
        loc="lower left",
        bbox_to_anchor=(0.0, 1.005),
        ncols=3,
        handletextpad=0.4,
        columnspacing=1.8,
    )
    _titles(
        fig,
        "Jev against human behaviour, measure by measure",
        "Neutral framing. Bar length between marks is the gap. Human values are published "
        "reference points, not a matched control group.",
    )
    fig.subplots_adjust(top=0.86)
    path = out / "fig1_vs_human.png"
    fig.savefig(path, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)
    return path


def fig_gap(sdf: pd.DataFrame, out: Path) -> Path:
    """Deviation from the human benchmark, centred on zero.

    Diverging by polarity: one warm and one cool pole either side of a neutral
    zero rule, so 'more than humans' and 'less than humans' read as opposites
    at a glance.
    """
    rows = []
    for inst, stat, bench, label in PROBABILITY_MEASURES:
        jev = _lookup(sdf, inst, stat, "neutral", "jev")
        if jev is None:
            continue
        rows.append((label, jev - BENCHMARKS[bench].value))
    rows.sort(key=lambda r: r[1])

    y = np.arange(len(rows))
    vals = [r[1] for r in rows]
    colours = [BASE if v > 0 else JEV for v in vals]

    fig, ax = plt.subplots(figsize=(10.0, 0.46 * len(rows) + 2.4), dpi=170)
    fig.patch.set_facecolor(SURFACE)
    for i, (v, c) in enumerate(zip(vals, colours, strict=True)):
        ax.plot([0, v], [i, i], color=c, linewidth=2.2, solid_capstyle="round", zorder=2)
    for i, (v, c) in enumerate(zip(vals, colours, strict=True)):
        ax.plot(
            [v],
            [i],
            "o",
            markersize=8,
            color=c,
            markeredgecolor=SURFACE,
            markeredgewidth=2,
            zorder=3,
        )
        ax.text(
            v + (0.02 if v >= 0 else -0.02),
            i,
            f"{v:+.2f}",
            va="center",
            ha="left" if v >= 0 else "right",
            color=INK_2,
            fontsize=8.5,
        )

    ax.axvline(0, color=INK_3, linewidth=1.4, zorder=1)
    ax.set_yticks(y, [r[0] for r in rows], fontsize=9.5)
    lim = max(abs(min(vals)), abs(max(vals))) * 1.28
    ax.set_xlim(-lim, lim)
    ax.set_xlabel("Jev minus human rate", color=INK_2, fontsize=9.5)
    _grid(ax, "x")

    handles = [
        Line2D(
            [],
            [],
            color=BASE,
            marker="o",
            linestyle="-",
            linewidth=2.2,
            markersize=8,
            markeredgecolor=SURFACE,
            markeredgewidth=2,
            label="Does it MORE than humans",
        ),
        Line2D(
            [],
            [],
            color=JEV,
            marker="o",
            linestyle="-",
            linewidth=2.2,
            markersize=8,
            markeredgecolor=SURFACE,
            markeredgewidth=2,
            label="Does it LESS than humans",
        ),
    ]
    ax.legend(
        handles=handles,
        frameon=False,
        fontsize=9.5,
        labelcolor=INK_2,
        loc="lower left",
        bbox_to_anchor=(0.0, 1.005),
        ncols=2,
        handletextpad=0.4,
        columnspacing=1.8,
    )
    _titles(
        fig,
        "Which human biases does Jev reproduce?",
        "Distance from zero is how far the model departs from the published human rate.",
    )
    fig.subplots_adjust(top=0.86)
    path = out / "fig2_gap_from_human.png"
    fig.savefig(path, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)
    return path


def fig_persona(sdf: pd.DataFrame, out: Path) -> Path:
    """Dumbbells: what one line of persona text does to self-report and to money."""
    fig, axes = plt.subplots(
        1, 2, figsize=(13.6, 5.0), dpi=170, gridspec_kw={"width_ratios": [1, 1.1], "wspace": 0.52}
    )
    fig.patch.set_facecolor(SURFACE)

    # -- manipulation check -------------------------------------------
    ax = axes[0]
    traits = ["machiavellianism", "psychopathy", "narcissism", "overall"]
    labels = ["Machiavellianism", "Psychopathy", "Narcissism", "Overall"]
    y = np.arange(len(traits))
    neu = [_lookup(sdf, "dirty_dozen", t, "neutral", "jev") for t in traits]
    anti = [_lookup(sdf, "dirty_dozen", t, "antisocial", "jev") for t in traits]
    for i, (a, b) in enumerate(zip(neu, anti, strict=True)):
        if a is None or b is None:
            continue
        ax.annotate(
            "",
            xy=(b, i),
            xytext=(a, i),
            arrowprops={
                "arrowstyle": "-|>",
                "color": INK_3,
                "linewidth": 1.8,
                "shrinkA": 6,
                "shrinkB": 6,
            },
        )
    ax.plot(
        neu,
        y,
        "o",
        markersize=9,
        color=JEV,
        markeredgecolor=SURFACE,
        markeredgewidth=2,
        linestyle="none",
        label="Neutral",
        zorder=3,
    )
    ax.plot(
        anti,
        y,
        "o",
        markersize=9,
        color=BASE,
        markeredgecolor=SURFACE,
        markeredgewidth=2,
        linestyle="none",
        label="Antisocial persona",
        zorder=3,
    )
    for i, (a, b) in enumerate(zip(neu, anti, strict=True)):
        if a is not None and b is not None:
            ax.text(
                10.2,
                i,
                f"{b - a:+.1f}",
                va="center",
                ha="right",
                color=INK_2,
                fontsize=9,
                fontweight="bold",
                clip_on=False,
            )
    ax.text(
        10.2,
        1.012,
        "shift",
        transform=ax.get_xaxis_transform(),
        va="bottom",
        ha="right",
        color=INK_3,
        fontsize=8.5,
        fontweight="bold",
        clip_on=False,
    )
    ax.set_yticks(y, labels, fontsize=9.5)
    ax.set_xlim(1, 9.5)
    ax.set_xlabel("mean agreement (1-9 scale)", color=INK_2, fontsize=9.5)
    ax.set_title(
        "Manipulation check: did the persona land?",
        color=INK,
        fontsize=11,
        fontweight="bold",
        loc="left",
        pad=12,
    )
    _grid(ax, "x")
    handles, labels = ax.get_legend_handles_labels()

    # -- consequential spillover --------------------------------------
    ax = axes[1]
    y = np.arange(len(GAME_MEASURES))
    neu = [_lookup(sdf, i, s, "neutral", "jev") for i, s, _ in GAME_MEASURES]
    anti = [_lookup(sdf, i, s, "antisocial", "jev") for i, s, _ in GAME_MEASURES]
    for i, (a, b) in enumerate(zip(neu, anti, strict=True)):
        if a is None or b is None:
            continue
        ax.annotate(
            "",
            xy=(b, i),
            xytext=(a, i),
            arrowprops={
                "arrowstyle": "-|>",
                "color": INK_3,
                "linewidth": 1.8,
                "shrinkA": 6,
                "shrinkB": 6,
            },
        )
    ax.plot(
        neu,
        y,
        "o",
        markersize=9,
        color=JEV,
        markeredgecolor=SURFACE,
        markeredgewidth=2,
        linestyle="none",
        label="Neutral",
        zorder=3,
    )
    ax.plot(
        anti,
        y,
        "o",
        markersize=9,
        color=BASE,
        markeredgecolor=SURFACE,
        markeredgewidth=2,
        linestyle="none",
        label="Antisocial persona",
        zorder=3,
    )
    for i, (a, b) in enumerate(zip(neu, anti, strict=True)):
        if a is not None and b is not None:
            ax.text(
                1.20,
                i,
                f"{b - a:+.2f}",
                va="center",
                ha="right",
                color=INK_2,
                fontsize=9,
                fontweight="bold",
                clip_on=False,
            )
    ax.text(
        1.20,
        1.012,
        "shift",
        transform=ax.get_xaxis_transform(),
        va="bottom",
        ha="right",
        color=INK_3,
        fontsize=8.5,
        fontweight="bold",
        clip_on=False,
    )
    ax.set_yticks(y, [m[2] for m in GAME_MEASURES], fontsize=9.5)
    ax.set_xlim(-0.03, 1.03)
    ax.set_xlabel("share given / cooperation rate", color=INK_2, fontsize=9.5)
    ax.set_title(
        "Spillover: does it change the money?",
        color=INK,
        fontsize=11,
        fontweight="bold",
        loc="left",
        pad=12,
    )
    _grid(ax, "x")

    _titles(
        fig,
        "Persona steerability across self-report and economic choices",
        "Arrow length is the effect of one sentence of persona text. Left: does the persona "
        "take hold. Right: does it reach consequential choices.",
        y=1.0,
    )
    fig.legend(
        handles,
        labels,
        frameon=False,
        fontsize=9.5,
        labelcolor=INK_2,
        loc="upper right",
        bbox_to_anchor=(1.0, 1.0),
        ncols=2,
        handletextpad=0.4,
        columnspacing=1.6,
    )
    fig.subplots_adjust(top=0.76, wspace=0.42)
    path = out / "fig3_persona.png"
    fig.savefig(path, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)
    return path


def fig_reflection(sdf: pd.DataFrame, out: Path) -> Path:
    """Slope chart across personas, plus reasoning accuracy against depth."""
    fig, axes = plt.subplots(1, 2, figsize=(12.8, 4.8), dpi=170)
    fig.patch.set_facecolor(SURFACE)
    personas = ["neutral", "typical_human", "rational_agent", "antisocial"]
    xs = np.arange(len(personas))

    ax = axes[0]
    series = [
        ("proportion_correct", JEV, "Jev — correct answer"),
        ("probability_mass_on_lure", BASE, "Jev — intuitive lure"),
    ]
    tracks: dict[str, list[float | None]] = {}
    for stat, colour, label in series:
        vals = [_lookup(sdf, "crt", stat, p, "jev") for p in personas]
        tracks[stat] = vals
        ax.plot(
            xs,
            vals,
            marker="o",
            markersize=9,
            linewidth=2.2,
            color=colour,
            markeredgecolor=SURFACE,
            markeredgewidth=2,
            label=label,
        )

    # Endpoint labels are pushed apart by which series is on top at that end,
    # so two lines that happen to meet there cannot print over each other.
    correct, lure = tracks["proportion_correct"], tracks["probability_mass_on_lure"]
    for idx, ha, dx in ((0, "right", -9), (len(personas) - 1, "left", 9)):
        above_is_correct = (correct[idx] or 0.0) >= (lure[idx] or 0.0)
        for vals, colour, on_top in (
            (correct, JEV, above_is_correct),
            (lure, BASE, not above_is_correct),
        ):
            v = vals[idx]
            if v is None:
                continue
            ax.annotate(
                f"{v:.2f}",
                xy=(idx, v),
                xytext=(dx, 9 if on_top else -9),
                textcoords="offset points",
                ha=ha,
                va="center",
                color=colour,
                fontsize=9,
                fontweight="bold",
            )

    hb = BENCHMARKS["crt_proportion_correct"].value
    ax.axhline(hb, color=HUMAN, linewidth=2)
    ax.annotate(
        f"humans {hb:.2f}",
        xy=(0, hb),
        xytext=(0, 6),
        textcoords="offset points",
        color=HUMAN,
        fontsize=9,
        fontweight="bold",
    )
    ax.set_xticks(xs, [PERSONA_TICK[p] for p in personas], fontsize=9)
    ax.set_xlim(-0.55, len(personas) - 0.45)
    ax.set_ylim(-0.14, 1.16)
    ax.set_yticks(np.arange(0, 1.01, 0.25))
    ax.set_ylabel("probability mass", color=INK_2, fontsize=9.5)
    ax.set_title(
        "Cognitive reflection across personas",
        color=INK,
        fontsize=11,
        fontweight="bold",
        loc="left",
        pad=34,
    )
    _grid(ax, "y")
    ax.legend(
        frameon=False,
        fontsize=9,
        labelcolor=INK_2,
        loc="lower left",
        bbox_to_anchor=(0.0, 1.005),
        ncols=2,
        handletextpad=0.4,
        columnspacing=1.4,
    )

    ax = axes[1]
    steps = sorted(
        int(s.rsplit("_", 1)[1])
        for s in sdf[sdf.statistic.str.startswith("accuracy_steps_")].statistic.unique()
    )
    arm_tracks: dict[str, list[float | None]] = {}
    for arm, colour, label in (("jev", JEV, "Jev"), ("baseline", BASE, "Baseline LLM")):
        vals = [
            _lookup(sdf, "fluid_reasoning", f"accuracy_steps_{s}", "neutral", arm) for s in steps
        ]
        if all(v is None for v in vals):
            continue
        arm_tracks[arm] = vals
        ax.plot(
            steps,
            vals,
            marker="o",
            markersize=9,
            linewidth=2.2,
            color=colour,
            markeredgecolor=SURFACE,
            markeredgewidth=2,
            label=label,
        )

    # Separated by which arm sits on top at that end, so two arms that agree
    # there — both at 1.00, say — cannot print on top of each other.
    for idx, ha, dx in ((0, "right", -9), (len(steps) - 1, "left", 9)):
        jev_v = (arm_tracks.get("jev") or [None] * len(steps))[idx]
        base_v = (arm_tracks.get("baseline") or [None] * len(steps))[idx]
        jev_on_top = (jev_v or 0.0) >= (base_v or 0.0)
        for arm, colour, on_top in (
            ("jev", JEV, jev_on_top),
            ("baseline", BASE, not jev_on_top),
        ):
            track = arm_tracks.get(arm)
            if track is None or track[idx] is None:
                continue
            ax.annotate(
                f"{track[idx]:.2f}",
                xy=(steps[idx], track[idx]),
                xytext=(dx, 9 if on_top else -9),
                textcoords="offset points",
                ha=ha,
                va="center",
                color=colour,
                fontsize=9,
                fontweight="bold",
            )
    ax.set_xticks(steps)
    ax.set_xlim(steps[0] - 0.55, steps[-1] + 0.55)
    ax.set_ylim(-0.14, 1.16)
    ax.set_yticks(np.arange(0, 1.01, 0.25))
    ax.set_xlabel("chained inferences the item requires", color=INK_2, fontsize=9.5)
    ax.set_ylabel("accuracy", color=INK_2, fontsize=9.5)
    ax.set_title(
        "Reasoning accuracy against depth",
        color=INK,
        fontsize=11,
        fontweight="bold",
        loc="left",
        pad=34,
    )
    _grid(ax, "y")
    ax.legend(
        frameon=False,
        fontsize=9,
        labelcolor=INK_2,
        loc="lower left",
        bbox_to_anchor=(0.0, 1.005),
        ncols=2,
        handletextpad=0.4,
        columnspacing=1.4,
    )

    _titles(
        fig,
        "Deliberation: the System 1 question, directly",
        "Left: can the model be steered onto the human error. "
        "Right: accuracy as the inference chain lengthens (not an IQ score).",
        y=1.0,
    )
    fig.subplots_adjust(top=0.72, wspace=0.34)
    path = out / "fig4_reflection.png"
    fig.savefig(path, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)
    return path


def fig_distributions(df: pd.DataFrame, out: Path) -> Path:
    """Whole answer distributions — the thing a single call buys you."""
    dists = distributions(df)
    fig, axes = plt.subplots(1, 2, figsize=(12.6, 4.6), dpi=170)
    fig.patch.set_facecolor(SURFACE)

    ax = axes[0]
    d = dists.get(("dictator_allocation", "neutral", "jev"), {})
    xs = list(range(11))
    ys = [d.get(f"${v}", 0.0) for v in xs]
    human_x, human_y = (
        [0, 5],
        [BENCHMARKS["dictator_share_zero"].value, BENCHMARKS["dictator_share_half"].value],
    )
    top = max([*ys, *human_y, 0.1]) * 1.30
    ax.bar(xs, ys, 0.70, color=JEV, label="Jev (neutral)")
    ax.plot(
        human_x,
        human_y,
        "D",
        markersize=9,
        color=HUMAN,
        markeredgecolor=SURFACE,
        markeredgewidth=2,
        linestyle="none",
        label="Human rate (Engel 2011)",
        zorder=4,
    )
    peak = int(np.argmax(ys))
    ax.annotate(
        f"{ys[peak]:.2f}",
        xy=(peak, ys[peak]),
        xytext=(0, 6),
        textcoords="offset points",
        ha="center",
        color=JEV,
        fontsize=9,
        fontweight="bold",
    )
    ax.set_xticks(xs, [f"${v}" for v in xs], fontsize=9)
    ax.set_ylim(0, top)
    ax.set_xlabel("amount given of $10", color=INK_2, fontsize=9.5)
    ax.set_ylabel("probability", color=INK_2, fontsize=9.5)
    ax.set_title(
        "Dictator game: full allocation distribution",
        color=INK,
        fontsize=11,
        fontweight="bold",
        loc="left",
        pad=12,
    )
    _grid(ax, "y")
    ax.legend(frameon=False, fontsize=9, labelcolor=INK_2, loc="upper right")

    # Binned, because 101 one-unit spikes is noise rather than a distribution.
    ax = axes[1]
    d = dists.get(("beauty_contest_2_3", "neutral", "jev"), {})
    edges = np.arange(0, 105, 5)
    binned = [sum(d.get(str(v), 0.0) for v in range(lo, min(lo + 5, 101))) for lo in edges[:-1]]
    centres = edges[:-1] + 2.5
    ax.bar(centres, binned, 4.3, color=JEV, label="Jev (neutral)")
    hb = BENCHMARKS["beauty_contest_mean"].value
    ax.plot(
        [hb],
        [max(binned) * 1.06],
        "D",
        markersize=9,
        color=HUMAN,
        markeredgecolor=SURFACE,
        markeredgewidth=2,
        linestyle="none",
        label=f"Human mean ({hb:.0f})",
        zorder=4,
    )
    for v, lab in ((0, "equilibrium"), (33, "one step of reasoning")):
        ax.axvline(v, color=INK_3, linewidth=1.2, zorder=1)
        ax.annotate(
            lab,
            xy=(v, max(binned) * 1.16),
            xytext=(4, 0),
            textcoords="offset points",
            color=INK_2,
            fontsize=8.5,
            va="center",
        )
    ax.set_xlim(-3, 103)
    ax.set_ylim(0, max(binned) * 1.32)
    ax.set_xlabel("number chosen, binned by 5", color=INK_2, fontsize=9.5)
    ax.set_ylabel("probability", color=INK_2, fontsize=9.5)
    ax.set_title(
        "p-beauty contest: depth of strategic reasoning",
        color=INK,
        fontsize=11,
        fontweight="bold",
        loc="left",
        pad=12,
    )
    _grid(ax, "y")
    ax.legend(frameon=False, fontsize=9, labelcolor=INK_2, loc="upper right")

    _titles(
        fig,
        "What a single call returns: the whole distribution",
        "A text model needs N resamples to estimate these, mixing decoder noise into "
        "the estimate. Jev reports them directly.",
        y=1.0,
    )
    fig.subplots_adjust(top=0.80)
    path = out / "fig5_distributions.png"
    fig.savefig(path, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)
    return path


def fig_order_effects(odf: pd.DataFrame, out: Path) -> Path:
    """H6: humans move a lot when options are reordered. Does this model?"""
    fig, ax = plt.subplots(figsize=(9.2, 4.2), dpi=170)
    fig.patch.set_facecolor(SURFACE)
    vals = odf["mean_tv_distance"].dropna().to_numpy()
    ax.hist(vals, bins=32, color=JEV, edgecolor=SURFACE, linewidth=0.8)
    m = float(np.mean(vals)) if vals.size else float("nan")
    ax.axvline(m, color=BASE, linewidth=2.2, zorder=3)
    ax.annotate(
        f"mean {m:.3f}",
        xy=(m, ax.get_ylim()[1] * 0.92),
        xytext=(8, 0),
        textcoords="offset points",
        color=BASE,
        fontsize=9.5,
        fontweight="bold",
    )
    ax.set_xlabel(
        "total-variation distance between replicates with different option orders",
        color=INK_2,
        fontsize=9.5,
    )
    ax.set_ylabel("probes", color=INK_2, fontsize=9.5)
    _grid(ax, "y")
    _titles(
        fig,
        "Option-order sensitivity",
        "0 means reordering the options changed nothing. Humans show large order "
        "effects on forced-choice items.",
        y=1.0,
    )
    fig.subplots_adjust(top=0.80)
    path = out / "fig6_order_effects.png"
    fig.savefig(path, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)
    return path


def build_figures(run_path: Path, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    df = load_records(run_path)
    sdf = pd.DataFrame([asdict(s) for s in compute_stats(df)])
    odf = order_effects(df)
    paths = [
        fig_vs_human(sdf, out_dir),
        fig_gap(sdf, out_dir),
        fig_persona(sdf, out_dir),
        fig_reflection(sdf, out_dir),
        fig_distributions(df, out_dir),
        fig_order_effects(odf, out_dir),
    ]
    for p in paths:
        print(f"wrote {p}")
    return paths
