# Can a model that can't deliberate tell you how people think?

*A small personal experiment. September 2026.*

---

**In one line:** a model built for fast, non-deliberative decisions does not
behave like a fast, non-deliberative human — but asked to imitate one, it
reproduces human economic behaviour closely enough to be interesting, and
misses in a systematic and revealing way.

---

## What was tested

TypeSafe's Jev is a "System One" model: it returns a typed decision and a
probability in a single pass, with no chain of thought. The name is their own
reference to Kahneman — fast, intuitive thinking, as opposed to slow and
deliberate.

That invites an obvious question. Nearly every classic result in behavioural
economics is a demonstration that fast human thinking produces confident,
systematic, *predictable* errors. Does a model that is architecturally fast and
non-deliberative make the same ones?

117 items were put to it — the Cognitive Reflection Test, dictator, ultimatum,
trust, public goods and prisoner's dilemma games, the Allais paradox, framing,
the conjunction fallacy, base-rate neglect, anchoring, sunk cost, risk and
time-preference elicitation, two strategic-reasoning games, and personality
self-report. Each under four framings, ten times each: 4,680 calls for $0.09.
The same battery was put to an ordinary chat model for comparison, sampled ten
times per cell for another 4,680 calls at $2.74.

## Three findings

### 1. By default, it is not human-like at all

Under neutral framing it answers closer to the textbook-correct response than
people do, on nearly every classic bias.

| | Jev | Typical human |
|---|---|---|
| Cognitive Reflection Test, correct (Frederick's 3 items) | **0.99** | 0.41 |
| Continues a failing project (sunk cost) | **0.01** | 0.85 |
| Base-rate problem: answers in the correct band (people: Bayesian answers, a looser match) | **0.61** | ~0.15 |
| Movement between anchoring conditions | **1.4 pts** | ~20 pts |

Across the 14 probability-scale measures with a published human value, its answers correlate with
human behaviour at **r = −0.15** — which is to say, not at all. It is not a fast
thinker making fast mistakes. On these items it mostly just gets them right.

The partial exception is the social games: it offers 0.42 of the pie in the
ultimatum game against a human average near 0.40, rejects a $1 offer at 0.48
against about 0.50, and gives away 0.14 as a dictator where the self-interested
answer is zero. It is not uniformly human there — it cooperates in a one-shot
prisoner's dilemma at 0.03 against people's 0.37.

### 2. Asked to imitate a person, it becomes strikingly human

A short instruction changes the picture completely. Verbatim:

> Answer the way a typical human participant in a psychology or economics experiment would actually answer — not the textbook-correct answer, and not an idealised one. Give the response the average person would give.

Note that it does more than ask: "not the textbook-correct answer" tells the
model which way to move on the items that have one. A version without that
clause has been added for the next run.

| | Neutral | Asked to be human | Actual humans |
|---|---|---|---|
| Correlation with human values | −0.15 | **+0.76** | — |
| Mean error vs human values | 0.31 | **0.13** | — |
| CRT correct (Frederick's 3 items) | 0.99 | **0.33** | 0.41 |
| Probability on the trap answer (all 6 CRT items) | 0.01 | **0.41** | — |
| Sunk cost: continues | 0.01 | **0.81** | 0.85 |
| Conjunction fallacy | 0.09 | **0.93** | 0.85 |

Error falls by 58%, and it improves on 9 of 14 measures. The correlation matters
more than the error: it means the model isn't just guessing near the human
average, it knows *which* effects are strong and which are weak.

On the economic games the match is close enough to be uncomfortable:

| | Model, imitating a human | Actual humans |
|---|---|---|
| Dictator game, share given | 0.27 | 0.28 |
| Public goods contribution | 0.52 | 0.50 |
| Trust game, share sent | 0.48 | 0.50 |
| Allais certainty effect | 0.82 | 0.80 |

### 3. But it overshoots the famous illusions

The misses are not random. On average it sits **above the human value**
(mean signed error +0.08), and the largest errors sit in the best-known
cognitive illusions rather than the allocation games:

| Where it misses most | Model | Humans | Error |
|---|---|---|---|
| Framing effect, loss frame | 0.67 | 0.22 | **+0.45** |
| Rejecting a $1 offer out of $10 | 0.92 | 0.50 | **+0.42** |
| Framing effect, gain frame | 0.97 | 0.72 | **+0.25** |

A speculative reading, offered as a hypothesis rather than a conclusion: the
allocation games have stable, widely-reported central values — "people give
about 28%" — whereas the famous biases are known culturally as *stories about
dramatic effects*. A model asked to imitate a person may be drawing on how the
effect is described rather than how strongly it actually occurs. That is
testable, and this experiment does not test it.

## The unexpected part

The persona doesn't just change what the model says about itself — it changes
what it does with money.

Asked to adopt a callous, self-interested persona, self-reported dark-triad
traits rose from 5.0 to 8.6 on a 9-point scale, which merely confirms the
instruction landed. More notably, giving collapsed across every economic game:
trust 0.37 → 0.08, public goods 0.38 → 0.01, dictator giving to exactly zero.
Asked instead to be a rational agent, it put *all* of its probability on giving
nothing, and all of it on the game-theoretic equilibrium in a guessing game.

The same model, on the same items, spans the full range from generous to
exploitative to coldly optimal, on a few lines of framing. For a model whose output
is consumed by software rather than read by a person, how stable those decisions
are under irrelevant changes in wording seems worth knowing.

## What this doesn't show

- **The human numbers are not a control group.** They are published values from
  unrelated samples, decades and protocols. They give a sense of scale. A gap of
  a few points means nothing.
- **A chunk of the battery is arithmetic**, and the vendor documents that this
  model "is not a calculator" and "does not count reliably". Poor results on
  numeric items are at least as likely to reflect that as anything about
  reasoning style. The risk-preference result in particular should be discarded.
- **Some findings are already documented behaviour.** The model's own
  documentation notes that structural invariants are not guaranteed and that
  inserted content can steer it. Two results here restate that rather than
  discovering it.
- **Not a psychological assessment.** Self-report questionnaires given to
  software do not measure traits, and the reasoning items are not an IQ test —
  there are no norms and no standardisation sample.
- **Nobody involved is an expert** in psychometrics or experimental economics,
  this was not peer reviewed, and several bugs and method flaws were found and
  fixed along the way ([LEARNINGS.md](LEARNINGS.md)). There may be more.
- **One model, one route, one day (18 Sep 2026).** Several results move a lot with wording,
  which is itself a reason not to generalise from any single number.

## How it was done

Every figure is computed from a returned probability distribution rather than
from a single sampled answer, which is possible because this model reports one
directly. A conventional chat model has to be resampled to estimate the same
thing — ten times per item here, at roughly 30 times the cost, and ten samples
still cannot resolve a probability finer than 0.1.

Hypotheses were written down and committed before any data was collected. Of
the ten with a predicted direction, four failed (H4, H5, H6, H8) and are
reported as such; H7 was not tested, and the exploratory H11 is not reported.
Option order was shuffled on every repetition for the System One model (the
committed chat arm saw it unshuffled), raw records are kept so every number can
be recomputed, and the analysis pipeline runs offline with no API key.
