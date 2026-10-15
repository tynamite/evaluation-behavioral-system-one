"""The pick-a-number comparison: Jev read two ways, a chat model, and people."""

from __future__ import annotations

import pandas as pd
import pytest

from jevbench.pick_number import NUMBERS, YOUGOV_PERCENT, human, summarise


def _jev(probs: dict[str, float], value: str) -> dict:
    return {"arm": "jev", "model": "jev-1.13.0", "persona": "neutral", "error": None,
            "probabilities": probs, "value": value}  # fmt: skip


def test_jev_is_read_two_ways_and_the_chat_model_once() -> None:
    a = {"7": 0.6, "5": 0.4}
    b = {"7": 0.2, "3": 0.8}
    chat = [{"arm": "baseline", "model": "haiku", "persona": "neutral", "error": None,
             "probabilities": {}, "value": v} for v in ("7", "7", "3", None)]  # fmt: skip
    rows = {r["source"]: r for r in summarise(pd.DataFrame([_jev(a, "7"), _jev(b, "3"), *chat]))}
    dist = rows["Jev 1.13, its distribution"]
    assert dist["7"] == pytest.approx(0.4) and dist["3"] == pytest.approx(0.4)
    picks = rows["Jev 1.13, one pick per call"]
    assert picks["7"] == pytest.approx(0.5) and picks["n"] == 2
    # An unread chat reply is left out, not counted as a number.
    chat_row = rows["Haiku, one pick per call"]  # named from the model id "haiku"
    assert chat_row["n"] == 3 and chat_row["7"] == pytest.approx(2 / 3)


def test_human_reference_is_yougov_normalised() -> None:
    h = human()
    assert list(h) == NUMBERS
    assert sum(h.values()) == pytest.approx(1.0)
    assert sum(YOUGOV_PERCENT.values()) == 101  # published, rounded
    assert max(h, key=h.get) == "7"


def test_chat_name_comes_from_the_model() -> None:
    from jevbench.pick_number import chat_name

    assert chat_name("anthropic/claude-haiku-5.5") == "Claude Haiku 5.5"
    assert chat_name("openai/gpt-6-luna") == "Gpt 6 Luna"


def test_analyse_refuses_more_than_one_run_per_arm(tmp_path) -> None:
    import json

    from jevbench.pick_number import analyse

    base = {"probe_id": "pick_number_1_10", "instrument": "pick_number", "backend": "x",
            "kind": "choice", "value": "7", "probabilities": {"7": 1.0}, "error": None}  # fmt: skip
    jev = [{**base, "arm": "jev", "model": "jev-1.13.0", "persona": p, "replicate": r}
           for p in ("neutral", "typical_human") for r in range(2)]  # fmt: skip
    chat = [{**base, "arm": "baseline", "model": "anthropic/claude-haiku-5.5", "persona": p,
             "replicate": r} for p in ("neutral", "typical_human") for r in range(2)]  # fmt: skip
    # The same System One model twice, as a rerun left in the folder would be.
    for name in ("run_live_A_jev.jsonl", "run_live_B_jev.jsonl"):
        (tmp_path / name).write_text("".join(json.dumps(r) + "\n" for r in jev))
    (tmp_path / "run_live_C_chat.jsonl").write_text("".join(json.dumps(r) + "\n" for r in chat))
    with pytest.raises(ValueError, match="each System One model once"):
        analyse(tmp_path, tmp_path / "out")


def test_analyse_refuses_two_models_in_one_run(tmp_path) -> None:
    import json

    from jevbench.pick_number import analyse

    base = {"probe_id": "pick_number_1_10", "instrument": "pick_number", "persona": "neutral",
            "replicate": 0, "backend": "x", "kind": "choice", "value": "7",
            "probabilities": {"7": 1.0}, "error": None}  # fmt: skip
    jev = [{**base, "arm": "jev", "model": m} for m in ("jev-1.13.0", "jev-1.14.0")]
    chat = [{**base, "arm": "baseline", "model": "anthropic/claude-haiku-5.5"}]
    (tmp_path / "run_live_A_jev.jsonl").write_text("".join(json.dumps(r) + "\n" for r in jev))
    (tmp_path / "run_live_B_chat.jsonl").write_text("".join(json.dumps(r) + "\n" for r in chat))
    with pytest.raises(ValueError, match="not one of each"):
        analyse(tmp_path, tmp_path / "out")


