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
from typing import Any, Literal

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
        "Arrow length is the effect of a short persona instruction. Left: does the persona "
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
    maybe_paths: list[Path | None] = [
        fig_vs_human(sdf, out_dir),
        fig_gap(sdf, out_dir),
        fig_persona(sdf, out_dir),
        fig_reflection(sdf, out_dir),
        fig_distributions(df, out_dir),
        fig_order_effects(odf, out_dir),
        fig_human_fidelity(sdf, out_dir),
        fig_followup_elicitations(sdf, out_dir),
        fig_followup_currency(sdf, out_dir),
    ]
    paths = [p for p in maybe_paths if p is not None]
    skipped = len(maybe_paths) - len(paths)
    for p in paths:
        print(f"wrote {p}")
    if skipped:
        print(f"skipped {skipped} figure(s) with no data for their instruments")
    return paths


def _label_extremes(fig: Any, extremes: list[tuple[Any, list[tuple[str, float, float]]]]) -> None:
    """Label the largest misses and the best match in each scatter panel.

    Each label points back into its panel, so it cannot run onto the next
    panel's tick labels. Two extremes can sit close together, so a label that
    would cover one already placed tries the other side of its point, and is
    left off rather than printed over another.
    """
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    for ax, picks in extremes:
        placed: list[Any] = []
        for rank, (label, h, m) in enumerate(picks):
            to_left = h > 0.5
            dy = -13 if m > 0.90 else (9 if rank == 2 else 5)
            for oy in (dy, -dy - 4):
                note = ax.annotate(
                    label,
                    xy=(h, m),
                    xytext=(-9 if to_left else 9, oy),
                    textcoords="offset points",
                    ha="right" if to_left else "left",
                    color=INK_2,
                    fontsize=8,
                )
                box = note.get_window_extent(renderer).padded(2)
                if not any(box.overlaps(other) for other in placed):
                    placed.append(box)
                    break
                note.remove()


