"""A deterministic offline backend.

Its purpose is to let the whole pipeline — runner, analysis, plots, tests — be
exercised in CI with no API key and no network. It is emphatically *not* a
model of Jev: it produces structurally valid, reproducible nonsense. Every
record it writes is tagged `backend="simulator"`, and the analysis layer refuses
to mix simulated and live records in one report.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .schema import Choice, DecisionResponse, Noul, Question, Score


def _unit_float(*parts: str) -> float:
    digest = hashlib.sha256("|".join(parts).encode()).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


def _softmax_like(keys: list[str], seed: str) -> dict[str, float]:
    weights = [_unit_float(seed, k) ** 2 + 1e-6 for k in keys]
    total = sum(weights)
    return {k: round(w / total, 4) for k, w in zip(keys, weights, strict=True)}


class SimulatorClient:
    """Mirrors `SystemOneClient.decide` without touching the network."""

    def __init__(self, seed: str = "jevbench", stands_in_for: str | None = None) -> None:
        self.seed = seed
        # Named so that two simulated "models" stay distinguishable in a
        # comparison, without the served name ever looking like a real model.
        self.model = f"simulator-v1[{stands_in_for}]" if stands_in_for else "simulator-v1"
        self.call_log: list[dict[str, Any]] = []

    def close(self) -> None:  # parity with the HTTP client
        return None

    def __enter__(self) -> SimulatorClient:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def decide(self, state: Any, questions: dict[str, Question]) -> DecisionResponse:
        state_key = json.dumps(state, sort_keys=True, default=str)
        answers: dict[str, Any] = {}
        for qid, q in questions.items():
            base = f"{self.seed}|{state_key}|{qid}|{q.instructions}"
            if isinstance(q, Choice):
                probs = _softmax_like(list(q.criteria), base)
                answers[qid] = {
                    "type": "choice",
                    "choice": max(probs, key=lambda k: probs[k]),
                    "probabilities": probs,
                    "confidence": round(max(probs.values()), 4),
                }
            elif isinstance(q, Score):
                keys = [str(i) for i in range(len(q.criteria))]
                probs = _softmax_like(keys, base)
                expected = sum(int(k) * v for k, v in probs.items())
                answers[qid] = {
                    "type": "score",
                    "score": round(expected, 4),
                    "legend": {str(i): lvl for i, lvl in enumerate(q.criteria)},
                    "probabilities": probs,
                    "confidence": round(max(probs.values()), 4),
                }
            elif isinstance(q, Noul):
                answers[qid] = {"type": "noul", "noul": round(_unit_float(base), 4)}
        obj = {
            "model": self.model,
            "answers": answers,
            "usage": {"input_tokens": 0, "output_tokens": 0, "cost": 0.0},
        }
        self.call_log.append({"url": "simulator", "status": 200, "usage": obj["usage"]})
        return DecisionResponse.parse(obj)
