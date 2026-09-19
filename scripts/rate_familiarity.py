#!/usr/bin/env python3
"""Leg 3 of the fame index: comparison-model-rated familiarity.

`FOLLOWUP_PREREGISTRATION.md` Section 8.2: "how well-known is this finding to
a general audience" (Score 1-5), averaged over 5 replicates, sourced from the
*comparison arm's* model rather than Jev, to avoid asking Jev to rate an
effect's fame and then using that rating to explain Jev's own behaviour on
it. This makes live calls against `Config.baseline_model` via the same
`SystemOneClient.chat_choice` path the main battery's baseline arm already
uses — one call per (item, replicate), 14 items x 5 replicates = 70 calls.

    python scripts/rate_familiarity.py

Writes `data/fame_familiarity.json`: {item_key: [rating, rating, ...]}.
Existing entries for an item are overwritten; other items in the file, if
any, are left alone, so a partial re-run only touches what it actually ran.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jevbench import fame  # noqa: E402
from jevbench.client import SystemOneClient  # noqa: E402
from jevbench.config import Config  # noqa: E402

REPLICATES = 5
SCALE = ["1", "2", "3", "4", "5"]

PROMPT = """Here is a finding from behavioural science, described without naming \
the study or the researchers:

{description}

On a scale from 1 to 5, how well-known is this specific finding to a general \
audience (people with no particular background in psychology or economics)?

1 = most people have never encountered this, even in passing
3 = some people would recognise it, most would not
5 = most people have encountered this at some point, even without a \
psychology background

Answer with a single digit from 1 to 5."""


def main() -> int:
    config = Config.from_env()
    existing: dict[str, list[float]] = fame.load_familiarity()
    out: dict[str, list[float]] = dict(existing)

    total_cost = 0.0
    unparsed = 0
    with SystemOneClient(config) as client:
        for item in fame.ITEMS.values():
            ratings: list[float] = []
            for _ in range(REPLICATES):
                result = client.chat_choice(
                    PROMPT.format(description=item.familiarity_prompt), SCALE
                )
                total_cost += float((result.get("usage") or {}).get("cost") or 0.0)
                parsed = result.get("parsed")
                if parsed is None:
                    unparsed += 1
                    continue
                ratings.append(float(parsed))
            out[item.key] = ratings
            mean = sum(ratings) / len(ratings) if ratings else float("nan")
            print(f"{item.key:22s} {ratings}  mean={mean:.2f}")

    fame.FAMILIARITY_PATH.parent.mkdir(parents=True, exist_ok=True)
    fame.FAMILIARITY_PATH.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(f"\nwrote {fame.FAMILIARITY_PATH}")
    print(f"total cost ${total_cost:.4f}  unparsed {unparsed}/{len(fame.ITEMS) * REPLICATES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