def test_analyse_refuses_an_interrupted_run(tmp_path) -> None:
    import json

    from jevbench.pick_number import analyse

    base = {"probe_id": "pick_number_1_10", "instrument": "pick_number", "backend": "x",
            "kind": "choice", "value": "7", "probabilities": {"7": 1.0}, "error": None}  # fmt: skip
    jev = [{**base, "arm": "jev", "model": "jev-1.13.0", "persona": p, "replicate": r}
           for p in ("neutral", "typical_human") for r in range(3)]  # fmt: skip
    jev = jev[:-1]  # typical_human stopped one call short
    chat = [{**base, "arm": "baseline", "model": "anthropic/claude-haiku-5.5", "persona": p,
             "replicate": r} for p in ("neutral", "typical_human") for r in range(3)]  # fmt: skip
    (tmp_path / "run_live_A_jev.jsonl").write_text("".join(json.dumps(r) + "\n" for r in jev))
    (tmp_path / "run_live_B_chat.jsonl").write_text("".join(json.dumps(r) + "\n" for r in chat))
    with pytest.raises(ValueError, match="incomplete or uneven"):
        analyse(tmp_path, tmp_path / "out")


def test_analyse_refuses_a_prompt_with_no_usable_answers(tmp_path) -> None:
    import json

    from jevbench.pick_number import analyse

    base = {"probe_id": "pick_number_1_10", "instrument": "pick_number", "backend": "x",
            "kind": "choice", "value": "7", "probabilities": {"7": 1.0}, "error": None}  # fmt: skip
    jev = [{**base, "arm": "jev", "model": "jev-1.13.0", "persona": p, "replicate": r}
           for p in ("neutral", "typical_human") for r in range(2)]  # fmt: skip
    for r in jev[2:]:
        r.update(error="unusable answer: bad", probabilities={}, value=None)
    chat = [{**base, "arm": "baseline", "model": "anthropic/claude-haiku-5.5", "persona": p,
             "replicate": r} for p in ("neutral", "typical_human") for r in range(2)]  # fmt: skip
    (tmp_path / "run_live_A_jev.jsonl").write_text("".join(json.dumps(r) + "\n" for r in jev))
    (tmp_path / "run_live_B_chat.jsonl").write_text("".join(json.dumps(r) + "\n" for r in chat))
    with pytest.raises(ValueError, match="no usable answers"):
        analyse(tmp_path, tmp_path / "out")


def test_analyse_refuses_a_run_with_no_usable_jev_answers_at_all(tmp_path) -> None:
    import json

    from jevbench.pick_number import analyse

    base = {"probe_id": "pick_number_1_10", "instrument": "pick_number", "backend": "x",
            "kind": "choice", "value": "7", "probabilities": {"7": 1.0}, "error": None}  # fmt: skip
    jev = [{**base, "arm": "jev", "model": "jev-1.13.0", "persona": p, "replicate": r,
            "error": "unusable answer: bad", "probabilities": {}, "value": None}
           for p in ("neutral", "typical_human") for r in range(2)]  # fmt: skip
    chat = [{**base, "arm": "baseline", "model": "anthropic/claude-haiku-5.5", "persona": p,
             "replicate": r} for p in ("neutral", "typical_human") for r in range(2)]  # fmt: skip
    (tmp_path / "run_live_A_jev.jsonl").write_text("".join(json.dumps(r) + "\n" for r in jev))
    (tmp_path / "run_live_B_chat.jsonl").write_text("".join(json.dumps(r) + "\n" for r in chat))
    with pytest.raises(ValueError, match="no usable answers"):
        analyse(tmp_path, tmp_path / "out")


def test_resume_refuses_a_file_from_the_other_arm(tmp_path, capsys) -> None:
    import json

    from jevbench.cli import main

    rec = {"probe_id": "pick_number_1_10", "instrument": "pick_number", "persona": "neutral",
           "arm": "baseline", "replicate": 0, "backend": "openrouter",
           "model": "anthropic/claude-haiku-5.5",
           "kind": "choice", "value": "7", "probabilities": {}, "error": None}  # fmt: skip
    path = tmp_path / "run_live_x.jsonl"
    path.write_text(json.dumps(rec) + "\n")
    assert main(["pick-number", "run", "--replicates", "1", "--resume", str(path)]) == 1
    assert "holds arm baseline, not jev" in capsys.readouterr().err
    assert path.read_text().count("\n") == 1  # untouched


