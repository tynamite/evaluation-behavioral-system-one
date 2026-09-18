"""Transport for the System One decision API, plus the autoregressive baseline arm.

Three backends share one interface:

  openrouter  POST /api/alpha/decisions        (Jev via OpenRouter)
  typesafe    POST /v1/systemone               (Jev native)
  simulator   no network at all                (deterministic, for tests/CI)

The OpenRouter decisions route is an alpha route. `jevbench doctor` probes it
and reports what it finds so a move can be diagnosed in one command rather than
by reading tracebacks; JEVBENCH_DECISIONS_URL overrides it.
"""

from __future__ import annotations

import json
import random
import re
import time
from typing import Any, Protocol

import httpx

from .config import Config, redact
from .schema import DecisionResponse, Question

RETRY_STATUS = {408, 429, 500, 502, 503, 504, 529}


class DecisionBackend(Protocol):
    def decide(self, state: Any, questions: dict[str, Question]) -> DecisionResponse: ...


class SystemOneClient:
    """HTTP client for Jev, with bounded exponential backoff and jitter."""

    def __init__(self, config: Config | None = None) -> None:
        self.config = config or Config.from_env()
        self._key = self.config.require_key()
        self._client = httpx.Client(timeout=self.config.timeout)
        self.call_log: list[dict[str, Any]] = []

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> SystemOneClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _headers(self) -> dict[str, str]:
        headers = {"Authorization": f"Bearer {self._key}", "Content-Type": "application/json"}
        if self.config.backend == "openrouter":
            # Optional attribution headers; harmless if ignored.
            headers["HTTP-Referer"] = "https://github.com/tynamite/Jev_test"
            headers["X-Title"] = "jevbench"
        return headers

    def decide(self, state: Any, questions: dict[str, Question]) -> DecisionResponse:
        payload = {
            "model": self.config.model,
            "state": state,
            "questions": {qid: q.to_payload() for qid, q in questions.items()},
        }
        obj = self._post(self.config.decisions_url, payload)
        return DecisionResponse.parse(obj)

    def _post(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(self.config.max_retries):
            try:
                started = time.monotonic()
                resp = self._client.post(url, headers=self._headers(), json=payload)
                elapsed = time.monotonic() - started
                if resp.status_code in RETRY_STATUS:
                    raise httpx.HTTPStatusError(
                        f"retryable status {resp.status_code}", request=resp.request, response=resp
                    )
                if resp.status_code >= 400:
                    detail = redact(resp.text[:600], self._key)
                    raise RuntimeError(f"HTTP {resp.status_code} from {url}: {detail}")
                obj: dict[str, Any] = resp.json()
                self.call_log.append(
                    {
                        "url": url,
                        "status": resp.status_code,
                        "latency_s": round(elapsed, 4),
                        "usage": obj.get("usage", {}),
                    }
                )
                return obj
            except (httpx.HTTPError, json.JSONDecodeError) as exc:
                last_error = exc
                if attempt == self.config.max_retries - 1:
                    break
                backoff = min(2.0**attempt, 16.0) + random.uniform(0, 0.75)
                time.sleep(backoff)
        raise RuntimeError(
            f"request to {url} failed after {self.config.max_retries} attempts: "
            f"{redact(str(last_error), self._key)}"
        ) from last_error

    # -- baseline arm ---------------------------------------------------
    def chat_choice(self, prompt: str, options: list[str]) -> dict[str, Any]:
        """Ask an ordinary chat model to pick one option, returning its raw reply.

        The baseline arm deliberately does *not* try to extract a calibrated
        distribution from the chat model — that asymmetry is the point of the
        project. It is resampled instead (see `BatteryRunner.run_baseline`).

        `max_tokens` is generous rather than minimal. An earlier version capped
        it at 8, which truncated the reply into `content: null` on exactly the
        items the model found hardest — a systematic hole, not random loss.
        """
        payload = {
            "model": self.config.baseline_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 1.0,
            "max_tokens": 64,
        }
        obj = self._post(self.config.chat_url, payload)
        choices = obj.get("choices") or []
        message = (choices[0].get("message") if choices else None) or {}
        text = message.get("content")
        finish = choices[0].get("finish_reason") if choices else None
        return {
            "raw_text": text,
            "parsed": parse_option(text, options),
            "finish_reason": finish,
            "usage": obj.get("usage", {}),
        }


def parse_option(text: str | None, options: list[str]) -> str | None:
    """Recover which option a free-text reply names.

    Substring matching alone is wrong here: on the p-beauty contest the options
    are "0".."100", so a naive search finds "3" inside "33" and "1" inside
    "100". Longest-first matching on word boundaries avoids that, and numeric
    option sets are resolved by parsing the number rather than by text search.
    """
    if not text or not text.strip():
        return None
    cleaned = text.strip()
    lowered = cleaned.lower()

    for opt in options:
        if opt.lower() == lowered:
            return opt

    numeric = all(_as_number(o) is not None for o in options)
    if numeric:
        found = re.findall(r"-?\d+(?:\.\d+)?", cleaned.replace(",", ""))
        if found:
            # The final number in the reply is the answer when a model
            # restates the problem before answering.
            for token in reversed(found):
                for opt in options:
                    if _as_number(opt) == _as_number(token):
                        return opt
        return None

    for opt in sorted(options, key=len, reverse=True):
        if re.search(rf"(?<![\w${{}}.]){re.escape(opt.lower())}(?![\w.])", lowered):
            return opt
    return None


def _as_number(text: str) -> float | None:
    try:
        return float(text.strip().lstrip("$").replace(",", ""))
    except ValueError:
        return None
