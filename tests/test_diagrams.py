"""The editorial figures build from committed data, and keep the house rules."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from jevbench.analysis import primary_run
from jevbench.config import RAW_DIR, REPO_ROOT, TABLES_DIR
from jevbench.diagrams import ACCENT, _domain, build_diagrams, dumbbell

COMMITTED_RUN = primary_run(RAW_DIR)


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> list[Path]:
    out = tmp_path_factory.mktemp("diagrams")
    return build_diagrams(COMMITTED_RUN, TABLES_DIR, REPO_ROOT / "results" / "comparison", out)


def test_every_figure_is_an_accessible_figure(built: list[Path]) -> None:
    assert len(built) == 15
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
    assert len(points) == 12
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
    # Jev 1 then 4. An operator-precedence slip once drew every row negative.
    page = next(p for p in built if p.stem == "framing-contrast").read_text()
    refs = [float(v) for v in re.findall(r'data-series="reference" data-value="([-\d.]+)"', page)]
    focal = [float(v) for v in re.findall(r'data-series="focal" data-value="([-\d.]+)"', page)]
    pairs = list(zip(refs, focal, strict=True))
    assert any(abs(a - 23.9) < 0.1 and abs(b - 31.1) < 0.1 for a, b in pairs)  # d1
    assert any(abs(a - 0.6) < 0.1 and abs(b - 4.1) < 0.1 for a, b in pairs)  # Jev
    assert sum(1 for a, _b in pairs if a < 0) == 1  # only Microsoft-Decision-1 reverses it


def test_decision_chart_shows_all_three_series_on_every_row(built: list[Path]) -> None:
    page = next(p for p in built if p.stem == "jev-decisions").read_text()
    for series in ("people", "neutral", "typical"):
        assert len(re.findall(rf'data-series="{series}"', page)) == 7
    # Pinned: the cognitive reflection row (Frederick's three items) is 0.41
    # people, 0.99 and 0.32 for Jev.
    assert 'data-series="neutral" data-value="0.9950"' in page
    assert 'data-series="typical" data-value="0.3183"' in page


def test_steer_chart_compares_the_two_typical_person_prompts(built: list[Path]) -> None:
    page = next(p for p in built if p.stem == "jev-steer").read_text()
    for series in ("people", "plain", "typical"):
        assert len(re.findall(rf'data-series="{series}"', page)) == 7
    # Without "not the textbook-correct answer", Jev gets 0.53 of the CRT right.
    assert 'data-series="plain" data-value="0.5310"' in page
    assert 'data-series="typical" data-value="0.3183"' in page


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
    tags = {"circle": "circle", "square": "rect", "diamond": "path", "triangle": "path"}
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
    page = next(p for p in built if p.stem == "dictator-distribution").read_text()
    assert len(re.findall(r'data-series="people"', page)) == 11
    assert len(re.findall(r'data-series="jev"', page)) == 11


def test_main_charts_carry_the_four_chosen_models(built: list[Path]) -> None:
    import pandas as pd

    from jevbench.diagrams import DECISION_MEASURES, MAIN_MODELS, SHORT

    cdf = pd.read_csv(REPO_ROOT / "results" / "comparison" / "statistics.csv")
    names = [SHORT[m] for m, _c in MAIN_MODELS]
    assert names == ["Jev 1.13", "GPT-6 Luna Decisions", "Clef", "d1"]
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
    assert len(re.findall(r'data-series="people"', dictator)) == 4 * 11


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