def test_same_model_allows_a_version_suffix_only() -> None:
    from jevbench.pick_number import same_model

    assert same_model("upstage/solar-decide", "upstage/solar-decide-20260928")
    assert same_model("typesafe/jev-1.13", "jev-1.13.0")
    assert same_model("anthropic/claude-haiku-5.5", "anthropic/claude-haiku-5.5")
    assert not same_model("upstage/solar-decide", "upstage/solar-decide-flash-20261008")
    assert not same_model("anthropic/claude-haiku-5.5", "anthropic/claude-sonnet-5.5")
    # Same model name under another provider is another model.
    assert not same_model("other/claude-haiku-5.5", "anthropic/claude-haiku-5.5")


def test_resume_refuses_a_file_from_another_model(tmp_path, capsys) -> None:
    import json

    from jevbench.cli import main

    rec = {"probe_id": "pick_number_1_10", "instrument": "pick_number", "persona": "neutral",
           "arm": "baseline", "replicate": 0, "backend": "openrouter",
           "model": "anthropic/claude-haiku-5.5", "kind": "choice", "value": "7",
           "probabilities": {}, "error": None}  # fmt: skip
    path = tmp_path / "run_live_x.jsonl"
    path.write_text(json.dumps(rec) + "\n")
    argv = ["pick-number", "run", "--backend", "openrouter", "--baseline-samples", "2",
            "--baseline-model", "anthropic/claude-sonnet-5.5", "--resume", str(path)]  # fmt: skip
    assert main(argv) == 1
    assert "holds model anthropic/claude-haiku-5.5" in capsys.readouterr().err
    assert path.read_text().count("\n") == 1


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"probe_id": "dictator"}, "holds probe_id dictator"),
        ({"backend": "typesafe"}, "holds backend typesafe"),
    ],
)
def test_resume_refuses_another_probe_or_backend(tmp_path, change, message) -> None:
    import json

    from jevbench.pick_number import resume_problem

    rec = {"probe_id": "pick_number_1_10", "instrument": "pick_number", "persona": "neutral",
           "arm": "jev", "replicate": 0, "backend": "openrouter", "model": "jev-1.13.0",
           "kind": "choice", "value": "7", "probabilities": {"7": 1.0}, "error": None}  # fmt: skip
    path = tmp_path / "run_live_x.jsonl"
    path.write_text(json.dumps(rec) + "\n")
    ok = {"arm": "jev", "model": "typesafe/jev-1.13", "backend": "openrouter"}
    assert resume_problem(path, **ok) is None
    path.write_text(json.dumps({**rec, **change}) + "\n")
    assert message in (resume_problem(path, **ok) or "")


def test_analyse_keeps_two_jev_versions_apart(tmp_path) -> None:
    import json

    from jevbench.pick_number import analyse

    base = {"probe_id": "pick_number_1_10", "instrument": "pick_number", "backend": "x",
            "kind": "choice", "value": "7", "probabilities": {"7": 1.0}, "error": None}  # fmt: skip
    grid = [("neutral", r) for r in range(2)] + [("typical_human", r) for r in range(2)]

    def write(runs: dict[str, tuple[str, str]]) -> None:
        for f in tmp_path.glob("run_live_*"):
            f.unlink()
        for name, (arm, model) in runs.items():
            rows = [{**base, "arm": arm, "model": model, "persona": p, "replicate": r}
                    for p, r in grid]  # fmt: skip
            (tmp_path / f"run_live_{name}.jsonl").write_text(
                "".join(json.dumps(r) + "\n" for r in rows)
            )

    chat = ("baseline", "anthropic/claude-haiku-5.5")
    write({"A": ("jev", "jev-1.13.0"), "B": ("jev", "jev-1.14.0"), "C": chat})
    sources = set(analyse(tmp_path, tmp_path / "out")["source"])
    assert {"Jev 1.13, its distribution", "Jev 1.14, its distribution"} <= sources
    # The same version twice (direct and through OpenRouter) would share a label.
    write({"A": ("jev", "jev-1.13.0"), "B": ("jev", "typesafe/jev-1.13-20260917"), "C": chat})
    with pytest.raises(ValueError, match="named alike"):
        analyse(tmp_path, tmp_path / "out")


def test_same_model_never_matches_a_jev_alias() -> None:
    from jevbench.pick_number import same_model

    # An alias may move to another version, so it never matches a file's records.
    assert not same_model("jev-preview", "jev-1.14.0")
    assert not same_model("jev-latest", "jev-1.13.0")


