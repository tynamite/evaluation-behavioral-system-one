"""Executes the battery and writes one JSONL record per observation."""

from __future__ import annotations

import json
import random
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .client import SystemOneClient
from .config import RAW_DIR, Config
from .instruments import PERSONAS, Probe, all_probes, apply_persona, permute_options
from .schema import Choice, Score
from .simulator import SimulatorClient


@dataclass(slots=True)
class Record:
    """One observation: a probe, under a persona, on one arm, in one replicate."""

    probe_id: str
    instrument: str
    persona: str
    arm: str  # "jev" | "baseline"
    replicate: int
    backend: str
    model: str
    kind: str
    value: str | float | None
    probabilities: dict[str, float] = field(default_factory=dict)
    confidence: float | None = None
    legend: dict[str, Any] | None = None
    option_order: list[str] | None = None
    meta: dict[str, Any] = field(default_factory=dict)
    usage: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    timestamp: str = ""


def render_prompt(probe: Probe) -> tuple[str, list[str]]:
    """Render a probe as plain text for the autoregressive baseline arm."""
    q = probe.question
    parts: list[str] = []
    if probe.state:
        parts.append(json.dumps(probe.state, indent=2, default=str))
    parts.append(q.instructions)
    if isinstance(q, Choice):
        options = list(q.criteria)
        listing = "\n".join(f"- {k}: {v}" for k, v in q.criteria.items())
        parts.append(f"Options:\n{listing}")
        parts.append("Reply with exactly one option key and nothing else.")
    elif isinstance(q, Score):
        options = [str(i) for i in range(len(q.criteria))]
        listing = "\n".join(f"- {i}: {lvl}" for i, lvl in enumerate(q.criteria))
        parts.append(f"Levels:\n{listing}")
        parts.append("Reply with exactly one level number and nothing else.")
    else:
        options = ["true", "false"]
        parts.append("Reply with exactly 'true' or 'false' and nothing else.")
    return "\n\n".join(parts), options


class BatteryRunner:
    def __init__(
        self,
        config: Config,
        *,
        personas: list[str] | None = None,
        replicates: int = 3,
        seed: int = 20260918,
        workers: int = 8,
        randomise_options: bool = True,
    ) -> None:
        self.config = config
        self.personas = personas or list(PERSONAS)
        self.replicates = replicates
        self.seed = seed
        self.workers = workers
        self.randomise_options = randomise_options
        self._lock = threading.Lock()
        self._done = 0
        self._cost = 0.0

    def _client(self) -> Any:
        if self.config.backend == "simulator":
            return SimulatorClient(stands_in_for=self.config.model)
        return SystemOneClient(self.config)

    def _tick(self, total: int, cost: float) -> None:
        with self._lock:
            self._done += 1
            self._cost += cost
            if self._done % 25 == 0 or self._done == total:
                pct = 100 * self._done / total
                print(
                    f"  {self._done}/{total} ({pct:5.1f}%)  spend so far ${self._cost:.4f}",
                    file=sys.stderr,
                    flush=True,
                )

    # -- Jev arm --------------------------------------------------------
    def run_jev(self, probes: list[Probe]) -> list[Record]:
        jobs: list[tuple[Probe, str, int]] = [
            (p, persona, rep)
            for p in probes
            for persona in self.personas
            for rep in range(self.replicates)
        ]
        total = len(jobs)
        print(
            f"Jev arm: {total} calls ({len(probes)} probes x {len(self.personas)} personas "
            f"x {self.replicates} replicates)",
            file=sys.stderr,
        )
        records: list[Record] = []
        client = self._client()
        try:
            with ThreadPoolExecutor(max_workers=self.workers) as pool:
                futures = {pool.submit(self._one_jev, client, *job): job for job in jobs}
                for fut in as_completed(futures):
                    rec = fut.result()
                    records.append(rec)
                    self._tick(total, float(rec.usage.get("cost") or 0.0))
        finally:
            client.close()
        return records

    def _one_jev(self, client: Any, probe: Probe, persona_key: str, replicate: int) -> Record:
        persona = PERSONAS[persona_key]
        prepared = apply_persona(probe, persona)
        if self.randomise_options:
            rng = random.Random(f"{self.seed}|{probe.probe_id}|{persona_key}|{replicate}")
            prepared = permute_options(prepared, rng)
        now = datetime.now(UTC).isoformat()
        try:
            resp = client.decide(prepared.state, {"answer": prepared.question})
            ans = resp.answers["answer"]
            return Record(
                probe_id=probe.probe_id,
                instrument=probe.instrument,
                persona=persona_key,
                arm="jev",
                replicate=replicate,
                backend=self.config.backend,
                model=resp.model,
                kind=ans.kind,
                value=ans.value,
                probabilities=ans.probabilities,
                confidence=ans.confidence,
                legend=ans.legend,
                option_order=prepared.meta.get("option_order"),
                meta=probe.meta,
                usage=resp.usage,
                timestamp=now,
            )
        except Exception as exc:
            return Record(
                probe_id=probe.probe_id,
                instrument=probe.instrument,
                persona=persona_key,
                arm="jev",
                replicate=replicate,
                backend=self.config.backend,
                model=self.config.model,
                kind=probe.question.kind,
                value=None,
                meta=probe.meta,
                error=str(exc)[:500],
                timestamp=now,
            )

    # -- baseline arm ---------------------------------------------------
    def run_baseline(self, probes: list[Probe], samples: int = 10) -> list[Record]:
        """Estimate a chat model's response distribution by resampling.

        This is the comparison that motivates the project: to get from a
        text-generating model what Jev returns in a single call, the same prompt
        must be paid for `samples` times, and the result still mixes decoding
        noise into the estimate.
        """
        if self.config.backend == "simulator":
            return []
        jobs = [
            (p, persona, s) for p in probes for persona in self.personas for s in range(samples)
        ]
        total = len(jobs)
        print(
            f"Baseline arm: {total} calls ({samples} samples per probe x persona)", file=sys.stderr
        )
        records: list[Record] = []
        client = SystemOneClient(self.config)
        self._done = 0
        try:
            with ThreadPoolExecutor(max_workers=self.workers) as pool:
                futures = [pool.submit(self._one_baseline, client, *job) for job in jobs]
                for fut in as_completed(futures):
                    rec = fut.result()
                    records.append(rec)
                    self._tick(total, float(rec.usage.get("cost") or 0.0))
        finally:
            client.close()
        return records

    def _one_baseline(
        self, client: SystemOneClient, probe: Probe, persona_key: str, sample: int
    ) -> Record:
        persona = PERSONAS[persona_key]
        prepared = apply_persona(probe, persona)
        prompt, options = render_prompt(prepared)
        now = datetime.now(UTC).isoformat()
        try:
            out = client.chat_choice(prompt, options)
            return Record(
                probe_id=probe.probe_id,
                instrument=probe.instrument,
                persona=persona_key,
                arm="baseline",
                replicate=sample,
                backend=self.config.backend,
                model=self.config.baseline_model,
                kind=probe.question.kind,
                value=out["parsed"],
                meta={
                    **probe.meta,
                    "raw_text": out["raw_text"],
                    "finish_reason": out.get("finish_reason"),
                },
                usage=out.get("usage", {}),
                timestamp=now,
            )
        except Exception as exc:
            return Record(
                probe_id=probe.probe_id,
                instrument=probe.instrument,
                persona=persona_key,
                arm="baseline",
                replicate=sample,
                backend=self.config.backend,
                model=self.config.baseline_model,
                kind=probe.question.kind,
                value=None,
                meta=probe.meta,
                error=str(exc)[:500],
                timestamp=now,
            )


