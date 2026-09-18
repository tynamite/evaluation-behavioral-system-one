"""End-to-end on the offline simulator: no key, no network, fully deterministic."""

from __future__ import annotations

from pathlib import Path

import pytest

from jevbench.analysis import analyse_run, load_records
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
    secret = "sk-or-v1-abcdef0123456789"
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