def fig_human_fidelity(sdf: pd.DataFrame, out: Path) -> Path:
    """How closely does each condition reproduce the human values?

    The left panels are the canonical form for this question: the published
    human value on x, the model's on y, and a 45-degree line. A point on the
    line is a measure the condition reproduces exactly; distance from the line
    is the error, and its direction says whether the model is more or less
    extreme than people.
    """
    from .analysis import human_fidelity

    fid, points = human_fidelity(sdf, PROBABILITY_MEASURES)
    by_key = {(f.arm, f.persona): f for f in fid}

    fig, axes = plt.subplots(
        1,
        3,
        figsize=(15.0, 5.0),
        dpi=170,
        gridspec_kw={"width_ratios": [1, 1, 1.05], "wspace": 0.38},
    )
    fig.patch.set_facecolor(SURFACE)
    extremes: list[tuple[Any, list[tuple[str, float, float]]]] = []

    for ax, persona, title in (
        (axes[0], "neutral", "Answering neutrally"),
        (axes[1], "typical_human", "Asked to answer as a typical human"),
    ):
        pairs = points.get(("jev", persona), [])
        f = by_key.get(("jev", persona))
        ax.plot([0, 1], [0, 1], color=INK_3, linewidth=1.2, zorder=1)
        hs = [p[1] for p in pairs]
        ms = [p[2] for p in pairs]
        for h, m in zip(hs, ms, strict=True):
            ax.plot([h, h], [h, m], color=GRID, linewidth=1.4, zorder=2)
        ax.plot(
            hs,
            ms,
            "o",
            markersize=9,
            color=JEV,
            markeredgecolor=SURFACE,
            markeredgewidth=2,
            linestyle="none",
            zorder=3,
        )
        # Label only the extremes: the three worst misses and the best match.
        ranked = sorted(pairs, key=lambda p: -abs(p[2] - p[1]))
        # Placed once the layout is final (below), so overlaps are measured where
        # the labels will actually be drawn.
        extremes.append((ax, [*ranked[:2], ranked[-1]] if ranked else []))
        if f is not None:
            ax.text(
                0.0,
                1.012,
                f"mean error {f.mae:.2f}   ·   correlation r = {f.r:+.2f}",
                transform=ax.transAxes,
                va="bottom",
                ha="left",
                color=INK_2,
                fontsize=9,
                fontweight="bold",
            )
        ax.set_xlim(-0.04, 1.08)
        ax.set_ylim(-0.04, 1.08)
        ax.set_xticks(np.arange(0, 1.01, 0.25))
        ax.set_yticks(np.arange(0, 1.01, 0.25))
        ax.set_xlabel("published human rate", color=INK_2, fontsize=9.5)
        ax.set_ylabel("Jev", color=INK_2, fontsize=9.5)
        ax.set_title(title, color=INK, fontsize=11, fontweight="bold", loc="left", pad=30)
        _grid(ax, "both")

    # Mean error by condition, both arms.
    ax = axes[2]
    order = ["typical_human", "neutral", "antisocial", "rational_agent"]
    y = np.arange(len(order))
    for arm, colour, label, off in (
        ("jev", JEV, "Jev", 0.16),
        ("baseline", BASE, "Baseline LLM", -0.16),
    ):
        vals = [by_key[(arm, p)].mae if (arm, p) in by_key else np.nan for p in order]
        ax.plot(
            vals,
            y + off,
            "o",
            markersize=9,
            color=colour,
            markeredgecolor=SURFACE,
            markeredgewidth=2,
            linestyle="none",
            label=label,
            zorder=3,
        )
        for i, v in enumerate(vals):
            if np.isfinite(v):
                ax.plot([0, v], [i + off, i + off], color=colour, linewidth=2, zorder=2)
                ax.text(v + 0.012, i + off, f"{v:.2f}", va="center", color=INK_2, fontsize=8.5)
    ax.set_yticks(y, [PERSONA_LABEL[p] for p in order], fontsize=9.5)
    ax.set_xlim(0, 0.62)
    ax.invert_yaxis()
    ax.set_xlabel("mean absolute error vs the human rate", color=INK_2, fontsize=9.5)
    ax.set_title(
        "Distance from human behaviour",
        color=INK,
        fontsize=11,
        fontweight="bold",
        loc="left",
        pad=34,
    )
    _grid(ax, "x")
    ax.legend(
        frameon=False,
        fontsize=9,
        labelcolor=INK_2,
        loc="lower left",
        bbox_to_anchor=(0.0, 1.005),
        ncols=2,
        handletextpad=0.4,
        columnspacing=1.6,
    )

    _titles(
        fig,
        "Does the model know how people answer?",
        "Fourteen measures with a published human value, all on a 0-1 scale. The diagonal is an "
        "exact match. Human values are reference points from unrelated samples, not a "
        "matched control group.",
        y=1.0,
    )
    fig.subplots_adjust(top=0.78)
    _label_extremes(fig, extremes)
    path = out / "fig7_human_fidelity.png"
    fig.savefig(path, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)
    return path


# -- follow-up battery ---------------------------------------------------
# See FOLLOWUP_PREREGISTRATION.md. These items have no data in the run
# committed alongside the main battery — that run predates them — so both
# functions return None rather than an empty figure when nothing is there.

