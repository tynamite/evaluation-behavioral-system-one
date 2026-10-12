"""The editorial figures build from committed data, and keep the house rules."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from jevbench.config import RAW_DIR, REPO_ROOT, TABLES_DIR
from jevbench.diagrams import _domain, build_diagrams, dumbbell

COMMITTED_RUN = RAW_DIR / "run_live_20260918T230710Z.jsonl"


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> list[Path]:
    out = tmp_path_factory.mktemp("diagrams")
    return build_diagrams(COMMITTED_RUN, TABLES_DIR, REPO_ROOT / "results" / "comparison", out)


def test_every_figure_is_an_accessible_figure(built: list[Path]) -> None:
    assert len(built) == 10
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
            r'<rect[^>]*width="(\d+(?:\.\d+)?)"[^>]*stroke="#bf4520"', path.read_text()
        )
        focal = [w for w in boxes if float(w) >= 60]
        assert len(focal) <= 2, f"{path.name}: {len(focal)} accented nodes or bars"


def test_dumbbell_axis_is_never_truncated() -> None:
    assert _domain([0.3, 0.7], 0.2) == (0.0, 0.8)
    assert _domain([-48, 80], 20) == (-60, 80)
    assert _domain([0, 0], 1) == (0.0, 1)


def test_dumbbell_refuses_too_many_rows() -> None:
    rows = [(f"r{i}", 0.1, 0.2) for i in range(9)]
    with pytest.raises(ValueError, match="4-8 rows"):
        dumbbell(rows, ref_name="a", focal_name="b", axis_title="x", step=0.2, order_note="")


def test_every_model_in_the_scatter_is_named(built: list[Path]) -> None:
    page = next(p for p in built if p.stem == "models-scatter").read_text()
    points = set(re.findall(r'<circle data-name="([^"]+)"', page))
    labels = set(re.findall(r'data-name="([^"]+)" data-role="label"', page))
    assert len(points) == 11
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
