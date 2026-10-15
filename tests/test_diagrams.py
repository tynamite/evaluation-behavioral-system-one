"""The editorial figures build from committed data, and keep the house rules."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import pytest

from jevbench.analysis import primary_run
from jevbench.config import RAW_DIR, REPO_ROOT, TABLES_DIR
from jevbench.diagrams import ACCENT, _domain, build_diagrams, dumbbell

COMMITTED_RUN = primary_run(RAW_DIR, live_only=True)


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> list[Path]:
    out = tmp_path_factory.mktemp("diagrams")
    return build_diagrams(COMMITTED_RUN, TABLES_DIR, REPO_ROOT / "results" / "comparison", out)


def test_every_figure_is_an_accessible_figure(built: list[Path]) -> None:
    assert len(built) == 11
    for path in built:
        page = path.read_text()
        slug = path.stem
        assert f'aria-labelledby="{slug}-title {slug}-desc"' in page
        # <title> comes first inside the svg, before <defs>.
        svg = page[page.index("<svg") :]
        assert svg.index(f'<title id="{slug}-title">') < svg.index("<defs>")
        assert "box-shadow" not in page and "JetBrains" not in page


def test_at_most_two_focal_nodes_or_bars(built: list[Path]) -> None:
    # Dumbbells use the accent for a whole series by design. Elsewhere the
    # accent marks at most two nodes or bars; a headline connector may share it.
    for path in built:
        if path.stem.startswith(("jev-", "persona-", "framing-")):
            continue
        boxes = re.findall(
            r'<rect[^>]*width="(\d+(?:\.\d+)?)"[^>]*stroke="' + ACCENT + '"', path.read_text()
        )
        focal = [w for w in boxes if float(w) >= 60]
        assert len(focal) <= 2, f"{path.name}: {len(focal)} accented nodes or bars"


def test_dumbbell_axis_is_never_truncated() -> None:
    assert _domain([0.3, 0.7], 0.2) == (0.0, 0.8)
    assert _domain([-48, 80], 20) == (-60, 80)
    assert _domain([0, 0], 1) == (0.0, 1)


def test_dumbbell_refuses_too_many_rows() -> None:
    rows = [(f"r{i}", "what was asked", 0.1, 0.2) for i in range(9)]
    with pytest.raises(ValueError, match="4-8 rows"):
        dumbbell(rows, ref_name="a", focal_name="b", axis_title="x", step=0.2, order_note="")


def test_every_model_in_the_scatter_is_named(built: list[Path]) -> None:
    page = next(p for p in built if p.stem == "models-scatter").read_text()
    points = set(re.findall(r'data-name="([^"]+)" data-x=', page))
    labels = set(re.findall(r'data-name="([^"]+)" data-role="label"', page))
    assert len(points) == 15
    assert labels == points


def test_scatter_labels_never_overlap() -> None:
    from jevbench.diagrams import _overlaps, place_labels

    # The real figure's layout, cluster included: every label must find room.
    xy = [
        (385, 352),
        (478, 236),
        (548, 299),
        (549, 334),
        (560, 293),
        (575, 301),
        (581, 325),
        (598, 310),
        (617, 303),
        (707, 328),
        (792, 306),
    ]
    pts = [(f"Model number {i}", float(x), float(y), 5.0) for i, (x, y) in enumerate(xy)]
    placed = place_labels(pts, size=10, bounds=(84, 44, 956, 516), reserved=[])
    boxes = [b for _x, _y, _a, b, _l in placed.values()]
    assert len(boxes) == 11
    for i, a in enumerate(boxes):
        for b in boxes[i + 1 :]:
            assert not _overlaps(a, b)


def test_framing_figure_plots_the_real_swings(built: list[Path]) -> None:
    # Pinned against results/comparison/measures.csv: d1 swings 24 then 31 points,
    # Jev 1.13 1 then 4, Jev 1.14 -9 then -5. An operator-precedence slip once drew
    # every row negative.
    page = next(p for p in built if p.stem == "framing-contrast").read_text()
    refs = [float(v) for v in re.findall(r'data-series="reference" data-value="([-\d.]+)"', page)]
    focal = [float(v) for v in re.findall(r'data-series="focal" data-value="([-\d.]+)"', page)]
    pairs = list(zip(refs, focal, strict=True))
    assert any(abs(a - 23.9) < 0.1 and abs(b - 31.1) < 0.1 for a, b in pairs)  # d1
    assert any(abs(a - 0.6) < 0.1 and abs(b - 4.1) < 0.1 for a, b in pairs)  # Jev 1.13
    assert any(abs(a + 9.3) < 0.1 and abs(b + 4.5) < 0.1 for a, b in pairs)  # Jev 1.14
    assert any(abs(a - 33.9) < 0.5 and abs(b - 41.2) < 0.5 for a, b in pairs)  # Drex 2.0
    # Jev 1.14, Microsoft-Decision-1 and Drex 1.5 reverse it; the chart keeps to
    # eight rows.
    assert sum(1 for a, _b in pairs if a < 0) == 3
    assert len(pairs) == 8


def test_steer_chart_compares_the_two_typical_person_prompts(built: list[Path]) -> None:
    page = next(p for p in built if p.stem == "jev-steer").read_text()
    assert len(re.findall(r'data-series="people"', page)) == 2 * 7
    for jev in ("Jev 1.14", "Jev 1.13"):
        for panel in ("typical_human_plain", "typical_human"):
            n = len(re.findall(rf'data-series="{jev}" data-panel="{panel}"', page))
            assert n == 7, (jev, panel)
    # Without "not the textbook-correct answer", Jev 1.13 gets 0.53 of the CRT
    # right and 1.14 0.50; with it, 0.32 and 0.27.
    for jev, plain, typical in (("Jev 1.13", "0.5310", "0.3183"), ("Jev 1.14", "0.4963", "0.2693")):
        assert f'data-series="{jev}" data-panel="typical_human_plain" data-value="{plain}"' in page
        assert f'data-series="{jev}" data-panel="typical_human" data-value="{typical}"' in page


def test_scatter_legend_matches_where_the_highlighted_model_sits(built: list[Path]) -> None:
    page = next(p for p in built if p.stem == "models-scatter").read_text()
    points = {
        n: (float(x), float(y))
        for n, x, y in re.findall(r'data-name="([^"]+)" data-x="([\d.]+)" data-y="([\d.]+)"', page)
    }
    # "Above the line" means told-to-be-human is further from people than neutral.
    above = {n for n, (x, y) in points.items() if y > x}
    note = re.search(r">([^<>]+): (the only model above the line|furthest above the line)<", page)
    # A model is singled out exactly when one sits above the line, and it is one of them.
    assert bool(note) == bool(above)
    if note:
        assert note.group(1) in above


def test_main_models_keep_shape_and_colour_in_the_scatter(built: list[Path]) -> None:
    from jevbench.diagrams import MAIN_MODELS, MAIN_SHAPES, SHORT

    page = next(p for p in built if p.stem == "models-scatter").read_text()
    tags = {
        "circle": "circle",
        "square": "rect",
        "diamond": "path",
        "triangle": "path",
        "hexagon": "polygon",
    }
    for model, colour in MAIN_MODELS:
        tag = tags[MAIN_SHAPES[model]]
        assert re.search(
            rf'<{tag} data-name="{re.escape(SHORT[model])}"[^>]*fill="{colour}"', page
        ), SHORT[model]


def test_dictator_chart_uses_the_full_human_distribution(built: list[Path]) -> None:
    from jevbench.benchmarks import DICTATOR_HUMAN_DISTRIBUTION

    # Engel (2011) Figure 2: the labels sum to one, and the three the text states.
    assert abs(sum(DICTATOR_HUMAN_DISTRIBUTION.values()) - 1) < 0.001
    assert DICTATOR_HUMAN_DISTRIBUTION["$0"] == 0.3611
    assert DICTATOR_HUMAN_DISTRIBUTION["$5"] == 0.1674
    assert DICTATOR_HUMAN_DISTRIBUTION["$10"] == 0.0544
    page = next(p for p in built if p.stem == "models-dictator").read_text()
    assert len(re.findall(r'data-series="people"', page)) == 5 * 11
    for name in ("Jev 1.14", "Jev 1.13"):
        assert len(re.findall(rf'data-series="{name}"', page)) == 11


def test_main_charts_carry_the_five_chosen_models(built: list[Path]) -> None:
    import pandas as pd

    from jevbench.diagrams import DECISION_MEASURES, MAIN_MODELS, SHORT

    cdf = pd.read_csv(REPO_ROOT / "results" / "comparison" / "statistics.csv")
    names = [SHORT[m] for m, _c in MAIN_MODELS]
    assert names == ["Jev 1.14", "Jev 1.13", "GPT-6 Luna Decisions", "Clef", "d1"]
    page = next(p for p in built if p.stem == "models-decisions").read_text()
    for (model, _c), name in zip(MAIN_MODELS, names, strict=True):
        dots = re.findall(
            rf'data-series="{re.escape(name)}" data-panel="neutral" data-value="([\d.]+)"', page
        )
        assert len(dots) == len(DECISION_MEASURES)
        # The first row is the CRT; its dot is the comparison's value for that model.
        crt = cdf[
            (cdf.instrument == "crt")
            & (cdf.statistic == "proportion_correct")
            & (cdf.persona == "neutral")
            & (cdf.model == model)
        ]["value"].iloc[0]
        assert abs(float(dots[0]) - crt) < 1e-3
    dictator = next(p for p in built if p.stem == "models-dictator").read_text()
    assert len(re.findall(r'data-series="people"', dictator)) == 5 * 11


def test_order_chart_averages_every_model_over_the_same_cells(built: list[Path]) -> None:
    page = next(p for p in built if p.stem == "models-order-effects").read_text()
    counts = set(re.findall(r"(\d+ shuffled cells · \d+ unshuffled)", page))
    assert len(counts) == 1, counts


def test_multi_model_runs_do_not_follow_the_focal_run(tmp_path: Path) -> None:
    import shutil

    # A focal run copied elsewhere must not move where the comparison runs are read from.
    moved = tmp_path / COMMITTED_RUN.name
    shutil.copy(COMMITTED_RUN, moved)
    paths = build_diagrams(
        moved, TABLES_DIR, REPO_ROOT / "results" / "comparison", tmp_path / "out"
    )
    assert any(p.stem == "models-dictator" for p in paths)


def test_every_figure_carries_the_watermark(built: list[Path]) -> None:
    from jevbench.diagrams import WATERMARK

    for path in built:
        assert f'<p class="mark" aria-hidden="true">{WATERMARK}</p>' in path.read_text(), path.stem


def test_h4_chart_draws_every_pair_from_the_table(built: list[Path]) -> None:
    import pandas as pd

    page = next(p for p in built if p.stem == "followup-h4").read_text()
    h4 = pd.read_csv(TABLES_DIR / "followup_h4.csv")
    for series in ("simulate", "estimate"):
        drawn = sorted(
            float(v)
            for v in re.findall(
                rf'data-series="{series}" data-panel="Jev 1.13" data-value="([^"]+)"', page
            )
        )
        assert drawn == pytest.approx(sorted(h4[f"scaled_error_{series}"]), abs=1e-4)
        # Jev 1.14's panel draws the same 23 statistics.
        assert len(re.findall(rf'data-series="{series}" data-panel="Jev 1.14"', page)) == 23


def _h4_table(rows: list[tuple[str, float, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "instrument": [r[0] for r in rows],
            "statistic": ["s"] * len(rows),
            "error_simulate": [r[1] for r in rows],
            "error_estimate": [r[2] for r in rows],
            "scaled_error_simulate": [r[1] for r in rows],
            "scaled_error_estimate": [r[2] for r in rows],
        }
    )


def test_h4_chart_counts_ties_apart() -> None:
    from jevbench.diagrams import JEV_113, fig_h4

    h4 = _h4_table([("a", 0.3, 0.1), ("b", 0.1, 0.3), ("c", 0.2, 0.2), ("d", 0.4, 0.2)])
    body = fig_h4([(JEV_113, h4)]).body
    assert "ESTIMATE CLOSER ON 2 OF 4 · TIED 1" in body


def test_h4_chart_renders_all_ties_with_no_test() -> None:
    from jevbench.diagrams import JEV_113, fig_h4

    h4 = _h4_table([("a", 0.2, 0.2), ("b", 0.3, 0.3)])
    fig = fig_h4([(JEV_113, h4)])
    assert "ESTIMATE CLOSER ON 0 OF 2 · TIED 2" in fig.body and "P = n/a" in fig.body
    # One surviving pair: drawn, with no test.
    one = fig_h4([(JEV_113, h4.iloc[:1])])
    assert "TIED 1" in one.body and "P = n/a" in one.body


def test_h4_chart_never_prints_a_zero_p_value() -> None:
    from jevbench.diagrams import JEV_113, fig_h4

    h4 = _h4_table([(f"i{k}", 0.5 + k / 100, 0.1) for k in range(23)])
    fig = fig_h4([(JEV_113, h4)])
    assert "< 0.001" in fig.subtitle and "0.000" not in fig.subtitle + fig.body


def test_h4_chart_is_removed_when_a_run_has_no_pairs(tmp_path: Path) -> None:
    import shutil

    tables = tmp_path / "tables"
    shutil.copytree(TABLES_DIR, tables)
    (tables / "followup_h4.csv").unlink()
    out = tmp_path / "diagrams"
    out.mkdir()
    (out / "followup-h4.html").write_text("stale")
    paths = build_diagrams(COMMITTED_RUN, tables, REPO_ROOT / "results" / "comparison", out)
    assert len(paths) == 10 and not (out / "followup-h4.html").exists()


def test_figures_follow_the_run_they_are_built_from(tmp_path: Path) -> None:
    """A run without the follow-up items draws no H4 chart, whatever the saved tables say."""
    import json

    from jevbench.diagrams import build_diagrams_for_run
    from jevbench.instruments import all_probes

    followup = {p.probe_id for p in all_probes(["followup"])}
    run = tmp_path / "run_live_20261013T000000Z_typesafe--jev-1.13.jsonl"
    with COMMITTED_RUN.open() as src, run.open("w") as dst:
        for line in src:
            if line.strip() and json.loads(line)["probe_id"] not in followup:
                dst.write(line)
    paths = build_diagrams_for_run(run, REPO_ROOT / "results" / "comparison", tmp_path / "out")
    assert len(paths) == 10
    assert not (tmp_path / "out" / "followup-h4.html").exists()


def test_diagrams_refuse_a_run_their_labels_would_misdescribe(tmp_path: Path) -> None:
    import json

    from jevbench.diagrams import build_diagrams_for_run

    run = tmp_path / "run_live_20261013T000000Z_typesafe--jev-1.13.jsonl"
    with COMMITTED_RUN.open() as src, run.open("w") as dst:
        for line in src:
            r = json.loads(line)
            if r["replicate"] < 3:  # a default three-replicate run
                dst.write(line)
    with pytest.raises(ValueError, match="do not have exactly 10 successful repeats"):
        build_diagrams_for_run(run, REPO_ROOT / "results" / "comparison", tmp_path / "out")


def test_diagrams_refuse_a_run_missing_a_prompt(tmp_path: Path) -> None:
    import json

    from jevbench.diagrams import build_diagrams_for_run

    run = tmp_path / "run_live_20261013T000000Z_typesafe--jev-1.13.jsonl"
    with COMMITTED_RUN.open() as src, run.open("w") as dst:
        for line in src:
            if json.loads(line)["persona"] == "neutral":
                dst.write(line)
    with pytest.raises(ValueError, match="no records under"):
        build_diagrams_for_run(run, REPO_ROOT / "results" / "comparison", tmp_path / "out")


def test_diagrams_refuse_a_run_with_a_failed_repeat(tmp_path: Path) -> None:
    """A single errored call leaves a cell short of the 10 repeats the figures claim."""
    import json

    from jevbench.diagrams import build_diagrams_for_run

    run = tmp_path / "run_live_20261013T000000Z_typesafe--jev-1.13.jsonl"
    failed = False
    with COMMITTED_RUN.open() as src, run.open("w") as dst:
        for line in src:
            r = json.loads(line)
            if not failed and r["arm"] == "jev" and r["probe_id"] == "crt_bat_ball":
                r["error"], r["probabilities"], failed = "refused: test", None, True
                line = json.dumps(r) + "\n"
            dst.write(line)
    with pytest.raises(
        ValueError, match=r"1 of \d+ core item-and-prompt cells do not have exactly 10"
    ):
        build_diagrams_for_run(run, REPO_ROOT / "results" / "comparison", tmp_path / "out")


def test_h4_chart_cites_the_run_it_was_drawn_from(built: list[Path]) -> None:
    page = next(p for p in built if p.stem == "followup-h4").read_text()
    assert f"data/raw/{COMMITTED_RUN.name}" in page


def test_diagrams_refuse_duplicated_repeats(tmp_path: Path) -> None:
    """A duplicated record is not one of the 10 repeats the figures claim."""
    from jevbench.diagrams import build_diagrams_for_run

    run = tmp_path / "run_live_20261013T000000Z_typesafe--jev-1.13.jsonl"
    lines = COMMITTED_RUN.read_text().splitlines(keepends=True)
    run.write_text("".join(lines) + lines[0])  # the first record (a Jev one), twice
    with pytest.raises(
        ValueError, match=r"1 of \d+ core item-and-prompt cells do not have exactly"
    ):
        build_diagrams_for_run(run, REPO_ROOT / "results" / "comparison", tmp_path / "out")


def test_diagrams_refuse_a_repeat_with_no_distribution(tmp_path: Path) -> None:
    import json

    from jevbench.diagrams import build_diagrams_for_run

    run = tmp_path / "run_live_20261013T000000Z_typesafe--jev-1.13.jsonl"
    done = False
    with COMMITTED_RUN.open() as src, run.open("w") as dst:
        for line in src:
            r = json.loads(line)
            if not done and r["arm"] == "jev" and r["probe_id"] == "crt_bat_ball":
                r["probabilities"], done = {}, True
                line = json.dumps(r) + "\n"
            dst.write(line)
    with pytest.raises(
        ValueError, match=r"1 of \d+ core item-and-prompt cells do not have exactly"
    ):
        build_diagrams_for_run(run, REPO_ROOT / "results" / "comparison", tmp_path / "out")


def test_shown_path_is_absolute_outside_the_repo(tmp_path: Path) -> None:
    from jevbench.diagrams import _shown_path

    assert _shown_path(COMMITTED_RUN) == f"data/raw/{COMMITTED_RUN.name}"
    outside = tmp_path / "run.jsonl"
    assert _shown_path(outside) == str(outside.resolve())


def test_order_study_chart_draws_both_versions_on_every_instrument() -> None:
    import pandas as pd

    from jevbench.diagrams import fig_order_study

    inst = pd.read_csv(REPO_ROOT / "results" / "order_study" / "instruments.csv")
    fig = fig_order_study(inst)
    assert fig is not None
    n = inst[inst["test"] == "O1 1.13"]["instrument"].nunique()
    for version in ("1.14", "1.13"):
        for test in ("O1", "O3"):
            marks = re.findall(rf'data-series="Jev {version}" data-panel="{test}"', fig.body)
            assert len(marks) == n, (version, test)
    # Nothing to draw without the four tests it plots.
    assert fig_order_study(inst[inst["test"] != "O3 1.14"]) is None


def test_route_comes_from_the_backend_each_run_records() -> None:
    import pandas as pd

    from jevbench.diagrams import JEV_113, JEV_114_ID, _route

    health = pd.read_csv(REPO_ROOT / "results" / "comparison" / "health.csv")
    files = dict(zip(health["model"], health["run_file"], strict=True))
    assert _route([JEV_114_ID, JEV_113], files) == (
        "Jev 1.14 was called through TypeSafe's API directly, the rest through OpenRouter. "
    )
    # The same model ID run through OpenRouter would claim no direct route.
    assert _route([JEV_114_ID], {JEV_114_ID: files[JEV_113]}) == ""
    assert _route([JEV_114_ID], None) == ""


def test_diagrams_name_a_main_model_missing_from_the_comparison(tmp_path: Path) -> None:
    import shutil

    import pandas as pd

    cmp = tmp_path / "comparison"
    shutil.copytree(REPO_ROOT / "results" / "comparison", cmp)
    health = pd.read_csv(cmp / "health.csv")
    health[health["model"] != "typesafe/jev-1.14.0"].to_csv(cmp / "health.csv", index=False)
    with pytest.raises(ValueError, match=re.escape("no run for typesafe/jev-1.14.0")):
        build_diagrams(COMMITTED_RUN, TABLES_DIR, cmp, tmp_path / "out")


def test_route_is_read_from_the_raw_directory_the_charts_use(tmp_path: Path) -> None:
    import shutil

    from jevbench.config import RAW_DIR

    # A relocated copy of the raw data whose 1.14 run records another route: the
    # caption must follow the copy, not the default raw directory.
    raw = tmp_path / "raw"
    shutil.copytree(RAW_DIR, raw, ignore=shutil.ignore_patterns("pick_number", "r2", "r3"))
    run = raw / "order_study" / "r1" / "run_live_20261014T231829Z_jev-1.14.0.jsonl"
    run.write_text(
        run.read_text().replace('"backend": "typesafe"', '"backend": "openrouter"'),
        encoding="utf-8",
    )
    built = build_diagrams(
        COMMITTED_RUN, TABLES_DIR, REPO_ROOT / "results" / "comparison", tmp_path / "out", raw
    )
    page = next(p for p in built if p.stem == "models-decisions").read_text()
    assert "called through TypeSafe" not in page


def test_figures_build_from_a_comparison_of_relocated_runs(tmp_path: Path) -> None:
    """A comparison built from runs outside data/raw/ records where they are, so the
    figures can load them, nested paths included."""
    import shutil

    from jevbench.compare import compare_runs
    from jevbench.config import RAW_DIR

    health = pd.read_csv(REPO_ROOT / "results" / "comparison" / "health.csv")
    files = dict(zip(health["model"], health["run_file"], strict=True))
    raw = tmp_path / "raw"
    copies = []
    for f in sorted({files[m] for m in health["model"]}):
        dst = raw / f
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(RAW_DIR / f, dst)
        copies.append(dst)
    cmp = tmp_path / "comparison"
    compare_runs(copies, cmp)
    built = build_diagrams(COMMITTED_RUN, TABLES_DIR, cmp, tmp_path / "out", raw)
    assert any(p.stem == "models-dictator" for p in built)