FOLLOWUP_PROPORTION_ROWS = [
    (
        "shafir_award_extreme",
        "choosing_rejecting",
        "prob_award_extreme",
        "Award custody to extreme parent",
    ),
    (
        "shafir_deny_extreme",
        "choosing_rejecting",
        "prob_deny_extreme",
        "Deny custody to extreme parent",
    ),
    ("norenzayan_rule_based", "categorization", "prob_rule_based", "Choose the rule-based group"),
    (
        "knobe_harm_intentional",
        "knobe",
        "prob_harm_intentional",
        "Intentional: harmful side effect",
    ),
    (
        "knobe_help_intentional",
        "knobe",
        "prob_help_intentional",
        "Intentional: helpful side effect",
    ),
    (
        "trolley_switch_permissible",
        "trolley",
        "prob_switch_permissible",
        "Permissible: divert by switch",
    ),
    (
        "trolley_push_permissible",
        "trolley",
        "prob_push_permissible",
        "Permissible: push off footbridge",
    ),
    (
        "false_consensus_wearer_predicts_wear",
        "false_consensus",
        "wearer_predicts_wear",
        "Wearers predict others also wear",
    ),
    (
        "false_consensus_nonwearer_predicts_wear",
        "false_consensus",
        "nonwearer_predicts_wear",
        "Non-wearers predict others wear",
    ),
]

FOLLOWUP_RATING_ROWS = [
    (
        "moral_typecasting_responsibility_man",
        "moral_typecasting",
        "responsibility_man",
        "Responsibility: high-agency actor",
    ),
    (
        "moral_typecasting_responsibility_baby",
        "moral_typecasting",
        "responsibility_baby",
        "Responsibility: low-agency actor",
    ),
    ("position_power_long_line", "position_power", "power_long_line", "Perceived power: long line"),
    (
        "position_power_short_line",
        "position_power",
        "power_short_line",
        "Perceived power: short line",
    ),
]

FOLLOWUP_PERCENT_ROWS = [
    ("incidental_anchor_p97", "incidental_anchors", "estimate_p97", 'Market-share estimate: "P97"'),
    ("incidental_anchor_p17", "incidental_anchors", "estimate_p17", 'Market-share estimate: "P17"'),
]


def _followup_points(
    sdf: pd.DataFrame, rows: list[tuple[str, str, str, str]]
) -> list[tuple[str, float | None, float | None, float | None, float]]:
    """(label, own, simulate, estimate, human) for each row, skipping rows with no data at all."""
    out: list[tuple[str, float | None, float | None, float | None, float]] = []
    for bench, inst, stat, label in rows:
        own = _lookup(sdf, inst, stat, "neutral", "jev")
        sim = _lookup(sdf, inst, stat, "typical_human", "jev")
        est = _lookup(sdf, f"{inst}_estimate", stat, "neutral", "jev")
        if own is None and sim is None and est is None:
            continue
        out.append((label, own, sim, est, BENCHMARKS[bench].value))
    return out


