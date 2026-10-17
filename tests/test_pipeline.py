"""End-to-end on the offline simulator: no key, no network, fully deterministic."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pandas as pd
import pytest

from jevbench.analysis import analyse_run, load_records
from jevbench.compare import compare_runs
from jevbench.config import Config, redact
from jevbench.instruments import all_probes
from jevbench.runner import run_battery
from jevbench.schema import Choice, Noul, Score
from jevbench.simulator import SimulatorClient


def test_simulator_is_deterministic() -> None:
    q = {"q": Choice(instructions="Pick.", criteria={"a": "A", "b": "B"})}
    a = SimulatorClient().decide({"s": 1}, q).answers["q"].probabilities
    b = SimulatorClient().decide({"s": 1}, q).answers["q"].probabilities
    assert a == b


def test_simulator_distributions_are_normalised() -> None:
    client = SimulatorClient()
    resp = client.decide(
        {"s": 1},
        {
            "c": Choice(instructions="Pick.", criteria={"a": "A", "b": "B", "c": "C"}),
            "s": Score(instructions="Rate.", criteria=["lo", "mid", "hi"]),
            "n": Noul(instructions="Claim."),
        },
    )
    for qid in ("c", "s"):
        assert sum(resp.answers[qid].probabilities.values()) == pytest.approx(1.0, abs=1e-3)
    assert 0.0 <= float(resp.answers["n"].value) <= 1.0


def test_full_pipeline_runs_offline(tmp_path: Path) -> None:
    cfg = Config.from_env(backend="simulator")
    path = run_battery(
        cfg,
        modules=["crt", "reasoning"],
        replicates=2,
        personas=["neutral", "typical_human"],
        out_dir=tmp_path,
    )
    df = load_records(path)
    n_probes = len(all_probes(["crt", "reasoning"]))
    assert len(df) == n_probes * 2 * 2
    assert df["error"].isna().all()
    summary = analyse_run(path, tmp_path / "tables")
    assert summary["n_errors"] == 0
    assert summary["backend"] == ["simulator"]
    assert (tmp_path / "tables" / "statistics.csv").exists()
    assert summary["n_statistics"] > 0


def test_run_filename_marks_simulated_data(tmp_path: Path) -> None:
    cfg = Config.from_env(backend="simulator")
    path = run_battery(cfg, modules=["crt"], replicates=1, personas=["neutral"], out_dir=tmp_path)
    assert "simulated" in path.name, "simulated output must be distinguishable on disk"


def test_redact_hides_a_key() -> None:
    secret = "sk-or-v1-EXAMPLE_FAKE_VALUE_FOR_TESTS_ONLY"
    assert secret not in redact(f"HTTP 401 for key {secret}", secret)
    assert "REDACTED" in redact(f"key {secret}", secret)


def test_redact_is_safe_with_no_secret() -> None:
    assert redact("plain text", None) == "plain text"
    assert redact("plain text", "") == "plain text"


def test_missing_key_raises_a_helpful_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    cfg = Config(backend="openrouter", api_key=None)
    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY is not set"):
        cfg.require_key()


def test_run_filename_names_the_model(tmp_path: Path) -> None:
    cfg = replace(Config.from_env(backend="simulator"), model="liquid/d1")
    path = run_battery(cfg, modules=["crt"], replicates=1, personas=["neutral"], out_dir=tmp_path)
    assert path.name.endswith("_liquid--d1.jsonl")
    assert "simulated" in path.name


def test_zero_runs_refuses_to_write_an_empty_file(tmp_path: Path) -> None:
    cfg = Config.from_env(backend="simulator")
    with pytest.raises(RuntimeError, match="nothing to run"):
        run_battery(cfg, modules=["crt"], replicates=0, personas=["neutral"], out_dir=tmp_path)


def _two_simulated_runs(tmp_path: Path) -> list[Path]:
    base = Config.from_env(backend="simulator")
    return [
        run_battery(
            replace(base, model=m),
            modules=["crt", "decision", "games"],
            replicates=1,
            personas=["neutral", "typical_human"],
            out_dir=tmp_path,
        )
        for m in ("typesafe/jev-1.13", "liquid/d1")
    ]


def test_compare_keys_each_model_by_its_served_name(tmp_path: Path) -> None:
    paths = _two_simulated_runs(tmp_path)
    tables = compare_runs(paths, tmp_path / "cmp")
    assert set(tables["health"]["model"]) == {
        "simulator-v1[typesafe/jev-1.13]",
        "simulator-v1[liquid/d1]",
    }
    assert set(tables["fidelity"]["model"]) == set(tables["health"]["model"])
    assert {"simulator-v1[liquid/d1]", "human"} <= set(tables["measures"].columns)
    for name in ("health.csv", "fidelity.csv", "measures.csv", "statistics.csv"):
        assert (tmp_path / "cmp" / name).exists()


def test_compare_refuses_the_same_model_twice(tmp_path: Path) -> None:
    path = _two_simulated_runs(tmp_path)[0]
    with pytest.raises(ValueError, match="appears in both"):
        compare_runs([path, path], tmp_path / "cmp")


def test_resume_finishes_an_interrupted_run_without_duplicates(tmp_path: Path) -> None:
    cfg = Config.from_env(backend="simulator")
    kwargs = {"modules": ["crt"], "replicates": 2, "personas": ["neutral"], "out_dir": tmp_path}
    path = run_battery(cfg, **kwargs)  # type: ignore[arg-type]
    full = path.read_text().splitlines()

    # Keep the first half, as if the process had been killed, and turn one of
    # the kept records into a failure that resuming should retry.
    half = full[: len(full) // 2]
    failed = json.loads(half[0])
    failed["error"] = "retryable status 502"
    path.write_text("\n".join([json.dumps(failed), *half[1:]]) + "\n")

    run_battery(cfg, resume=path, **kwargs)  # type: ignore[arg-type]
    df = load_records(path)
    assert len(df) == len(full)
    assert df["error"].isna().all()
    assert not df.duplicated(["arm", "probe_id", "persona", "replicate"]).any()


def test_proportion_items_are_flagged() -> None:
    probes = {p.probe_id: p for p in all_probes(None)}
    proportion = {pid for pid, p in probes.items() if p.meta.get("asks_for") == "proportion"}
    assert len(proportion) == 21
    assert all(probes[pid].question.kind == "noul" for pid in proportion)
    # Linda's statements are truth claims, which a true/false reply can answer.
    assert probes["conjunction_p_single"].meta["asks_for"] == "truth"


def test_chat_replies_are_reread_and_proportion_items_left_unscored(tmp_path: Path) -> None:
    base = {
        "instrument": "x",
        "arm": "baseline",
        "replicate": 0,
        "backend": "openrouter",
        "model": "chat",
        "persona": "neutral",
        "error": None,
    }
    rows = [
        # Stored answer from an older parser; the raw text says $1.
        {
            **base,
            "probe_id": "ultimatum_offer",
            "kind": "choice",
            "value": "$9",
            "meta": {"raw_text": "$1: Offer $1, keep $9"},
        },
        {
            **base,
            "probe_id": "trolley_push_estimate",
            "kind": "noul",
            "value": "false",
            "meta": {"raw_text": "false"},
        },
    ]
    path = tmp_path / "run_live_x.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    df = load_records(path).set_index("probe_id")
    assert df.loc["ultimatum_offer", "value"] == "$1"
    assert pd.isna(df.loc["trolley_push_estimate", "value"])
    assert bool(df.loc["trolley_push_estimate", "not_measurable"])
    assert not bool(df.loc["ultimatum_offer", "not_measurable"])


def test_analysis_summary_counts_unmeasurable_apart_from_unparsed(tmp_path: Path) -> None:
    base = {
        "instrument": "x",
        "arm": "baseline",
        "replicate": 0,
        "backend": "openrouter",
        "model": "chat",
        "persona": "neutral",
        "error": None,
        "usage": {},
    }
    rows = [
        {
            **base,
            "probe_id": "trolley_push_estimate",
            "kind": "noul",
            "value": "false",
            "meta": {"raw_text": "false"},
        },
        {
            **base,
            "probe_id": "ultimatum_offer",
            "kind": "choice",
            "value": None,
            "meta": {"raw_text": "no idea"},
        },
    ]
    path = tmp_path / "run_live_x.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    summary = analyse_run(path, tmp_path / "out")
    assert summary["n_baseline_not_measurable"] == 1
    assert summary["n_baseline_unparsed"] == 1
    assert summary["baseline_cells"] == 1


def test_simulated_run_never_writes_over_committed_results() -> None:
    from jevbench.cli import _default_out
    from jevbench.config import FIGURES_DIR, TABLES_DIR

    sim = Path("data/raw/run_simulated_20260101T000000Z.jsonl")
    live = Path("data/raw/run_live_20260918T230710Z.jsonl")
    assert _default_out(sim, TABLES_DIR) == TABLES_DIR.parent / "simulated" / "tables"
    assert _default_out(sim, FIGURES_DIR) == FIGURES_DIR.parent / "simulated" / "figures"
    assert _default_out(live, TABLES_DIR) == TABLES_DIR


def test_committed_outputs_never_read_a_simulated_run(tmp_path: Path) -> None:
    from jevbench.analysis import primary_run

    (
        tmp_path / "run_live_20261012T225915Z_typesafe--jev-1.13+anthropic--claude-sonnet-5.5.jsonl"
    ).touch()
    (tmp_path / "run_live_20261012T225927Z_cloudflare--clef.jsonl").touch()
    (tmp_path / "run_simulated_20261013T094732Z_typesafe--jev-1.13.jsonl").touch()
    # analyse and figures take the newest Jev run, simulated or not (their
    # output for a simulated run goes to results/simulated/)...
    assert "simulated" in primary_run(tmp_path).name  # type: ignore[union-attr]
    # ...but anything that writes committed files takes the newest live one.
    newest_live = primary_run(tmp_path, live_only=True)
    assert newest_live is not None and newest_live.name.startswith("run_live_20261012T225915Z")


def test_committed_outputs_need_a_live_jev_run(tmp_path: Path) -> None:
    from jevbench.analysis import primary_run

    # Another model's live run must never stand in for Jev's.
    (tmp_path / "run_live_20261012T225927Z_cloudflare--clef.jsonl").touch()
    (tmp_path / "run_simulated_20261013T094732Z_typesafe--jev-1.13.jsonl").touch()
    assert primary_run(tmp_path, live_only=True) is None


def test_primary_run_recognises_jev_under_either_backend(tmp_path: Path) -> None:
    from jevbench.analysis import primary_run

    (tmp_path / "run_live_20261012T225927Z_cloudflare--clef.jsonl").touch()
    native = tmp_path / "run_live_20261013T120000Z_jev-1.13.0.jsonl"
    native.touch()
    # The native TypeSafe backend's slug has no "typesafe--" prefix.
    assert primary_run(tmp_path, live_only=True) == native
    assert primary_run(tmp_path) == native


def test_analyse_removes_a_stale_h4_table(tmp_path: Path) -> None:
    from jevbench.analysis import analyse_run
    from jevbench.config import Config
    from jevbench.runner import run_battery

    out = tmp_path / "tables"
    out.mkdir()
    (out / "followup_h4.csv").write_text("left over from another run\n")
    path = run_battery(
        Config.from_env(backend="simulator"),
        modules=["crt"],
        replicates=1,
        baseline_samples=0,
        out_dir=tmp_path / "raw",
    )
    analyse_run(path, out)
    assert not (out / "followup_h4.csv").exists()


def test_h4_pairs_the_reused_items_with_their_estimates(tmp_path: Path) -> None:
    """The six items reused from the first project enter H4 beside the new ones."""
    from dataclasses import asdict

    import pandas as pd

    from jevbench.analysis import compute_stats, simulate_vs_estimate

    cfg = Config.from_env(backend="simulator")
    path = run_battery(
        cfg,
        modules=["crt", "decision", "followup"],
        replicates=1,
        personas=["neutral", "typical_human"],
        out_dir=tmp_path,
    )
    sdf = pd.DataFrame([asdict(s) for s in compute_stats(load_records(path))])
    table = simulate_vs_estimate(sdf)
    pairs = set(zip(table["instrument"], table["statistic"], strict=True))
    assert {
        ("allais", "prob_certain_pair1"),
        ("allais", "prob_safer_pair2"),
        ("base_rate", "prob_correct_band"),
        ("conjunction", "prob_fallacy_forced_choice"),
        ("crt", "proportion_correct"),
        ("framing", "prob_certain_gain_frame"),
        ("framing", "prob_certain_loss_frame"),
        ("sunk_cost", "prob_continue"),
    } <= pairs
    assert len(pairs) == 23


def test_crt_scores_ignore_the_crt_population_questions(tmp_path: Path) -> None:
    """`crt_*_estimate` probes share the CRT prefix but are not CRT items."""
    from dataclasses import asdict

    import pandas as pd

    from jevbench.analysis import compute_stats

    cfg = Config.from_env(backend="simulator")

    def crt_stats(modules: list[str]) -> pd.DataFrame:
        path = run_battery(
            cfg, modules=modules, replicates=1, personas=["neutral"], out_dir=tmp_path / modules[-1]
        )
        sdf = pd.DataFrame([asdict(s) for s in compute_stats(load_records(path))])
        return sdf[sdf.instrument == "crt"].set_index("statistic")["value"]

    pd.testing.assert_series_equal(crt_stats(["crt"]), crt_stats(["crt", "followup"]))


def test_crt_estimate_needs_all_three_frederick_items(tmp_path: Path) -> None:
    """A refused CRT population question drops the pair rather than averaging fewer items."""
    from dataclasses import asdict

    import pandas as pd

    from jevbench.analysis import compute_stats

    cfg = Config.from_env(backend="simulator")
    path = run_battery(
        cfg, modules=["crt", "followup"], replicates=1, personas=["neutral"], out_dir=tmp_path
    )
    df = load_records(path)

    def has_crt_estimate(records: pd.DataFrame) -> bool:
        sdf = pd.DataFrame([asdict(s) for s in compute_stats(records)])
        return bool((sdf.instrument == "crt_estimate").any())

    assert has_crt_estimate(df)
    assert not has_crt_estimate(df[df.probe_id != "crt_widgets_estimate"])


def test_runner_records_an_answer_on_unknown_options_as_an_error() -> None:
    """A reply that puts probability on keys the question never offered is not used."""
    from jevbench.instruments import all_probes
    from jevbench.runner import BatteryRunner
    from jevbench.schema import DecisionResponse

    class Stub:
        def decide(self, state: object, questions: object) -> DecisionResponse:
            return DecisionResponse.parse(
                {
                    "model": "stub",
                    "usage": {"cost": 0.01},
                    "answers": {
                        "answer": {"type": "choice", "choice": "zz", "probabilities": {"zz": 1.0}}
                    },
                }
            )

    probe = next(p for p in all_probes(["crt"]))
    runner = BatteryRunner(Config.from_env(backend="simulator"), replicates=1)
    rec = runner._one_jev(Stub(), probe, "neutral", 0)
    assert rec.error and "not options" in rec.error
    # The call was served and billed: its model and cost are kept.
    assert rec.model == "stub" and rec.usage == {"cost": 0.01}
    assert rec.probabilities == {} and rec.value is None


def test_runner_records_a_noul_outside_the_unit_interval_as_an_error() -> None:
    from jevbench.instruments import all_probes
    from jevbench.runner import BatteryRunner
    from jevbench.schema import DecisionResponse, Noul

    class Stub:
        def decide(self, state: object, questions: object) -> DecisionResponse:
            return DecisionResponse.parse(
                {"model": "stub", "answers": {"answer": {"type": "noul", "noul": 1.5}}}
            )

    probe = next(p for p in all_probes() if isinstance(p.question, Noul))
    rec = BatteryRunner(Config.from_env(backend="simulator"), replicates=1)._one_jev(
        Stub(), probe, "neutral", 0
    )
    assert rec.error and "outside [0, 1]" in rec.error


def test_resume_keeps_a_billed_but_unusable_reply(tmp_path: Path) -> None:
    """Resuming does not drop, or pay again for, a reply that was served and rejected."""
    from jevbench.runner import UNUSABLE

    cfg = Config.from_env(backend="simulator")
    kwargs = {"modules": ["crt"], "replicates": 2, "personas": ["neutral"], "out_dir": tmp_path}
    path = run_battery(cfg, **kwargs)  # type: ignore[arg-type]
    lines = path.read_text().splitlines()
    rejected = json.loads(lines[0])
    rejected.update(error=f"{UNUSABLE}keys that are not options", usage={"cost": 0.01})
    path.write_text("\n".join([json.dumps(rejected), *lines[1:]]) + "\n")

    run_battery(cfg, resume=path, **kwargs)  # type: ignore[arg-type]
    records = [json.loads(line) for line in path.read_text().splitlines()]
    assert len(records) == len(lines)
    kept = [r for r in records if r.get("error")]
    assert len(kept) == 1 and kept[0]["usage"] == {"cost": 0.01}


def test_compare_names_a_direct_typesafe_run_and_where_it_lives(tmp_path: Path) -> None:
    """TypeSafe's own API serves `jev-1.14.0` with no provider; the comparison adds it,
    and records a run kept below data/raw/ by its path from there."""
    from jevbench.config import RAW_DIR

    run = RAW_DIR / "order_study" / "r1" / "run_live_20261014T231829Z_jev-1.14.0.jsonl"
    # A slice copied out of data/raw/ is recorded by its full path.
    sliced = tmp_path / run.name
    sliced.write_text(
        "".join(line for line in run.open() if '"instrument": "crt"' in line), encoding="utf-8"
    )
    health = compare_runs([sliced], tmp_path / "cmp")["health"]
    assert list(health["model"]) == ["typesafe/jev-1.14.0"]
    assert list(health["run_file"]) == [sliced.resolve().as_posix()]

    from jevbench.compare import _run_name

    assert _run_name(run) == f"order_study/r1/{run.name}"
    # TypeSafe's direct API reports tokens but no cost: unknown, not free.
    assert health["cost_usd"].isna().all()


def test_png_export_is_skipped_without_the_renderer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A base install has no Playwright: the figure's HTML stands, with a note."""
    import sys

    from jevbench.cli import _export_pngs

    monkeypatch.setitem(sys.modules, "playwright.sync_api", None)
    _export_pngs([tmp_path / "figure.html"])
    assert 'install `uv pip install -e ".[diagrams]"`' in capsys.readouterr().err


