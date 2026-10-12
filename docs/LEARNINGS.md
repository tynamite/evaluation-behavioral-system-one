# Learnings

What went wrong along the way, how it was found, and what it changed. Kept here
rather than in the README so the write-up describes the method as it is now;
nothing below is hidden, and every fix is regression-tested.

## The chat arm lost replies without counting them

Before the first committed run (18 Sep 2026), the chat arm had three defects,
all the same shape: a reply arrives, fails to parse, and disappears without
being counted as an error. The first capped replies at 8 tokens, truncating the
chat model into null content on 490 of 4,680 calls. The second raised that cap
only to 64, which still truncated 239, leaving 224 unresolved. Neither failed
at random — both concentrated on the numeric items where the model reasons
before answering, so the affected runs would have compared Jev against a
baseline missing precisely its hardest cases. The third matched option text by
substring, so on the p-beauty contest, whose options are the integers 0–100, a
reply of `"100"` could resolve to `"1"`.

All three are regression-tested, the cap is now 512 tokens by default and
configurable (`JEVBENCH_BASELINE_MAX_TOKENS`; Haiku 5.5 needed 4,096), and
`summary.json` reports unresolved replies and per-cell sample coverage so this
class of gap cannot go uncounted again. The committed run has no transport
errors and 9 unresolved replies (0.19%), against 224 (4.8%) before the fix;
even at 512, 8 Sonnet replies were cut off by the cap. Re-running moved no Jev
headline result by more than 0.04, but chat-arm results moved by up to 0.20, so
the earlier chat numbers would have been wrong, not just incomplete. Nothing
was counting unresolved replies at the time; that counter should have existed
from the first run.

Later, three smaller misreadings were found, now fixed and re-read from the
stored replies: a reply echoing the option line (`$1: Offer $1, keep $9`) was
read for its last amount, a reply declining the true/false format ("I can't
answer this with true or false") was read as *false*, and the follow-up items
that ask a chat model for a proportion as a true/false reply were scored as if
a vote were an estimate. Two Sonnet cells moved, neither reported here;
[MODELS.md](MODELS.md#how-a-chat-models-reply-becomes-an-answer) has the
detail.

## Method flaws found in an audit before publishing

An audit before publishing found flaws in how some items were put to the
models. All are fixed in the code. The runs of 18 Sep and 12 Oct 2026 predate
the fixes, so their numbers should be read with these in mind:

1. **The chat arm saw options in a fixed order.** Only the System One arm was
   shuffled. On every item with a right answer, the chat models saw the
   correct option listed first. Chat-arm accuracy on those items may be
   inflated, and the two arms are not on equal terms.
2. **Two items labelled their own condition.** The framing items carried
   `"frame": "gain"` / `"loss"` in the state sent to every model, chat arm
   included, and the anchoring items carried `"anchor_value"` alongside the
   anchor question. Labels like these tell a model which manipulation it is
   in.
3. **The sunk-cost item was a paraphrase, not Arkes & Blumer's wording.** It
   said the product would "now certainly lose money", which removes the
   uncertainty the original effect depends on and makes abandoning clearly
   right. The near-zero continuation under neutral framing, for every model,
   may owe a lot to that. The item now uses the original radar-blank-plane
   wording (Experiment 3, Question 3A).
4. **The 11-20 game hinted at its strategy.** The option for 20 was labelled
   "the largest amount, but never earns the bonus". Options are now plain.
5. **The categorisation follow-up item had a duplicated exemplar and a note
   explaining its structure** (12 Oct runs only; no result from it is
   reported). One Group 2 member was identical to a Group 1 member, and the
   prompt described which group shares a rule. Both are fixed, following the
   Many Labs 2 protocol.
6. **The `typical_human` instruction steers as well as asks**: "not the textbook-correct answer" tells the model
   which way to move on items with a right answer.
   A neutral version is added for the next run.
7. **Two deviations from the preregistered analysis plan.** It promised 95%
   bootstrap intervals; `statistics.csv` carries them for the multi-item
   measures, but no document reports them. And it said the only exclusions
   would be transport errors; chat replies that could not be read, model
   refusals, and chat replies to the proportion items (which a true/false reply
   cannot answer) are excluded too, each counted in `summary.json` or
   `health.csv`.

The benchmark comparisons were also tightened before publishing, and the
committed tables are recomputed with them: the CRT human value covers only
Frederick's three items, so the comparison now uses those three (all six are
reported separately); the ultimatum rejection value is compared with the $1
offer only; and an unsourced present-bias reference value was dropped.

## Smaller corrections

- **Option-order effects were first averaged over the wrong items.** An early
  version reported a mean total-variation distance of 0.051 by averaging in
  Likert and yes/no items, which are never shuffled. On the shuffled
  multiple-choice items alone it is 0.062.
- **The model comparison changed order when the benchmarks were tightened.**
  With all six CRT items and both the $0 and $1 ultimatum offers, Solar Decide
  Flash came out closest to people under neutral framing; on the like-for-like
  measures Clef Flash does. Neither is a ranking (see
  [MODELS.md](MODELS.md#why-the-top-of-that-table-should-not-be-read-as-a-ranking)).
- **Refusals were first logged as transport errors.** One model's route reports
  a refusal as HTTP 502, so each was tried five times before being recorded.
  Refusals are now recorded once and never retried.
- **An interrupted run lost everything.** Records were written only at the end
  of a run; they are now written as each completes, and `jevbench run --resume`
  finishes an interrupted run.