def _plot_elicitation_panel(
    ax: Axes,
    points: list[tuple[str, float | None, float | None, float | None, float]],
    total_rows: int,
) -> None:
    """own/simulate/estimate as same-colour, different-marker-shape points; human as an aqua
    diamond. No point-adjacent labels: with four markers per row they collide whenever two
    values sit close together, which is common here. The number that matters — how far the
    model's direct population estimate lands from the true value — goes in a fixed column
    on the right instead, the same fix used for the persona dumbbells in fig3.

    `total_rows` is the largest row count across all three panels, not this panel's own —
    the three panels share one figure height (set from the tallest panel), and without this
    a short panel's few rows autoscale to fill that whole height, spread out far more than
    the tallest panel's row spacing. Pinning every panel's y-limits to the same `total_rows`
    keeps one consistent row height across panels; a short panel just leaves blank space at
    the bottom instead of stretching.
    """
    y = np.arange(len(points))
    own_vals = [p[1] if p[1] is not None else np.nan for p in points]
    sim_vals = [p[2] if p[2] is not None else np.nan for p in points]
    est_vals = [p[3] if p[3] is not None else np.nan for p in points]
    humans = [p[4] for p in points]
    series: list[tuple[list[float], str, str]] = [
        (own_vals, "o", "Own answer (neutral)"),
        (sim_vals, "s", "Simulate (as typical human)"),
        (est_vals, "^", "Estimate (predict the population)"),
    ]
    for vals, marker, label in series:
        ax.plot(
            vals,
            y,
            marker,
            markersize=9,
            color=JEV,
            markeredgecolor=SURFACE,
            markeredgewidth=2,
            linestyle="none",
            label=label,
            zorder=3,
        )
    ax.plot(
        humans,
        y,
        "D",
        markersize=8,
        color=HUMAN,
        markeredgecolor=SURFACE,
        markeredgewidth=2,
        linestyle="none",
        label="Original study",
        zorder=4,
    )
    ax.set_yticks(y, [p[0] for p in points], fontsize=9)
    ax.set_ylim(-0.5, total_rows - 0.5)
    ax.invert_yaxis()
    _grid(ax, "x")

    # Fixed column: how far the "estimate" condition lands from the true value.
    for i, (est, human) in enumerate(zip(est_vals, humans, strict=True)):
        if not np.isfinite(est):
            continue
        ax.text(
            1.06,
            i,
            f"{est - human:+.1f}",
            transform=ax.get_yaxis_transform(),
            va="center",
            ha="left",
            color=INK_2,
            fontsize=8.5,
            clip_on=False,
            fontweight="bold"
            if abs(est - human) >= 0.25 * max(abs(h) for h in humans)
            else "normal",
        )
    # Anchored in pure axes-fraction coordinates (both x and y), not data-y, so
    # it sits just above *this panel's own* top edge regardless of how many
    # rows the panel has — mixing a data-y with an axes-x, as the per-row gap
    # labels above do, put this header at wildly different heights across the
    # three panels, since they have different row counts sharing one figure.
    ax.text(
        1.06,
        1.22,
        "est. gap",
        transform=ax.transAxes,
        va="bottom",
        ha="left",
        color=INK_3,
        fontsize=8,
        fontweight="bold",
        clip_on=False,
    )


def fig_followup_elicitations(sdf: pd.DataFrame, out: Path) -> Path | None:
    """Own vs. simulate vs. estimate against the original study's own number.

    Three panels, one per response scale, because a proportion, a 1-7 rating
    and a percentage estimate cannot share an axis. `estimate` predicts the
    population statistic itself rather than answering as a participant — see
    Amendment 1 in FOLLOWUP_PREREGISTRATION.md for why that is a different
    question from `simulate`, not a third point on the same one.
    """
    panels = [
        (FOLLOWUP_PROPORTION_ROWS, "Proportion choosing one option", (-0.04, 1.08)),
        (FOLLOWUP_RATING_ROWS, "Rating (1-7 scale)", (0.7, 7.3)),
        (FOLLOWUP_PERCENT_ROWS, "Estimated percentage", (-3, 103)),
    ]
    data = [(_followup_points(sdf, rows), title, xlim) for rows, title, xlim in panels]
    if all(not pts for pts, _, _ in data):
        return None

    widths = [max(len(pts), 1) for pts, _, _ in data]
    max_rows = max(widths)
    fig, axes = plt.subplots(
        1,
        3,
        figsize=(15.5, 1.1 * max_rows + 2.6),
        dpi=170,
        gridspec_kw={"width_ratios": [1, 1, 1], "wspace": 1.3},
    )
    fig.patch.set_facecolor(SURFACE)
    handles: list[Any] = []
    labels: list[str] = []
    for ax, (points, title, xlim) in zip(axes, data, strict=True):
        if not points:
            ax.set_visible(False)
            continue
        _plot_elicitation_panel(ax, points, max_rows)
        ax.set_xlim(*xlim)
        ax.set_title(title, color=INK, fontsize=10.5, fontweight="bold", loc="left", pad=10)
        if not handles:
            handles, labels = ax.get_legend_handles_labels()

    fig.legend(
        handles,
        labels,
        frameon=False,
        fontsize=9,
        labelcolor=INK_2,
        loc="upper left",
        bbox_to_anchor=(0.0, 1.0),
        ncols=4,
        handletextpad=0.4,
        columnspacing=1.4,
    )
    _titles(
        fig,
        "The follow-up battery: eight effects, sourced from ML2's protocol or the original papers",
        "Own answer, simulated-human answer, and a direct population estimate, against the "
        "original study's own number (N=64-207 per item — see FOLLOWUP_PREREGISTRATION.md).",
        y=1.14,
    )
    fig.subplots_adjust(top=0.72)
    path = out / "fig8_followup_elicitations.png"
    fig.savefig(path, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)
    return path