def _kept(probe_id: str, instrument: str, persona: str = "neutral", **extra: object) -> dict:
    return {
        "probe_id": probe_id,
        "instrument": instrument,
        "persona": persona,
        "arm": "jev",
        "replicate": 0,
        **extra,
    }


def test_resume_rejects_records_asked_before_the_item_index_was_removed() -> None:
    from jevbench.runner import resume_prompt_mismatch

    probes = all_probes()
    old_allais = _kept("allais_problem1", "allais")
    old_hl = _kept("holt_laury_03", "holt_laury")
    assert "allais_problem1" in (resume_prompt_mismatch([old_allais], probes) or "")
    assert "holt_laury_03" in (resume_prompt_mismatch([old_hl], probes) or "")
    # An old record of an item whose wording did not change is still resumable.
    assert resume_prompt_mismatch([_kept("crt_bat_ball", "crt")], probes) is None


def test_resume_checks_the_fingerprint_of_new_records() -> None:
    from jevbench.runner import prompt_fingerprint, resume_prompt_mismatch

    probes = all_probes()
    by_id = {p.probe_id: p for p in probes}
    p = by_id["allais_problem1"]
    good = _kept(p.probe_id, p.instrument, prompt_sha=prompt_fingerprint(p, "neutral", "jev"))
    assert resume_prompt_mismatch([good], probes) is None
    bad = {**good, "prompt_sha": "0" * 16}
    assert "other wording" in (resume_prompt_mismatch([bad], probes) or "")
    # Another persona is another prompt.
    assert prompt_fingerprint(p, "neutral", "jev") != prompt_fingerprint(p, "antisocial", "jev")


