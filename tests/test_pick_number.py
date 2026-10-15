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
    dist = rows["Jev, its distribution"]
    assert dist["7"] == pytest.approx(0.4) and dist["3"] == pytest.approx(0.4)
    picks = rows["Jev, one pick per call"]
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

    row = {"probe_id": "pick_number_1_10", "instrument": "pick_number", "persona": "neutral",
           "arm": "jev", "replicate": 0, "backend": "typesafe", "model": "jev-1.13.0",
           "kind": "choice", "value": "7", "probabilities": {"7": 1.0}, "error": None}  # fmt: skip
    for name in ("run_live_A_jev-1.13.0.jsonl", "run_live_B_jev-1.13.0.jsonl"):
        (tmp_path / name).write_text(json.dumps(row) + "\n")
    with pytest.raises(ValueError, match="exactly one Jev run and one chat run"):
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
    with pytest.raises(ValueError, match="not one model"):
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