def fig_followup_currency(sdf: pd.DataFrame, out: Path) -> Path | None:
    """H3: does the model track the textbook anchoring gap, or the one ML2 actually found?

    Critcher & Gilovich's original anchoring gap was 6.2 points. Many Labs 2's
    own replication of that exact effect came back at d=0.04 — essentially
    gone. This is the single most decisive planned test in the follow-up
    study: if simulating or estimating "a typical participant" reproduces
    something close to 6.2 points, the model is reciting the textbook
    description of an effect that, on the best current evidence, no longer
    holds.
    """
    conditions = [
        ("own", "incidental_anchors", "neutral", "Own answer\n(neutral)"),
        ("sim", "incidental_anchors", "typical_human", "Simulate\n(as typical human)"),
        ("est", "incidental_anchors_estimate", "neutral", "Estimate\n(predict the population)"),
    ]
    gaps = [
        (_lookup(sdf, inst, "anchor_gap", persona, "jev"), label)
        for _, inst, persona, label in conditions
    ]
    if all(g is None for g, _ in gaps):
        return None

    fig, ax = plt.subplots(figsize=(8.6, 4.6), dpi=170)
    fig.patch.set_facecolor(SURFACE)

    original_gap = (
        BENCHMARKS["incidental_anchor_p97"].value - BENCHMARKS["incidental_anchor_p17"].value
    )
    ml2_gap = 0.0  # d=0.04 on ML2's own replication is not distinguishable from zero at this scale

    x = np.arange(len(gaps))
    vals = [g if g is not None else np.nan for g, _ in gaps]
    ax.bar(x, vals, 0.55, color=JEV, zorder=3)
    # Positive bars are labelled above their top, in the empty space toward the
    # reference lines. A negative bar's tip points toward the two-line x-tick
    # labels below it, and no fixed points-offset clears every tick label's
    # height reliably (checked: it doesn't) — so a negative bar's label goes
    # inside the bar instead, near its tip, in white rather than chasing the
    # collision with ever-larger offsets.
    for xi, v in zip(x, vals, strict=True):
        if not np.isfinite(v):
            continue
        if v >= 0:
            ax.annotate(
                f"{v:+.1f} pts",
                xy=(xi, v),
                xytext=(0, 6),
                textcoords="offset points",
                ha="center",
                color=JEV,
                fontsize=9,
                fontweight="bold",
            )
        else:
            ax.annotate(
                f"{v:+.1f} pts",
                xy=(xi, v),
                xytext=(0, 6),
                textcoords="offset points",
                ha="center",
                va="bottom",
                color=SURFACE,
                fontsize=9,
                fontweight="bold",
            )

    ax.axhline(original_gap, color=HUMAN, linewidth=2, linestyle="--", zorder=2)
    ax.annotate(
        f"original study: {original_gap:+.1f} pts",
        xy=(len(gaps) - 0.4, original_gap),
        xytext=(6, 4),
        textcoords="offset points",
        color=HUMAN,
        fontsize=9,
        fontweight="bold",
        annotation_clip=False,
    )
    ax.axhline(ml2_gap, color=INK_3, linewidth=2, linestyle=":", zorder=2)
    ax.annotate(
        "ML2's own replication: ~0",
        xy=(len(gaps) - 0.4, ml2_gap),
        xytext=(6, -12),
        textcoords="offset points",
        color=INK_3,
        fontsize=9,
        fontweight="bold",
        annotation_clip=False,
    )

    ax.set_xticks(x, [label for _, label in gaps], fontsize=9)
    ax.set_ylabel('estimated gap, "P97" minus "P17" (points)', color=INK_2, fontsize=9.5)
    _grid(ax, "y")
    fig.subplots_adjust(right=0.78)
    _titles(
        fig,
        "Does the model know the textbook anchoring effect, or the real one?",
        "Critcher & Gilovich's original gap was 6.2 points; Many Labs 2's own replication of "
        "this exact effect found d=0.04 — essentially nothing.",
        y=1.0,
    )
    fig.subplots_adjust(top=0.76, bottom=0.22)
    path = out / "fig9_followup_currency.png"
    fig.savefig(path, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)
    return path


