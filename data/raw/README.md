# Raw run records

One JSON object per line, one line per observation. These files are committed
deliberately: every number in the README, the tables and the figures is derived
from them, so anyone can recompute the entire analysis without an API key and
without spending anything.

    jevbench analyse --run data/raw/run_live_<timestamp>.jsonl
    jevbench figures --run data/raw/run_live_<timestamp>.jsonl

Filenames are tagged `live` or `simulated`. `simulated` files come from the
offline deterministic backend; they are structurally valid nonsense used to
exercise the pipeline in CI, and `load_records` refuses to pool them with live
records.

## Fields

| Field | Meaning |
|---|---|
| `probe_id`, `instrument` | which item, and which instrument it belongs to |
| `persona` | `neutral`, `typical_human`, `rational_agent` or `antisocial` |
| `arm` | `jev` (System One) or `baseline` (autoregressive chat model) |
| `replicate` | replicate index; for the baseline arm, the resample index |
| `backend`, `model` | transport used, and the exact served model version |
| `kind` | `choice`, `score` or `noul` |
| `value` | the point answer — reported for readability, never analysed |
| `probabilities` | **the unit of analysis**: the returned distribution |
| `confidence` | the model's calibrated confidence, where the primitive returns one |
| `legend` | for Score items, the index-to-level mapping |
| `option_order` | the permutation used for this replicate, for the order-effect analysis |
| `meta` | scoring keys for the instrument (correct answer, lure, trait, reverse-keying) |
| `usage` | token counts and cost for this call |
| `error` | transport error, if any; such records are excluded and counted |

No prompts contain personal data, and no credentials appear in these files.