def test_analyse_refuses_another_probe(tmp_path) -> None:
    import json

    from jevbench.pick_number import analyse

    base = {"instrument": "pick_number", "backend": "x", "kind": "choice", "value": "7",
            "probabilities": {"7": 1.0}, "error": None}  # fmt: skip
    grid = [(p, r) for p in ("neutral", "typical_human") for r in range(2)]
    runs = {"A": ("jev", "jev-1.13.0", "pick_number_1_10"),
            "B": ("baseline", "anthropic/claude-haiku-5.5", "dictator")}  # fmt: skip
    for name, (arm, model, probe) in runs.items():
        rows = [{**base, "probe_id": probe, "arm": arm, "model": model, "persona": p,
                 "replicate": r} for p, r in grid]  # fmt: skip
        (tmp_path / f"run_live_{name}.jsonl").write_text(
            "".join(json.dumps(r) + "\n" for r in rows)
        )
    with pytest.raises(ValueError, match="holds probes"):
        analyse(tmp_path, tmp_path / "out")


def test_pick_number_figures_follow_the_house_rules() -> None:
    import re

    from jevbench.diagrams import JEV_PINK, pick_number_figures
    from jevbench.pick_number import PICK_RESULTS_DIR, system_one_name

    table = pd.read_csv(PICK_RESULTS_DIR / "distributions.csv", dtype={"persona": str})
    table["persona"] = table["persona"].fillna("")
    figures = pick_number_figures(table)
    models = sorted(set(table.loc[table["arm"] == "jev", "model"]))
    slugs = [f.slug for f in figures]
    assert len(slugs) == len(set(slugs))
    # Every System One model is drawn in exactly one group, under its own name;
    # every Jev is named with its version.
    reading = [f for f in figures if f.slug.startswith("pick-number-reading-")]
    drawn = [n for f in reading for n in re.findall(r'font-weight="600">([^<]+)</text>', f.body)]
    assert sorted(drawn) == sorted(system_one_name(m) for m in models)
    assert all(n != "Jev" for n in drawn)
    for f in figures:
        page = f.html()
        assert f'aria-labelledby="{f.slug}-title {f.slug}-desc"' in page
        if "jev" in f.desc.lower() or "Jev" in f.body:
            assert JEV_PINK in f.body


def test_resume_through_an_alias_names_the_version_to_use(tmp_path) -> None:
    import json

    from jevbench.pick_number import resume_problem

    rec = {"probe_id": "pick_number_1_10", "instrument": "pick_number", "persona": "neutral",
           "arm": "jev", "replicate": 0, "backend": "typesafe", "model": "jev-1.14.0",
           "kind": "choice", "value": "7", "probabilities": {"7": 1.0}, "error": None}  # fmt: skip
    path = tmp_path / "run_live_x.jsonl"
    path.write_text(json.dumps(rec) + "\n")
    problem = resume_problem(path, arm="jev", model="jev-preview", backend="typesafe")
    assert problem and "--model jev-1.14.0" in problem


def test_each_reply_counts_equally_in_the_mean() -> None:
    # One reply sums to 0.5 (all on 7), one to 1.0 (all on 3): equal weight.
    rows = summarise(pd.DataFrame([_jev({"7": 0.5}, "7"), _jev({"3": 1.0}, "3")]))
    dist = next(r for r in rows if r["source"].endswith("its distribution"))
    assert dist["7"] == pytest.approx(0.5) and dist["3"] == pytest.approx(0.5)


def test_resume_accepts_an_empty_file(tmp_path) -> None:
    from jevbench.pick_number import resume_problem

    path = tmp_path / "run_live_x.jsonl"
    path.write_text("")
    assert resume_problem(path, arm="jev", model="jev-1.14.0", backend="typesafe") is None


def test_pick_number_figures_draw_any_number_of_jev_versions_and_count_the_chat_model() -> None:
    from jevbench.diagrams import fig_pick_number_jev
    from jevbench.pick_number import PICK_RESULTS_DIR

    table = pd.read_csv(PICK_RESULTS_DIR / "distributions.csv", dtype={"persona": str})
    table["persona"] = table["persona"].fillna("")
    jev = table[table["model"] == "jev-1.14.0"].copy()
    jev["model"] = "jev-1.15.0"
    jev["source"] = jev["source"].str.replace("Jev 1.14", "Jev 1.15")
    # The chat model varies under one prompt: the figure must say so.
    chat = (table["arm"] == "baseline") & (table["persona"] == "typical_human")
    table.loc[chat, ["7", "3"]] = [0.9, 0.1]
    fig = fig_pick_number_jev(pd.concat([table, jev], ignore_index=True))
    assert "Jev 1.15" in fig.body and "Jev 1.13" in fig.body
    assert "7 in 90 of 100 calls" in fig.subtitle and "said 7 every time" not in fig.subtitle


