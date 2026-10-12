# Earlier runs

The runs the first version of this write-up was based on, kept so its
numbers stay recomputable. They predate the method fixes described in
[docs/LEARNINGS.md](../../docs/LEARNINGS.md) and are not used by any current
table, figure or document.

| File | What it is |
|---|---|
| `run_live_20260918T230710Z.jsonl` | Jev 1.13 and Claude Sonnet 5, 18 Sep 2026: 117 probes × 4 personas × 10 |
| `run_live_20261012T*_<model>.jsonl` | nine other System One models, Claude Haiku 5.5, and Drex 1.5, 12 Oct 2026: 147 probes × 4 personas × 10 |

The field layout is the same as in [data/raw/](../raw/README.md).

    jevbench analyse --run data/archive/run_live_20260918T230710Z.jsonl --out old-results/tables
