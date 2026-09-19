#!/usr/bin/env python3
"""Print the Section 3 pairing rule's eligible items and the pairs it forms.

    python scripts/pairing_report.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jevbench import pairing  # noqa: E402


def main() -> int:
    items = pairing.eligible_items()
    print(f"{'item':22s} {'fame tier':10s} {'format':8s} magnitude")
    print("-" * 55)
    for it in sorted(items, key=lambda i: (i.format_group, -i.magnitude)):
        print(f"{it.key:22s} {it.fame_tier:10s} {it.format_group:8s} {it.magnitude:.3f}")

    pairs = pairing.build_pairs(items)
    print(f"\n{len(items)} eligible item(s), {len(pairs)} pair(s) formed.\n")
    if not pairs:
        print("No pairs: see FOLLOWUP_PREREGISTRATION.md Amendment 3 for why.")
    for p in pairs:
        print(
            f"  {p.lower_fame_key} <-> {p.higher_fame_key} "
            f"({p.format_group}, gap={p.magnitude_gap:.3f})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
