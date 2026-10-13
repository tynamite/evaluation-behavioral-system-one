# Learnings

What went wrong along the way, how it was found, and what it changed. Kept here
rather than in the README so the write-up describes the method as it is now;
nothing below is hidden, and every fix is regression-tested.

## The chat arm lost replies without counting them

Before the first run (18 Sep 2026), the chat arm had three defects,
all the same shape: a reply arrives, fails to parse, and disappears without
being counted as an error. The first capped replies at 8 tokens, truncating the
chat model into null content on 490 of 4,680 calls. The second raised that cap
only to 64, which still truncated 239, leaving 224 unresolved. Neither failed
at random — both concentrated on the numeric items where the model reasons
before answering, so the affected runs would have compared Jev against a
baseline missing precisely its hardest cases. The third matched option text by
substring, so on the p-beauty contest, whose options are the integers 0–100, a
reply of `"100"` could resolve to `"1"`.

All three are regression-tested, the cap is now 4,096 tokens by default and
configurable (`JEVBENCH_BASELINE_MAX_TOKENS`), and
`summary.json` reports unresolved replies and per-cell sample coverage so this
class of gap cannot go uncounted again. The 18 Sep run had no transport
errors and 9 unresolved replies (0.19%), against 224 (4.8%) before the fix;
even at 512 tokens, 8 Sonnet replies were cut off by the cap. Re-running moved no Jev
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
models. All were fixed in the code, and every model was then re-run (see
below); the earlier runs, now in [data/archive/](../data/archive/README.md),
predate the fixes:

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
   explaining its structure** (the archived 12 Oct runs only; no result from it is
   reported). One Group 2 member was identical to a Group 1 member, and the
   prompt described which group shares a rule. Both are fixed, following the
   Many Labs 2 protocol.
6. **The `typical_human` instruction steers as well as asks**: "not the textbook-correct answer" tells the model
   which way to move on items with a right answer. A version without the
   clause was added and is reported alongside it ("no steer").
7. **Two deviations from the preregistered analysis plan.** It promised 95%
   bootstrap intervals; `statistics.csv` carries them for the multi-item
   measures, but no document reports them. And it said the only exclusions
   would be transport errors; chat replies that could not be read, model
   refusals, and chat replies to the proportion items (which a true/false reply
   cannot answer) are excluded too, each counted in `summary.json` or
   `health.csv`.

The benchmark comparisons were also tightened before publishing: the CRT human value covers only
Frederick's three items, so the comparison now uses those three (all six are
reported separately); the ultimatum rejection value is compared with the $1
offer only; and an unsourced present-bias reference value was dropped.

## What the re-run changed

Every model was re-run on 12–13 October 2026 with the fixes above, the
plain typical-person prompt added, and Claude Sonnet 5.5 in place of Sonnet 5
as the chat baseline. For Jev, the same measures before and after:

| Jev 1.13 | Before the fixes | After |
|---|---|---|
| Framing swing, no instruction (people ≈ 50 points) | 29 points | **1 point** |
| Framing swing, as a typical person | 30 points | **4 points** |
| Sunk cost: continues, as a typical person (people 0.85) | 0.81 | **0.17** |
| Sunk cost: continues, no instruction | 0.01 | 0.04 |
| CRT correct, as a typical person (Frederick's 3 items) | 0.33 | 0.32 |
| Conjunction fallacy, as a typical person | 0.93 | 0.93 |
| Anchoring gap, as a typical person (people ≈ 20 points) | 7.0 points | 5.3 points |
| Correlation with human values, as a typical person | +0.76 | **+0.39** |
| Mean distance from human values, as a typical person | 0.13 | 0.18 |

Two changes account for most of the difference. The framing effect came
almost entirely from the `"frame"` label: without it, Jev picks the sure
option equally often in both wordings. And the sunk-cost effect under the
typical-person prompt came from the paraphrase: in Arkes and Blumer's own
wording it nearly disappears. Hypothesis H4 (a framing effect much weaker than
people's) failed in the first run and holds in the second.

The chat-arm numbers changed too, but they cannot be compared before and
after: the baseline model changed at the same time as its options started
being shuffled.

## Corrections after a review of the re-run

An outside review of the published repository (GitHub issue #2) found the
following, among other claims that did not check out against the code:

- **The trust game's last returning item could not return $10 or $20.** With
  $10 sent and $30 received, the options went up in $3 steps. It now offers
  whole dollars up to $15 and $2 steps above, plus $15, and that one item was
  re-run for every model; nothing else in the run files changed.
- **The follow-up study's population questions were asked under every
  prompt.** A population estimate is not a participant's answer, so a persona
  does not belong on it (FOLLOWUP_PREREGISTRATION.md, section 8.1). They are now
  asked with no persona; the records from other prompts stay in the run files.
- **The option-order figure (H6) included the follow-up items**, which H6 was
  not written for and which move less. The core battery's figure is 0.063, up
  from 0.058 with them; H6 fails either way.
- **The analysis figures left out the no-steer prompt.** They now include it.
- **H4 was first reported on a scale the preregistration did not name.** It
  registers the absolute error against the human value; the first report
  divided each error by its item's range, which changes the test's ranks, and
  gave p = 0.17 for Jev. The registered test gave 0.047. Both are now
  reported, the scaled one as a check chosen after seeing the data.
- **The trust game's missing $10 also hid Sonnet's answers.** Under the
  typical-person prompt, Sonnet 5.5 answered "$10" six times on the last
  returning item; with no such option those replies could not be read, and
  they were 6 of its 9 unresolved replies. With $10 on the menu they resolve,
  and Sonnet's unresolved count is 3.
- **H4 was first tested on part of its item pool.** The preregistration's
  pool includes six items reused from the first project, but their
  population questions had never been built. They were built and asked of the
  ten System One models on 13 October (1,000 calls), which moved Jev from 8 of
  15 (p = 0.047) to 14 of 23 (p = 0.015).

## Smaller corrections

- **Option-order effects were first averaged over the wrong items.** An early
  version reported a mean total-variation distance of 0.051 by averaging in
  Likert and yes/no items, which are never shuffled. On the shuffled
  multiple-choice items alone it was 0.062 in the first run (0.058 in the
  re-run).
- **The model comparison changed order when the benchmarks were tightened.**
  With all six CRT items and both the $0 and $1 ultimatum offers, Solar Decide
  Flash came out closest to people under neutral framing; on the like-for-like
  measures Clef Flash did, and in the re-run the two tie. Neither is a ranking (see
  [MODELS.md](MODELS.md#why-the-top-of-that-table-should-not-be-read-as-a-ranking)).
- **Refusals were first logged as transport errors.** One model's route reports
  a refusal as HTTP 502, so each was tried five times before being recorded.
  Refusals are now recorded once and never retried.
- **An interrupted run lost everything.** Records were written only at the end
  of a run; they are now written as each completes, and `jevbench run --resume`
  finishes an interrupted run.
