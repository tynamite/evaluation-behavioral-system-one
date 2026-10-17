"""Check that the rebuilt tables and comparison match what git has committed.

Run after `jevbench analyse` and `jevbench compare`. Floating-point sums come
out different in the last digit on another machine, so numbers are compared
to a relative 1e-9 and everything else exactly. `intervals.csv` is left out:
CI rebuilds without the replicate intervals.
"""

from __future__ import annotations

import json
import math
import subprocess
import sys
from io import StringIO
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DIRS = ["results/tables", "results/comparison"]
RTOL = 1e-9


def committed(rel: str) -> str | None:
    p = subprocess.run(
        ["git", "-C", str(ROOT), "show", f"HEAD:{rel}"], capture_output=True, text=True
    )
    return p.stdout if p.returncode == 0 else None


def same(a: object, b: object) -> bool:
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b, strict=True))
    if isinstance(a, float) and isinstance(b, float):
        return (math.isnan(a) and math.isnan(b)) or math.isclose(a, b, rel_tol=RTOL, abs_tol=1e-12)
    return a == b


def main() -> int:
    tracked = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", *DIRS], capture_output=True, text=True, check=True
    ).stdout.split()
    wanted = [t for t in tracked if t.endswith((".csv", ".json")) and not t.endswith("intervals.csv")]
    problems = []
    for rel in wanted:
        path = ROOT / rel
        if not path.exists():
            problems.append(f"{rel}: not rebuilt")
            continue
        old = committed(rel)
        if old is None:
            problems.append(f"{rel}: not in HEAD")
        elif rel.endswith(".json"):
            if not same(json.loads(old), json.loads(path.read_text())):
                problems.append(f"{rel}: differs")
        else:
            a, b = pd.read_csv(StringIO(old)), pd.read_csv(path)
            try:
                pd.testing.assert_frame_equal(a, b, check_exact=False, rtol=RTOL, atol=1e-12)
            except AssertionError as exc:
                problems.append(f"{rel}: differs ({str(exc).splitlines()[0]})")
    for rel in subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "--others", "--exclude-standard", *DIRS],
        capture_output=True, text=True, check=True,
    ).stdout.split():
        if not rel.endswith("intervals.csv") and rel.endswith((".csv", ".json")):
            problems.append(f"{rel}: new file, not committed")
    for p in problems:
        print(p, file=sys.stderr)
    print(f"{len(wanted)} files checked, {len(problems)} differ")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
