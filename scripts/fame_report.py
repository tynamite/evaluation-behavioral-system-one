#!/usr/bin/env python3
"""Print the fame index's verdict for every item: tiers, drop rule, familiarity.

    python scripts/fame_report.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jevbench import fame  # noqa: E402


def main() -> int:
    verdicts = fame.all_verdicts()
    header = (
        f"{'item':22s} {'citations':10s} {'wikipedia':10s} {'familiarity':12s} {'tier':8s} reason"
    )
    print(header)
    print("-" * len(header))
    for v in verdicts:
        fam = f"{v.familiarity_mean:.2f}" if v.familiarity_mean is not None else "-"
        tier = v.fame_tier or ("DROPPED" if v.dropped else "-")
        print(
            f"{v.key:22s} {v.citation_tier or '-':10s} {v.wikipedia_tier:10s} "
            f"{fam:12s} {tier:8s} {v.reason}"
        )

    kept = [v for v in verdicts if not v.dropped]
    print(f"\n{len(kept)}/{len(verdicts)} items kept; {len(verdicts) - len(kept)} dropped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