def test_new_records_carry_the_fingerprint_of_what_was_asked(tmp_path: Path) -> None:
    from jevbench.runner import prompt_fingerprint

    cfg = Config.from_env(backend="simulator")
    path = run_battery(
        cfg, modules=["decision"], replicates=1, personas=["neutral"], out_dir=tmp_path
    )
    by_id = {p.probe_id: p for p in all_probes()}
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    assert rows and all(
        r["prompt_sha"] == prompt_fingerprint(by_id[r["probe_id"]], r["persona"], r["arm"])
        for r in rows
    )


def test_resuming_an_old_run_of_a_changed_item_is_refused(tmp_path: Path) -> None:
    cfg = Config.from_env(backend="simulator")
    kwargs = {"modules": ["decision"], "replicates": 1, "personas": ["neutral"]}
    path = run_battery(cfg, out_dir=tmp_path, **kwargs)  # type: ignore[arg-type]
    # Make the file look like one from before records carried a fingerprint.
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    for r in rows:
        r.pop("prompt_sha", None)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    with pytest.raises(RuntimeError, match="asked before its wording changed"):
        run_battery(cfg, resume=path, **kwargs)  # type: ignore[arg-type]


def test_fingerprint_follows_each_arms_own_request() -> None:
    from dataclasses import replace

    from jevbench.runner import prompt_fingerprint
    from jevbench.schema import Noul

    p = next(p for p in all_probes() if p.probe_id == "allais_problem1")
    jev, chat = (
        prompt_fingerprint(p, "neutral", "jev"),
        prompt_fingerprint(p, "neutral", "baseline"),
    )
    assert jev != chat
    # The same instructions as another kind of question is another request, for both arms.
    as_noul = replace(p, question=Noul(instructions=p.question.instructions))
    assert prompt_fingerprint(as_noul, "neutral", "jev") != jev
    assert prompt_fingerprint(as_noul, "neutral", "baseline") != chat
    # A change to the state alone is another request too.
    with_x = replace(p, state={**(p.state or {}), "x": 1})
    assert prompt_fingerprint(with_x, "neutral", "jev") != jev
    assert prompt_fingerprint(with_x, "neutral", "baseline") != chat


