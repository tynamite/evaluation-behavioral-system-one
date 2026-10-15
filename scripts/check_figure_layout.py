#!/usr/bin/env python3
"""Detect overlapping labels in the generated figures.

The palette validator checks colour; nothing checks layout, and eyeballing a
chart is exactly how a collision ships. This renders each figure and compares
the true bounding boxes of every visible text artist, reporting any pair that
intersects.

    python scripts/check_figure_layout.py [path/to/run.jsonl]

Exits non-zero if any overlap is found.
"""

from __future__ import annotations

import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.text import Text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jevbench import plots  # noqa: E402
from jevbench.analysis import (  # noqa: E402
    compute_stats,
    core_order_cells,
    load_records,
    order_effects,
    primary_run,
)

# Ignore sub-pixel touching; only report overlaps a reader would notice.
MIN_OVERLAP_PX = 2.0


def _texts(fig: plt.Figure) -> list[Text]:
    """Every text a reader actually sees.

    Tick labels need care: matplotlib keeps Text artists for ticks that fall
    outside the current axis limits, and they report as visible even though
    nothing is drawn. Including them produces phantom collisions, so ticks are
    filtered against the axis limits rather than by the visibility flag.
    """
    out: list[Text] = []
    for ax in fig.axes:
        out.extend(t for t in ax.texts if t.get_visible() and t.get_text().strip())
        for axis, lims in ((ax.xaxis, ax.get_xlim()), (ax.yaxis, ax.get_ylim())):
            lo, hi = sorted(lims)
            for tick in axis.get_major_ticks():
                if not lo - 1e-9 <= tick.get_loc() <= hi + 1e-9:
                    continue
                label = tick.label1
                if label.get_visible() and label.get_text().strip():
                    out.append(label)
        if ax.get_title():
            out.append(ax.title)
        legend = ax.get_legend()
        if legend is not None:
            out.extend(t for t in legend.get_texts() if t.get_text().strip())
    for legend in fig.legends:
        out.extend(t for t in legend.get_texts() if t.get_text().strip())
    out.extend(t for t in fig.texts if t.get_visible() and t.get_text().strip())
    return out


def _overlaps(fig: plt.Figure) -> list[tuple[str, str, float]]:
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    items = [(t, t.get_window_extent(renderer=renderer)) for t in _texts(fig)]
    found: list[tuple[str, str, float]] = []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            a, b = items[i][1], items[j][1]
            dx = min(a.x1, b.x1) - max(a.x0, b.x0)
            dy = min(a.y1, b.y1) - max(a.y0, b.y0)
            if dx > MIN_OVERLAP_PX and dy > MIN_OVERLAP_PX:
                found.append((items[i][0].get_text(), items[j][0].get_text(), dx * dy))
    return found


def main(argv: list[str]) -> int:
    run = Path(argv[1]) if len(argv) > 1 else primary_run(ROOT / "data" / "raw")
    if run is None:
        print("no run file found", file=sys.stderr)
        return 1
    df = load_records(run)
    sdf = pd.DataFrame([asdict(s) for s in compute_stats(df)])
    odf = core_order_cells(order_effects(df))
    # Draw into a scratch directory: this only measures layout, and must not
    # leave files beside the committed figures.
    out = Path(tempfile.mkdtemp(prefix="jevbench-layout-"))

    builders = {
        "fig1_vs_human": lambda: plots.fig_vs_human(sdf, out),
        "fig2_gap_from_human": lambda: plots.fig_gap(sdf, out),
        "fig3_persona": lambda: plots.fig_persona(sdf, out),
        "fig4_reflection": lambda: plots.fig_reflection(sdf, out),
        "fig5_distributions": lambda: plots.fig_distributions(df, out),
        "fig6_order_effects": lambda: plots.fig_order_effects(odf, out),
        "fig7_human_fidelity": lambda: plots.fig_human_fidelity(sdf, out),
        # These two return None (no figure at all) when the run has no data for the
        # follow-up battery, e.g. a run made with --modules that leaves it out.
        "fig8_followup_elicitations": lambda: plots.fig_followup_elicitations(sdf, out),
        "fig9_followup_currency": lambda: plots.fig_followup_currency(sdf, out),
    }
    # The option-order addendum's figure, when its analysis has been run.
    order_study = ROOT / "results" / "order_study" / "instruments.csv"
    if order_study.exists():
        inst = pd.read_csv(order_study)
        builders["order_study"] = lambda: plots.fig_order_study(inst, out)

    # Re-render inside this process so the figure is still open for measurement.
    failures = 0
    for name, build in builders.items():
        build()
        fig = plt.figure(plt.get_fignums()[-1]) if plt.get_fignums() else None
        # build() closes its figure, so re-run the body against a live canvas:
        del fig
        failures += _check(name, build)
    if failures:
        print(f"\n{failures} figure(s) with overlapping labels")
        return 1
    print("\nno overlapping labels in any figure")
    return 0


def _check(name: str, build) -> int:  # type: ignore[no-untyped-def]
    """Rebuild with savefig patched out so the figure survives for measurement."""
    real_close = plt.close
    captured: list[plt.Figure] = []

    def keep(fig=None):  # type: ignore[no-untyped-def]
        if isinstance(fig, plt.Figure):
            captured.append(fig)
        else:
            real_close(fig) if fig is not None else None

    plt.close = keep  # type: ignore[assignment]
    try:
        build()
    finally:
        plt.close = real_close  # type: ignore[assignment]

    bad = 0
    if not captured:
        print(f"{name}: skipped (no data for this figure's instruments)")
    for fig in captured:
        overlaps = _overlaps(fig)
        if overlaps:
            bad = 1
            print(f"\n{name}: {len(overlaps)} overlapping label pair(s)")
            for a, b, area in sorted(overlaps, key=lambda o: -o[2])[:8]:
                print(f"    {a!r:38s} overlaps {b!r:38s} ({area:.0f} px2)")
        else:
            print(f"{name}: clean")
        real_close(fig)
    return bad


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
