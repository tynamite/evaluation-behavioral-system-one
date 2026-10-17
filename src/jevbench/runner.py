"""Executes the battery and writes one JSONL record per observation."""

from __future__ import annotations

import hashlib
import json
import random
import re
import sys
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .client import SystemOneClient
from .config import RAW_DIR, Config
from .instruments import (
    PERSONAS,
    Probe,
    all_probes,
    apply_persona,
    asked_under,
    permute_options,
)
from .schema import Choice, Score, allowed_keys, distribution_problem
from .simulator import SimulatorClient

JobKey = tuple[str, str, str, int]  # (arm, probe_id, persona, replicate)


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
    # When the answer that was kept arrived. `timestamp` is taken when the call
    # is first sent, so retries and backoff can put minutes between the two.
    # Recorded on the Jev arm only; None in runs made before it existed.
    answered_at: str | None = None
    # A short hash of the wording this record was asked (see `prompt_fingerprint`).
    # None in runs made before it existed.
    prompt_sha: str | None = None


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


def prepare_probe(
    probe: Probe, persona_key: str, replicate: int, *, seed: int, randomise_options: bool
) -> Probe:
    """The probe as sent: the persona applied, then the seeded option shuffle.

    Seeded by item, persona and repeat, not by model, so every model sees the
    same order on a given repeat.
    """
    prepared = apply_persona(probe, PERSONAS[persona_key])
    if randomise_options:
        rng = random.Random(f"{seed}|{probe.probe_id}|{persona_key}|{replicate}")
        prepared = permute_options(prepared, rng)
    return prepared


def resume_order_mismatch(
    kept: list[dict[str, Any]], probes: list[Probe], *, seed: int, randomise_options: bool
) -> str | None:
    """Why the kept records of a resumed run were made with other order settings, if they were.

    Resuming with a different `--seed` or `--fixed-order` would mix two
    conditions in one file without a trace, so the option order each kept
    record saw is recomputed from the settings given now and compared.
    """
    by_id = {p.probe_id: p for p in probes}
    for row in kept:
        probe = by_id.get(row["probe_id"])
        if probe is None or row["persona"] not in PERSONAS:
            continue
        expected = prepare_probe(
            probe,
            row["persona"],
            int(row["replicate"]),
            seed=seed,
            randomise_options=randomise_options,
        ).meta.get("option_order")
        if row.get("option_order") != expected:
            return (
                f"{row['probe_id']} / {row['persona']} / repeat {row['replicate']} was "
                f"presented as {row.get('option_order')}, but these settings give {expected}"
            )
    return None


# Instruments whose wording changed after the 12-15 Oct 2026 runs: an index
# (`pair`, `row`) was removed from the state sent with each item. Records of these
# made before records carried a fingerprint used the old wording.
CHANGED_AFTER_FIRST_RUNS = frozenset({"allais", "allais_estimate", "holt_laury"})