def test_a_chat_only_format_change_leaves_system_one_fingerprints_alone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import jevbench.runner as runner

    p = next(p for p in all_probes() if p.probe_id == "allais_problem1")
    jev, chat = (
        runner.prompt_fingerprint(p, "neutral", "jev"),
        runner.prompt_fingerprint(p, "neutral", "baseline"),
    )
    real = runner.render_prompt
    monkeypatch.setattr(
        runner,
        "render_prompt",
        lambda probe: (real(probe)[0] + "\nAnswer briefly.", real(probe)[1]),
    )
    assert runner.prompt_fingerprint(p, "neutral", "jev") == jev
    assert runner.prompt_fingerprint(p, "neutral", "baseline") != chat


def test_fingerprint_notices_a_reordering_of_the_options() -> None:
    from dataclasses import replace

    from jevbench.runner import prompt_fingerprint
    from jevbench.schema import Choice

    p = next(p for p in all_probes() if p.probe_id == "allais_problem1")
    assert isinstance(p.question, Choice)
    flipped = replace(
        p,
        question=Choice(
            instructions=p.question.instructions,
            criteria=dict(reversed(list(p.question.criteria.items()))),
        ),
    )
    for arm in ("jev", "baseline"):
        assert prompt_fingerprint(flipped, "neutral", arm) != prompt_fingerprint(p, "neutral", arm)