def test_resume_ignores_failed_calls_the_runner_will_retry(tmp_path) -> None:
    import json

    from jevbench.pick_number import resume_problem

    ok = {"probe_id": "pick_number_1_10", "instrument": "pick_number", "persona": "neutral",
          "arm": "jev", "replicate": 0, "backend": "typesafe", "model": "jev-1.14.0",
          "kind": "choice", "value": "7", "probabilities": {"7": 1.0}, "error": None}  # fmt: skip
    failed = {**ok, "replicate": 1, "model": "jev-preview", "value": None, "probabilities": {},
              "error": "HTTP 503"}  # fmt: skip
    path = tmp_path / "run_live_x.jsonl"
    path.write_text(json.dumps(ok) + "\n" + json.dumps(failed) + "\n")
    assert resume_problem(path, arm="jev", model="jev-1.14.0", backend="typesafe") is None


def test_pick_number_figures_count_calls_from_the_table() -> None:
    from jevbench.diagrams import pick_number_figures
    from jevbench.pick_number import PICK_RESULTS_DIR

    table = pd.read_csv(PICK_RESULTS_DIR / "distributions.csv", dtype={"persona": str})
    table["persona"] = table["persona"].fillna("")
    table.loc[table["arm"] != "people", "n"] = 40
    for f in pick_number_figures(table):
        assert "100 calls" not in f.body + f.source and "100 returned" not in f.source, f.slug


def test_analyse_skips_an_empty_run_file(tmp_path) -> None:
    import json

    from jevbench.pick_number import analyse

    base = {"probe_id": "pick_number_1_10", "instrument": "pick_number", "backend": "x",
            "kind": "choice", "value": "7", "probabilities": {"7": 1.0}, "error": None}  # fmt: skip
    grid = [(p, r) for p in ("neutral", "typical_human") for r in range(2)]
    for name, (arm, model) in {"A": ("jev", "jev-1.13.0"),
                               "B": ("baseline", "anthropic/claude-haiku-5.5")}.items():  # fmt: skip
        rows = [{**base, "arm": arm, "model": model, "persona": p, "replicate": r} for p, r in grid]
        (tmp_path / f"run_live_{name}.jsonl").write_text(
            "".join(json.dumps(r) + "\n" for r in rows)
        )
    (tmp_path / "run_live_C.jsonl").write_text("")
    assert len(analyse(tmp_path, tmp_path / "out"))


def test_pick_number_build_removes_figures_it_no_longer_draws(tmp_path) -> None:
    from jevbench.diagrams import build_pick_number_diagrams
    from jevbench.pick_number import PICK_RESULTS_DIR

    table = pd.read_csv(PICK_RESULTS_DIR / "distributions.csv", dtype={"persona": str})
    table["persona"] = table["persona"].fillna("")
    html, png = tmp_path / "html", tmp_path / "png"
    png.mkdir()
    build_pick_number_diagrams(table, html, png)
    (png / "pick-number-models-b.png").write_bytes(b"x")
    # Keep only Jev and the main models: no second group.
    keep = ["jev-1.13.0", "jev-1.14.0", "cloudflare/clef", "liquid/d1-20260930",
            "openai/gpt-6-luna-decisions-20261006"]  # fmt: skip
    table = table[(table["arm"] != "jev") | table["model"].isin(keep)]
    build_pick_number_diagrams(table, html, png)
    assert not list(html.glob("pick-number-*-b.html")) and not list(png.glob("*-b.png"))


@pytest.mark.parametrize("keep", [1, 3, 6, 8])
def test_pick_number_figures_draw_any_number_of_models(keep: int) -> None:
    from jevbench.diagrams import pick_number_figures
    from jevbench.pick_number import PICK_RESULTS_DIR

    table = pd.read_csv(PICK_RESULTS_DIR / "distributions.csv", dtype={"persona": str})
    table["persona"] = table["persona"].fillna("")
    # Jev first, then by name: the same selection on every machine.
    models = sorted(
        set(table.loc[table["arm"] == "jev", "model"]), key=lambda m: ("jev" not in m, m)
    )
    table = table[(table["arm"] != "jev") | table["model"].isin(models[:keep])]
    slugs = [f.slug for f in pick_number_figures(table)]
    assert "pick-number-jev" in slugs and "pick-number-models-a" in slugs
    assert ("pick-number-reading-a" in slugs) == (keep >= 4)
