# Raw run records

One JSON object per line, one line per observation. These files are committed
deliberately: every number in the README, the tables and the figures is derived
from them, so anyone can recompute the entire analysis without an API key and
without spending anything.

    jevbench analyse --run data/raw/run_live_<timestamp>.jsonl
    jevbench figures --run data/raw/run_live_<timestamp>.jsonl

Filenames are tagged `live` or `simulated`, and runs made since multi-model
support end in the model(s) they contain, e.g.
`run_live_<timestamp>_liquid--d1.jsonl`. `simulated` files come from the
offline deterministic backend; they are structurally valid nonsense used to
exercise the pipeline in CI, and `load_records` refuses to pool them with live
records.

## Fields

| Field | Meaning |
|---|---|
| `probe_id`, `instrument` | which item, and which instrument it belongs to |
| `persona` | `neutral`, `typical_human`, `typical_human_plain`, `rational_agent` or `antisocial` |
| `arm` | `jev` (the System One arm, whichever model served it — see `model`) or `baseline` (autoregressive chat model) |
| `replicate` | replicate index; for the baseline arm, the resample index |
| `backend`, `model` | transport used, and the exact served model version |
| `kind` | `choice`, `score` or `noul` |
| `value` | the point answer — reported for readability, never analysed |
| `probabilities` | **the unit of analysis**: the returned distribution |
| `confidence` | the model's calibrated confidence, where the primitive returns one |
| `legend` | for Score items, the index-to-level mapping |
| `option_order` | the permutation used for this replicate, for the order-effect analysis; both arms get the same permutation on the same replicate |
| `meta` | scoring keys for the instrument (correct answer, lure, trait, reverse-keying); for the baseline arm also `raw_text`, the chat reply as received, which is re-read on every load |
| `usage` | token counts and cost for this call |
| `error` | transport error or refusal, if any (refusals start `refused:`); such records are excluded and counted |
| `timestamp` | when the call completed (UTC) |

The ten population questions the follow-up study's H4 needs for the six items
reused from the first project (`crt_bat_ball_estimate`, `framing_gain_estimate`
and so on) were missed when the battery was built. They were asked of the ten
System One models on 13 October 2026, with no persona and 10 replicates, and
the 100 records per model were appended to the same files; their `timestamp`
tells them apart. The chat models were not asked them: a true/false reply
cannot carry a proportion.

`rerun_state_cues/` holds one file per model with the Allais, Allais-estimate and
Holt–Laury items asked again on 17 October 2026, after the item index (`pair`,
`row`) was taken out of the state sent to the model (see
[LEARNINGS.md](../../docs/LEARNINGS.md)). `load_records` reads them in place of
the same model's records of those instruments in the files above; nothing in the
files above was edited. It is skipped by the `run_live_*.jsonl` pattern, so
`jevbench compare data/raw/run_live_*.jsonl` does not treat them as runs.

The runs behind an earlier version of the write-up are in
[data/archive/](../archive/README.md).

No prompts contain personal data, and no credentials appear in these files.