def fig_model_comparison(fdf: pd.DataFrame, out: Path) -> Path | None:
    """Which models land closest to people, answering neutrally and as a typical human?

    One row per model, its mean distance from the published human values on
    the shared 0-1 measures. Colour is assigned by model *type* — System One or
    resampled chat — not by model, so the palette stays the validated
    three-slot set however many models are compared; the correlation with the
    human values is printed beside each point because a low error alone can
    come from sitting near the middle of everything.
    """
    panels = [
        (p, t)
        for p, t in (
            ("neutral", "Answering neutrally"),
            ("typical_human", "Asked to answer as a typical human"),
        )
        if len(fdf) and (fdf["persona"] == p).any()
    ]
    if not panels:
        return None

    n_models = int(fdf["model"].nunique())
    fig, axes = plt.subplots(
        1,
        len(panels),
        figsize=(7.2 * len(panels), 1.4 + 0.42 * n_models),
        dpi=170,
        gridspec_kw={"wspace": 0.75},
        squeeze=False,
    )
    fig.patch.set_facecolor(SURFACE)
    top = max(0.5, float(fdf["mae"].max()) * 1.15)

    for ax, (persona, title) in zip(axes[0], panels, strict=True):
        sel = fdf[fdf["persona"] == persona].sort_values("mae", ascending=False)
        y = np.arange(len(sel))
        for yi, (_, row) in zip(y, sel.iterrows(), strict=True):
            system_one = row["type"] == "System One"
            colour = JEV if system_one else BASE
            ax.plot([0, row["mae"]], [yi, yi], color=GRID, linewidth=1.4, zorder=1)
            ax.plot(
                row["mae"],
                yi,
                "o" if system_one else "s",
                markersize=9,
                color=colour,
                markeredgecolor=SURFACE,
                markeredgewidth=2,
                zorder=3,
            )
            ax.annotate(
                f"r = {row['r']:+.2f}",
                xy=(row["mae"], yi),
                xytext=(9, 0),
                textcoords="offset points",
                va="center",
                color=INK_2,
                fontsize=8,
            )
        ax.set_yticks(y, list(sel["model"]), fontsize=9)
        ax.set_xlim(0, top)
        ax.set_ylim(-0.6, len(sel) - 0.4)
        ax.set_xlabel("mean distance from human rate (lower is closer)", color=INK_2, fontsize=9.5)
        ax.set_title(title, color=INK, fontsize=11, fontweight="bold", loc="left", pad=10)
        _grid(ax, "x")

    handles = [
        Line2D([], [], marker="o", color=JEV, linestyle="none", markersize=8, label="System One"),
        Line2D(
            [], [], marker="s", color=BASE, linestyle="none", markersize=8, label="Chat, resampled"
        ),
    ]
    fig.legend(
        handles=handles,
        loc="lower left",
        bbox_to_anchor=(0.0, -0.02 - 0.5 / (1.4 + 0.42 * n_models)),
        ncol=2,
        frameon=False,
        fontsize=9,
        labelcolor=INK_2,
    )
    path = out / "fig_models_vs_human.png"
    fig.savefig(path, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)
    return path
