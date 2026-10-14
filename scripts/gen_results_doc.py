#!/usr/bin/env python3
"""Regenerate docs/RESULTS.md from a run's statistics table.

Every number in the write-up is produced here, from the committed raw records.
Nothing is transcribed by hand, so the prose cannot disagree with the data.

    python scripts/gen_results_doc.py [path/to/run.jsonl]
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jevbench.analysis import (  # noqa: E402
    compute_stats, h4_summary, load_records, order_effects, primary_run, simulate_vs_estimate,
)
from jevbench.benchmarks import BENCHMARKS  # noqa: E402
from jevbench.diagrams import check_editorial_run  # noqa: E402
from dataclasses import asdict  # noqa: E402

PERSONA_ORDER = ["neutral", "typical_human", "typical_human_plain", "rational_agent", "antisocial"]
PERSONA_LABEL = {
    "neutral": "Neutral",
    "typical_human": "As typical human",
    "typical_human_plain": "As typical human (no steer)",
    "rational_agent": "As rational agent",
    "antisocial": "Antisocial",
}


def fmt(v: float | None, places: int = 2) -> str:
    if v is None or not isinstance(v, (int, float)) or pd.isna(v):
        return "—"
    return f"{v:.{places}f}"


FIGURES = ROOT / "results" / "figures"
# The committed figures are drawn from the committed run only (see
# `check_editorial_run`); main() turns this off for any other run, so its
# tables are never shown beside another experiment's figures.
EMBED_FIGURES = True


def committed_unchanged(path: Path) -> bool:
    """Whether git tracks `path` and it matches the committed version."""
    rel = str(path.resolve().relative_to(ROOT))
    tracked = subprocess.run(["git", "-C", str(ROOT), "ls-files", "--error-unmatch", rel],
                             capture_output=True).returncode == 0
    clean = subprocess.run(["git", "-C", str(ROOT), "diff", "--quiet", "HEAD", "--", rel],
                           capture_output=True).returncode == 0
    return tracked and clean


def figures_mismatch(run: Path, df: pd.DataFrame) -> str | None:
    """Why the committed figures would misdescribe this run, if they would.

    They are drawn from one file, the committed run, so only that exact file,
    unchanged from what git has committed, gets them; the shape check alone
    would pass an edited copy.
    """
    committed = primary_run(ROOT / "data" / "raw", live_only=True)
    if committed is None or run.resolve() != committed.resolve():
        return f"{run.name} is not the committed run"
    if not committed_unchanged(run):
        return f"{run.name} differs from the committed file"
    try:
        check_editorial_run(df)
    except ValueError as exc:
        return str(exc)
    return None


def figures(*items: tuple[str, str]) -> list[str]:
    """Markdown for the committed figures among `items` (file, alt text).

    A figure that is missing, or has been redrawn since it was committed
    (`jevbench diagrams --run` can redraw it from another run), is left out
    rather than shown beside tables it may not match.
    """
    if not EMBED_FIGURES:
        return []
    out = []
    for name, alt in items:
        path = FIGURES / name
        if path.exists() and committed_unchanged(path):
            out.append(f"![{alt}](../results/figures/{name})\n")
        elif path.exists():
            print(f"left out {name}: it differs from the committed figure", file=sys.stderr)
    return out


def persona_table(sdf: pd.DataFrame, rows: list[tuple[str, str, str]], arm: str = "jev") -> list[str]:
    personas = [p for p in PERSONA_ORDER if p in set(sdf["persona"])]
    out = ["| Measure | " + " | ".join(PERSONA_LABEL[p] for p in personas) + " | Human |",
           "|---|" + "---:|" * (len(personas) + 1)]
    for inst, stat, label in rows:
        sel = sdf[(sdf.instrument == inst) & (sdf.statistic == stat) & (sdf.arm == arm)]
        vals = {r["persona"]: r["value"] for _, r in sel.iterrows()}
        bench = sel["benchmark_key"].iloc[0] if len(sel) else ""
        human = BENCHMARKS[bench].value if bench and bench in BENCHMARKS else None
        cells = [fmt(vals.get(p)) for p in personas]
        out.append(f"| {label} | " + " | ".join(cells) + f" | {fmt(human)} |")
    return out


def main(argv: list[str]) -> int:
    run = Path(argv[1]) if len(argv) > 1 else primary_run(ROOT / "data" / "raw", live_only=True)
    if run is None:
        print("no run file found", file=sys.stderr)
        return 1
    df = load_records(run)
    global EMBED_FIGURES
    reason = figures_mismatch(run, df)
    if reason:
        EMBED_FIGURES = False
        print(f"figures left out: they are drawn from the committed run, not this one ({reason})",
              file=sys.stderr)
    sdf = pd.DataFrame([asdict(s) for s in compute_stats(df)])
    odf = order_effects(df)

    n_err = int(df["error"].notna().sum())
    cost = float(sum(float((u or {}).get("cost") or 0.0) for u in df["usage"]))
    jev_cost = float(sum(float((u or {}).get("cost") or 0.0)
                         for u in df[df.arm == "jev"]["usage"]))
    models = sorted({m for m in df["model"].unique()})

    L: list[str] = []
    L.append("# Results\n")
    L.append("<!-- Generated by scripts/gen_results_doc.py — do not edit by hand. -->\n")
    L.append(f"Run file: `{run.name}`  ")
    L.append(f"Models: {', '.join(f'`{m}`' for m in models)}  ")
    L.append(f"Records: {len(df):,} ({n_err} transport errors, excluded)  ")
    L.append(f"Total cost: ${cost:.4f} (Jev arm ${jev_cost:.4f})\n")
    L.append("Every table below is the Jev arm only; the chat baseline and the other "
             "System One models are compared in `results/comparison/`. Values are "
             "probability mass, computed from the returned distributions rather than "
             "from the point answers. Human values are "
             "literature reference points, not a matched control group — see "
             "[BENCHMARKS.md](BENCHMARKS.md).\n")
    L += figures(("how-it-works.png", "How one item becomes a number"))

    L.append("## Cognitive reflection\n")
    L += persona_table(sdf, [
        ("crt", "proportion_correct", "CRT correct (Frederick's 3 items)"),
        ("crt", "proportion_correct_all6", "CRT correct (all 6 items)"),
        ("crt", "probability_mass_on_lure", "CRT mass on intuitive lure"),
    ])
    L.append("")

    L.append("## Fluid reasoning by depth\n")
    L.append("Accuracy on an authored ICAR-format item set. **Not an IQ score.**\n")
    steps = sorted(int(s.rsplit("_", 1)[1]) for s in
                   sdf[sdf.statistic.str.startswith("accuracy_steps_")].statistic.unique())
    L += persona_table(sdf, [("fluid_reasoning", "accuracy", "Overall accuracy")] +
                       [("fluid_reasoning", f"accuracy_steps_{s}", f"{s} inference step(s)")
                        for s in steps] +
                       [("fluid_reasoning", "depth_penalty_1_vs_3plus", "Depth penalty (1 vs 3+)")])
    L.append("")

    L.append("## Social preferences\n")
    L += figures(
        ("jev-games-neutral.png", "Jev in the economic games, with no instruction"),
        ("models-games.png", "Four System One models against people in the economic games"),
        ("dictator-distribution.png", "What a single call returns: Jev's dictator distribution"),
        ("models-dictator.png", "What a single call returns, four models"),
        ("persona-antisocial.png", "Jev's antisocial persona in the economic games"),
        ("models-antisocial.png", "The antisocial persona in the economic games, four models"),
    )
    L += persona_table(sdf, [
        ("dictator", "mean_share", "Dictator: share given"),
        ("dictator", "prob_give_zero", "Dictator: mass on giving nothing"),
        ("dictator", "prob_give_half", "Dictator: mass on giving half"),
        ("ultimatum_proposer", "mean_share", "Ultimatum: offer share"),
        ("ultimatum_responder", "prob_reject_low_offer", "Ultimatum: reject a $1 offer"),
        ("trust_sender", "mean_share", "Trust: share sent"),
        ("trust_trustee", "return_share_sent_5", "Trust: share returned"),
        ("public_goods", "mean_share", "Public goods: contribution"),
        ("prisoners_dilemma", "cooperation_one_shot", "PD: cooperation (one-shot)"),
    ])
    L.append("")

    L.append("## Decision anomalies\n")
    L += figures(
        ("jev-decisions.png", "Jev on the seven decision-making tests, with and without the "
                              "typical-person instruction"),
        ("models-decisions.png", "Four System One models against people on the seven "
                                 "decision-making tests"),
        ("jev-steer.png", "Jev under the typical-person instruction with and without its steer"),
        ("framing-contrast.png", "The framing reversal by model"),
    )
    L += persona_table(sdf, [
        ("framing", "prob_certain_gain_frame", "Framing: certain option (gain frame)"),
        ("framing", "prob_certain_loss_frame", "Framing: certain option (loss frame)"),
        ("framing", "framing_swing", "Framing swing (human ≈ 0.50)"),
        ("allais", "prob_certain_pair1", "Allais: certainty in pair 1"),
        ("allais", "independence_violation", "Allais: independence violation"),
        ("conjunction", "prob_fallacy_forced_choice", "Conjunction fallacy (forced choice)"),
        ("conjunction_axiom", "axiom_margin", "Conjunction axiom margin (negative = violation)"),
        ("base_rate", "prob_correct_band", "Base rate: 0-10% band (vs Bayesian answers)"),
        ("anchoring", "anchoring_effect", "Anchoring gap (human ≈ 20 points)"),
        ("sunk_cost", "prob_continue", "Sunk cost: continue"),
    ])
    L.append("")

    L.append("## Risk, time and strategic depth\n")
    L += persona_table(sdf, [
        ("holt_laury", "expected_safe_choices", "Holt–Laury safe choices (risk neutral = 4)"),
        ("present_bias", "present_bias_gap", "Present-bias gap (direction only)"),
        ("beauty_contest", "expected_guess", "p-beauty: expected guess"),
        ("beauty_contest", "mass_at_0", "p-beauty: mass on equilibrium (0)"),
        ("money_request", "expected_request", "11-20 game: expected request"),
    ])
    L.append("")

    L.append("## Personality and Dark Triad\n")
    L.append("The Dark Triad scale is a **manipulation check**, not a diagnostic claim.\n")
    L += persona_table(sdf, [
        ("mini_ipip", t, f"Big Five: {t}")
        for t in ["extraversion", "agreeableness", "conscientiousness", "neuroticism", "openness"]
    ] + [
        ("dirty_dozen", t, f"Dark Triad: {t}")
        for t in ["machiavellianism", "psychopathy", "narcissism", "overall"]
    ])
    L.append("")

    L.append("## Option-order sensitivity\n")
    L += figures(
        ("order-effects.png", "Option-order sensitivity, Jev"),
        ("models-order-effects.png", "Option-order sensitivity, four models"),
    )
    if len(odf):
        followup = odf[odf.followup]
        odf = odf[~odf.followup]
        floor = odf[~odf.shuffled]
        odf = odf[odf.shuffled]
        if len(odf):  # a follow-up-only run has no core cells
            L.append(f"The core battery's multiple-choice items ({len(odf)} probe × persona cells), the "
                     "set H6 was written for: their options are shuffled per replicate. Likert and "
                     "yes/no items are not shuffled, so they measure replicate-to-replicate variation "
                     "with nothing changed instead.\n")
            L.append(f"- Mean total-variation distance across reorderings: **{odf.mean_tv_distance.mean():.4f}**")
            L.append(f"- Median: {odf.mean_tv_distance.median():.4f}")
            L.append(f"- 95th percentile: {odf.mean_tv_distance.quantile(0.95):.4f}")
            if len(floor):
                L.append(f"- Same measure on the {len(floor)} unshuffled cells (replicates with nothing reordered, a rough noise floor): "
                         f"{floor.mean_tv_distance.mean():.4f}")
            L.append(f"- Largest single probe: {odf.mean_tv_distance.max():.4f} "
                     f"(`{odf.loc[odf.mean_tv_distance.idxmax(), 'probe_id']}`)")
            worst = odf.nlargest(5, "mean_tv_distance")[["probe_id", "persona", "mean_tv_distance"]]
            L.append("\nMost order-sensitive probes:\n")
            L.append("| Probe | Persona | Mean TV distance |")
            L.append("|---|---|---:|")
            for _, r in worst.iterrows():
                L.append(f"| `{r.probe_id}` | {r.persona} | {r.mean_tv_distance:.4f} |")
        if len(followup):
            fs, fu = followup[followup.shuffled], followup[~followup.shuffled]
            L.append(f"\nThe follow-up items, reported apart: {fs.mean_tv_distance.mean():.4f} on "
                     f"{len(fs)} shuffled cells, {fu.mean_tv_distance.mean():.4f} on {len(fu)} "
                     "unshuffled ones.")
    L.append("")

    h4 = simulate_vs_estimate(sdf)
    if len(h4):
        L.append("## Follow-up H4: simulate or estimate\n")
        L += figures(("followup-h4.png", "Jev's error on each of the 23 statistics, "
                                         "simulated and estimated"))
        L.append("Each follow-up statistic measured two ways: the item asked with the typical-person "
                 "prompt (simulate), and its population question asked with no persona (estimate). "
                 "Errors are distances from the original study's published value (Many Labs 2 "
                 "reports only effect sizes, not per-condition values), in the item's own units, as "
                 "preregistered. Those units differ (proportions, 1–7 ratings, percentage bands), so "
                 "the raw test weighs the ratings and percentages most; as a post-hoc check the same "
                 "test is repeated with each error divided by its scale's range (1, 6 and 100), and "
                 "the mean errors below are on that scaled footing. The population questions for the "
                 "six items reused from the first project (CRT, framing, conjunction, sunk cost, "
                 "Allais, base rate) were asked on 13 October 2026, after the main run.\n")
        L.append("| Item | Statistic | Published | Simulate | Estimate | Error (simulate) | "
                 "Error (estimate) | Scaled (simulate) | Scaled (estimate) |")
        L.append("|---|---|---:|---:|---:|---:|---:|---:|---:|")
        for _, r in h4.iterrows():
            L.append(f"| {r.instrument} | {r.statistic} | {r.human:.2f} | {r.simulate:.2f} | "
                     f"{r.estimate:.2f} | {r.error_simulate:.3f} | {r.error_estimate:.3f} | "
                     f"{r.scaled_error_simulate:.3f} | {r.scaled_error_estimate:.3f} |")
        for label, sim, est in (
            ("as preregistered", "typical_human", "neutral"),
            ("simulate without the steer, estimate with no persona", "typical_human_plain", "neutral"),
            ("both asked under the steer-free typical-person prompt (exploratory)",
             "typical_human_plain", "typical_human_plain"),
        ):
            hs = h4_summary(simulate_vs_estimate(sdf, simulate=sim, estimate=est))
            if "estimate_closer" not in hs:
                continue  # e.g. runs that ask estimate items with no persona only
            def p(v: float | None) -> str:
                return "n/a (every pair tied)" if v is None else f"{v:.3f}"

            L.append(f"\n- {label.capitalize()}: estimate closer on {hs['estimate_closer']} of "
                     f"{hs['n']}; one-sided Wilcoxon p = {p(hs['wilcoxon_p_one_sided'])} on the raw "
                     f"errors ({p(hs['wilcoxon_p_scaled'])} scaled, post-hoc); mean scaled error "
                     f"{hs['mean_scaled_error_simulate']:.3f} (simulate) vs "
                     f"{hs['mean_scaled_error_estimate']:.3f} (estimate)")
        L.append("")

    across = figures(
        ("models-scatter.png", "Every model's distance from the published human results"),
        ("health-checks.png", "What the health table caught"),
    )
    if across:
        L.append("## Across the System One models\n")
        L.append("All twelve models are compared, with the discussion, in "
                 "[MODELS.md](MODELS.md).\n")
        L += across
        L.append("")

    order = figures(("order-study.png", "How far option order moves Jev's answers, per "
                                        "instrument, 1.13 and 1.14"))
    if order:
        L.append("## Addendum: option order, and the Jev 1.14 preview\n")
        L.append("A separate preregistered study, run on 14 October 2026 on Jev 1.13 and the "
                 "1.14 preview; the tables above are not from it. Its plan is in "
                 "[ORDER_PREREGISTRATION.md](../ORDER_PREREGISTRATION.md), its results in "
                 "[results/order_study/](../results/order_study/) and the "
                 "[README](../README.md#addendum-14-october-2026-option-order-and-the-jev-114-preview).\n")
        L += order
        L.append("")

    out = ROOT / "docs" / "RESULTS.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
