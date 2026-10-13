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