def prompt_fingerprint(probe: Probe, persona_key: str) -> str:
    """A short hash of what the model is asked: state, instructions and the option set.

    Taken before the option shuffle, so it does not depend on the seed, and
    after the persona, so each persona has its own.
    """
    p = apply_persona(probe, PERSONAS[persona_key])
    q = p.question
    options = getattr(q, "criteria", None)
    if isinstance(options, dict):
        options = sorted(options.items())
    body = {"state": p.state or {}, "instructions": q.instructions, "options": options}
    raw = json.dumps(body, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def resume_prompt_mismatch(kept: list[dict[str, Any]], probes: list[Probe]) -> str | None:
    """Why the kept records of a resumed run were asked other wording than now, if they were.

    Resuming skips what is done and asks the rest, so a changed item would end up
    half in one wording and half in the other without a trace. A record carries
    the fingerprint of what it was asked; one from before records did is checked
    against the instruments known to have changed since.
    """
    by_id = {p.probe_id: p for p in probes}
    for row in kept:
        probe = by_id.get(row["probe_id"])
        if probe is None or row["persona"] not in PERSONAS:
            continue
        sha = row.get("prompt_sha")
        if sha is None:
            if probe.instrument in CHANGED_AFTER_FIRST_RUNS:
                return (
                    f"{row['probe_id']} was asked before its wording changed (its state no "
                    "longer carries the item index); re-run it into a new file"
                )
        elif sha != prompt_fingerprint(probe, row["persona"]):
            return f"{row['probe_id']} / {row['persona']} was asked other wording than it is now"
    return None


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
        sink: Callable[[Record], None] | None = None,
        done: set[JobKey] | None = None,
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
        # Each record goes to `sink` the moment it completes, so a run that is
        # killed part-way keeps everything it has paid for; `done` lists what a
        # previous attempt already has, which `--resume` then skips.
        self.sink = sink
        self.done = done or set()

    def _emit(self, rec: Record) -> None:
        if self.sink is not None:
            with self._lock:
                self.sink(rec)

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
            if asked_under(p, persona)
            for rep in range(self.replicates)
            if ("jev", p.probe_id, persona, rep) not in self.done
        ]
        total = len(jobs)
        print(
            f"Jev arm: {total} calls ({len(probes)} probes x up to {len(self.personas)} personas "
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
                    self._emit(rec)
                    self._tick(total, float(rec.usage.get("cost") or 0.0))
        finally:
            client.close()
        return records

    def _one_jev(self, client: Any, probe: Probe, persona_key: str, replicate: int) -> Record:
        prepared = prepare_probe(
            probe,
            persona_key,
            replicate,
            seed=self.seed,
            randomise_options=self.randomise_options,
        )
        now = datetime.now(UTC).isoformat()
        try:
            resp = client.decide(prepared.state, {"answer": prepared.question})
            answered_at = datetime.now(UTC).isoformat()
            ans = resp.answers["answer"]
            # Checked here, after the response, so a rejected reply keeps the
            # model that served it and the cost it ran up.
            problem = distribution_problem(ans.probabilities, allowed_keys(prepared.question))
            return Record(
                probe_id=probe.probe_id,
                instrument=probe.instrument,
                persona=persona_key,
                arm="jev",
                replicate=replicate,
                backend=self.config.backend,
                model=resp.model,
                kind=ans.kind,
                value=None if problem else ans.value,
                probabilities={} if problem else ans.probabilities,
                confidence=ans.confidence,
                legend=ans.legend,
                option_order=prepared.meta.get("option_order"),
                meta=probe.meta,
                usage=resp.usage,
                error=f"{UNUSABLE}{problem}" if problem else None,
                timestamp=now,
                answered_at=answered_at,
                prompt_sha=prompt_fingerprint(probe, persona_key),
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
                prompt_sha=prompt_fingerprint(probe, persona_key),
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
            (p, persona, s)
            for p in probes
            for persona in self.personas
            if asked_under(p, persona)
            for s in range(samples)
            if ("baseline", p.probe_id, persona, s) not in self.done
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
                    self._emit(rec)
                    self._tick(total, float(rec.usage.get("cost") or 0.0))
        finally:
            client.close()
        return records

    def _one_baseline(
        self, client: SystemOneClient, probe: Probe, persona_key: str, sample: int
    ) -> Record:
        # Same seeded shuffle as the System One arm, so on a given replicate
        # both arms see the options in the same order. The committed runs (18 Sep
        # and 12 Oct 2026) did not shuffle here, and listed every scored item's correct option
        # first; docs/LEARNINGS.md has the detail.
        prepared = prepare_probe(
            probe, persona_key, sample, seed=self.seed, randomise_options=self.randomise_options
        )
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
                option_order=prepared.meta.get("option_order"),
                meta={
                    **probe.meta,
                    "raw_text": out["raw_text"],
                    "finish_reason": out.get("finish_reason"),
                    "max_tokens": out.get("max_tokens"),
                },
                usage=out.get("usage", {}),
                timestamp=now,
                prompt_sha=prompt_fingerprint(probe, persona_key),
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
                prompt_sha=prompt_fingerprint(probe, persona_key),
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


# The error prefix for a reply that arrived and was billed but could not be used.
UNUSABLE = "unusable answer: "


def _done_keys(path: Path) -> tuple[list[dict[str, Any]], set[JobKey]]:
    """The records in an interrupted run worth keeping, and their job keys.

    Records that ended in an error are dropped so `--resume` retries them,
    rather than leaving the failure and its retry side by side in one file.
    A reply that was served, billed and then rejected as unusable is kept as
    it is: dropping it would lose its cost and its place in the health counts,
    and retrying would pay for the same call again.
    """
    kept = [
        r for r in read_jsonl(path) if not r.get("error") or str(r["error"]).startswith(UNUSABLE)
    ]
    return kept, {(r["arm"], r["probe_id"], r["persona"], int(r["replicate"])) for r in kept}


def run_battery(
    config: Config,
    *,
    modules: list[str] | None = None,
    personas: list[str] | None = None,
    replicates: int = 3,
    baseline_samples: int = 0,
    workers: int = 8,
    seed: int = 20260918,
    randomise_options: bool = True,
    out_dir: Path | None = None,
    resume: Path | None = None,
    probes: list[Probe] | None = None,
) -> Path:
    if replicates <= 0 and baseline_samples <= 0:
        raise RuntimeError("nothing to run: set --replicates or --baseline-samples above 0")

    # A study outside the battery (such as the pick-a-number addendum) passes
    # its own items; otherwise the battery's modules are run.
    probes = probes if probes is not None else all_probes(modules)
    if resume is not None:
        path = resume
        kept, done = _done_keys(path)
        # Against the whole battery, not this invocation's modules: a kept
        # record from a module not selected now must still match.
        problem = resume_order_mismatch(
            kept, all_probes() + probes, seed=seed, randomise_options=randomise_options
        )
        if problem:
            raise RuntimeError(
                f"cannot resume {path.name} with these --seed/--fixed-order settings: {problem}"
            )
        problem = resume_prompt_mismatch(kept, all_probes() + probes)
        if problem:
            raise RuntimeError(f"cannot resume {path.name}: {problem}")
        print(f"resuming {path.name}: keeping {len(kept)} completed records", file=sys.stderr)
    else:
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
        kept, done = [], set()

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in kept:
            fh.write(json.dumps(row, default=str) + "\n")
        fh.flush()

        def sink(rec: Record) -> None:
            fh.write(json.dumps(asdict(rec), default=str) + "\n")
            fh.flush()

        runner = BatteryRunner(
            config,
            personas=personas,
            replicates=replicates,
            seed=seed,
            workers=workers,
            randomise_options=randomise_options,
            sink=sink,
            done=done,
        )
        started = time.time()
        # replicates=0 skips the System One arm, so a new chat model can be added
        # as a baseline-only run without paying for the typed arm again.
        if replicates > 0:
            runner.run_jev(probes)
        if baseline_samples > 0:
            runner.run_baseline(probes, samples=baseline_samples)

    rows = read_jsonl(path)
    total_cost = sum(float((r.get("usage") or {}).get("cost") or 0.0) for r in rows)
    errors = sum(1 for r in rows if r.get("error"))
    print(
        f"\nwrote {len(rows)} records to {path.name}\n"
        f"elapsed {time.time() - started:.1f}s  total cost ${total_cost:.4f}  errors {errors}",
        file=sys.stderr,
    )
    return path