def model_slug(model: str) -> str:
    """A filesystem-safe name for a model id: `openai/gpt-6-luna` -> `openai--gpt-6-luna`."""
    return re.sub(r"[^A-Za-z0-9._-]+", "-", model.replace("/", "--")).strip("-")


def write_jsonl(records: list[Record], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(asdict(rec), default=str) + "\n")
    return path


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def run_battery(
    config: Config,
    *,
    modules: list[str] | None = None,
    personas: list[str] | None = None,
    replicates: int = 3,
    baseline_samples: int = 0,
    workers: int = 8,
    out_dir: Path | None = None,
) -> Path:
    probes = all_probes(modules)
    runner = BatteryRunner(config, personas=personas, replicates=replicates, workers=workers)
    started = time.time()
    # replicates=0 skips the System One arm, so a new chat model can be added
    # as a baseline-only run without paying for the typed arm again.
    records = runner.run_jev(probes) if replicates > 0 else []
    if baseline_samples > 0:
        records.extend(runner.run_baseline(probes, samples=baseline_samples))
    if not records:
        raise RuntimeError("nothing to run: set --replicates or --baseline-samples above 0")

    out_dir = out_dir or RAW_DIR
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    tag = "simulated" if config.backend == "simulator" else "live"
    # The timestamp still leads, so `latest_run` keeps sorting chronologically;
    # the suffix names which models are in the file, so runs of several models
    # can sit side by side in data/raw/.
    arms = [config.model] if replicates > 0 else []
    if baseline_samples > 0 and config.backend != "simulator":
        arms.append(config.baseline_model)
    path = out_dir / f"run_{tag}_{stamp}_{'+'.join(model_slug(m) for m in arms)}.jsonl"
    write_jsonl(records, path)

    total_cost = sum(float(r.usage.get("cost") or 0.0) for r in records)
    errors = sum(1 for r in records if r.error)
    print(
        f"\nwrote {len(records)} records to {path.relative_to(path.parents[2])}\n"
        f"elapsed {time.time() - started:.1f}s  total cost ${total_cost:.4f}  errors {errors}",
        file=sys.stderr,
    )
    return path