def test_fingerprint_tells_an_empty_state_from_no_state() -> None:
    from dataclasses import replace

    from jevbench.runner import prompt_fingerprint

    p = next(p for p in all_probes() if p.probe_id == "allais_problem1")
    prints = {
        prompt_fingerprint(replace(p, state=state), "neutral", "jev") for state in (None, {}, [])
    }
    assert len(prints) == 3


def _rec(arm: str, model: str, instrument: str, probe_id: str, value: str) -> dict:
    return {
        "probe_id": probe_id,
        "instrument": instrument,
        "persona": "neutral",
        "arm": arm,
        "replicate": 0,
        "backend": "openrouter",
        "model": model,
        "kind": "choice",
        "value": value,
        "probabilities": {value: 1.0},
        "error": None,
        "meta": {},
        "usage": {},
    }


def test_rerun_replaces_only_the_changed_instruments_of_its_own_model(tmp_path, monkeypatch):
    import json

    from jevbench import config
    from jevbench.analysis import RERUN_DIR_NAME, load_records

    raw = tmp_path / "raw"
    (raw / RERUN_DIR_NAME).mkdir(parents=True)
    monkeypatch.setattr(config, "RAW_DIR", raw)
    old = [
        _rec("jev", "v/m", "allais", "allais_problem1", "old"),
        _rec("jev", "v/m", "crt", "crt_1", "kept"),
        _rec("baseline", "chat/other", "allais", "allais_problem1", "chat-old"),
    ]
    new = [_rec("jev", "v/m-2026", "allais", "allais_problem1", "new")]
    run = raw / "run_live_1_m.jsonl"
    run.write_text("\n".join(json.dumps(r) for r in old))
    (raw / RERUN_DIR_NAME / "run_live_2_m.jsonl").write_text("\n".join(json.dumps(r) for r in new))

    df = load_records(run).set_index(["arm", "probe_id"])
    assert df.loc[("jev", "allais_problem1"), "value"] == "new"
    assert df.loc[("jev", "crt_1"), "value"] == "kept"
    assert df.loc[("baseline", "allais_problem1"), "value"] == "chat-old"
