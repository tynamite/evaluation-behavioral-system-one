# Retired code

The follow-up study's fame index and pairing rule
([`FOLLOWUP_PREREGISTRATION.md`](../FOLLOWUP_PREREGISTRATION.md), sections 3 and
8.2) were built and applied to the item pool, which turned out not to support the
design (Amendment 3, section 10, gives the findings and the consequence for the
pairing rule). H1 and H2, the hypotheses that depend on them, were
therefore never run. Nothing else in the project uses this code, so it is kept
here rather than in the package, where its tests and type checks would keep
running for no result.

| File | What it was |
|---|---|
| `fame.py` | the fame index: citation count, Wikipedia article length, model-rated familiarity |
| `pairing.py` | the Section 3 rule that pairs each item with its nearest neighbour on magnitude from the opposite fame tercile |
| `ml2_effects.py` | the Many Labs 2 effect sizes the pairing rule reads |
| `fame_report.py`, `pairing_report.py`, `rate_familiarity.py` | the scripts that ran them |
| `test_fame.py`, `test_pairing.py` | their tests |

`data/fame_familiarity.json` is the one output it produced, and stays where it
was. To run any of this, move the three modules back into `src/jevbench/`, the
scripts into `scripts/` and the tests into `tests/`.
