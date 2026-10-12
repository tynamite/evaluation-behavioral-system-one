"""Transport behaviour, against a mocked HTTP layer: no key, no network."""

from __future__ import annotations

import json

import httpx
import pytest

from jevbench.client import Refusal, SystemOneClient
from jevbench.config import Config
from jevbench.schema import Noul


def _client(handler: httpx.MockTransport, **cfg: object) -> SystemOneClient:
    config = Config(backend="openrouter", api_key="sk-or-v1-TEST_ONLY_NOT_A_KEY", **cfg)  # type: ignore[arg-type]
    client = SystemOneClient(config)
    client._client = httpx.Client(transport=handler)
    return client


def test_a_refusal_is_reported_as_one_and_not_retried() -> None:
    calls = 0

    def handle(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        body = {"error": {"message": 'OpenAI refused to answer question "answer"', "code": 502}}
        return httpx.Response(502, json=body)

    client = _client(httpx.MockTransport(handle), max_retries=5)
    with pytest.raises(Refusal, match=r"^refused: "):
        client.decide({}, {"answer": Noul(instructions="A claim.")})
    assert calls == 1


def test_a_plain_502_is_still_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("jevbench.client.time.sleep", lambda _s: None)
    calls = 0

    def handle(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(502, text="Bad Gateway")

    client = _client(httpx.MockTransport(handle), max_retries=3)
    with pytest.raises(RuntimeError, match="after 3 attempts"):
        client.decide({}, {"answer": Noul(instructions="A claim.")})
    assert calls == 3


def test_the_baseline_token_cap_is_configurable_and_recorded() -> None:
    sent: dict[str, object] = {}

    def handle(request: httpx.Request) -> httpx.Response:
        sent.update(json.loads(request.content))
        reply = {"choices": [{"message": {"content": "b"}, "finish_reason": "stop"}]}
        return httpx.Response(200, json=reply)

    client = _client(httpx.MockTransport(handle), baseline_max_tokens=4096)
    out = client.chat_choice("Pick one.", ["a", "b"])
    assert sent["max_tokens"] == 4096
    assert out["max_tokens"] == 4096
    assert out["parsed"] == "b"
