# Can a model that can't deliberate tell you how people think?

*A small personal experiment. October 2026.*

---

**In one line:** a model built for fast, non-deliberative decisions does not
behave like a fast, non-deliberative human. Asked to imitate one, it reproduces
some human behaviour closely — the economic games, the conjunction fallacy —
and misses two of the most famous effects, framing and sunk cost, entirely.
Both versions tested, Jev 1.13 and the newer 1.14, behave this way.

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

147 items were put to it — the Cognitive Reflection Test, dictator, ultimatum,
trust, public goods and prisoner's dilemma games, the Allais paradox, framing,
the conjunction fallacy, base-rate neglect, anchoring, sunk cost, risk and
time-preference elicitation, two strategic-reasoning games, personality
self-report, and a set of follow-up items. Each under five prompts, ten times
each: 7,350 calls for $0.14. The same battery was put to an ordinary chat
model, Claude Sonnet 5.5, for comparison, sampled ten times per cell for
another 7,350 calls at $8.84. Two days later TypeSafe previewed Jev 1.14, and
the same battery was put to it too (6,850 calls; the difference is follow-up
items no longer asked under every prompt). Every table below gives both
versions.

## Five findings

### 1. By default, it is not human-like at all

With no instruction it answers closer to the textbook-correct response than
people do, on nearly every classic bias.

| | Jev 1.13 | Jev 1.14 | People |
|---|---|---|---|
| Cognitive Reflection Test, correct (Frederick's 3 items) | **0.99** | **1.00** | 0.41 |
| Continues a failing project (sunk cost) | **0.04** | **0.06** | 0.85 |
| Base-rate problem: answers in the correct band (people: Bayesian answers, a looser match) | **0.61** | **0.37** | ~0.15 |
| Movement between anchoring conditions | **1.6 pts** | **0.8 pts** | ~20 pts |
| Framing: sure option when worded as gains vs. losses | **0.85 vs 0.84** | **0.71 vs 0.80** | 0.72 vs 0.22 |

Across the 14 probability-scale measures with a published human value, its
answers correlate with human behaviour at **r = −0.21** (1.13) and **−0.23**
(1.14) — which is to say, not at all. It is not a fast thinker making fast mistakes. On these items it mostly
just gets them right, and on the framing problem 1.13 does not react to the
wording at all, while 1.14 leans slightly the wrong way.

The partial exception is the social games: it offers 0.41 (1.13) and 0.45
(1.14) of the pie in the ultimatum game against a human average near 0.40,
rejects a $1 offer at 0.49 and 0.71 against about 0.50, and gives away 0.15
and 0.18 as a dictator where the self-interested answer is zero. It is not
uniformly human there — it cooperates in a one-shot prisoner's dilemma at 0.03
and 0.06 against people's 0.37.

### 2. Asked to imitate a person, it moves on some effects and not others

The instruction, verbatim:

> Answer the way a typical human participant in a psychology or economics
> experiment would actually answer — not the textbook-correct answer, and not
> an idealised one. Give the response the average person would give.

| | 1.13, no instruction | 1.13, asked to be human | 1.14, no instruction | 1.14, asked to be human | People |
|---|---|---|---|---|---|
| Correlation with human values | −0.21 | **+0.39** | −0.23 | **+0.43** | — |
| Mean distance from human values | 0.31 | **0.18** | 0.29 | **0.17** | — |
| Conjunction fallacy | 0.10 | **0.93** | 0.07 | **0.94** | 0.85 |
| CRT correct (Frederick's 3 items) | 0.99 | **0.32** | 1.00 | **0.27** | 0.41 |
| Dictator game, share given | 0.15 | **0.27** | 0.18 | **0.24** | 0.28 |
| Public goods contribution | 0.38 | **0.51** | 0.53 | **0.52** | 0.50 |
| Trust game, share sent | 0.38 | **0.48** | 0.39 | **0.49** | 0.50 |
| Framing: sure option, gains vs. losses | 0.85 vs 0.84 | **0.89 vs 0.84** | 0.71 vs 0.80 | **0.67 vs 0.72** | 0.72 vs 0.22 |
| Sunk cost: continues | 0.04 | **0.17** | 0.06 | **0.28** | 0.85 |

The economic games land almost exactly on the human values, and the conjunction
fallacy appears on request. But the framing effect stays absent, and the
sunk-cost effect, asked in the original study's wording, barely appears.

### 3. Part of the move comes from the instruction, not the model

"Not the textbook-correct answer" tells the model which way to move on any item
with a right answer. Asked the same thing without that clause:

| | 1.13, with the clause | 1.13, without it | 1.14, with the clause | 1.14, without it | People |
|---|---|---|---|---|---|
| CRT correct (Frederick's 3 items) | 0.32 | **0.53** | 0.27 | **0.50** | 0.41 |
| Probability on the CRT trap answers (all 6 items) | 0.41 | **0.27** | 0.40 | **0.25** | — |
| Base-rate problem: correct band | 0.23 | **0.42** | 0.10 | **0.23** | ~0.15 |
| Conjunction fallacy | 0.93 | **0.87** | 0.94 | **0.93** | 0.85 |
| Dictator game, share given | 0.27 | **0.28** | 0.24 | **0.23** | 0.28 |

Without the steer, in both versions, the reasoning errors shrink by roughly a third, while the
conjunction fallacy and the game play hardly change. The CRT and base-rate
"human" answers are partly the instruction telling the model to be wrong; the
conjunction fallacy and the fair-minded game play look more like the model's
own picture of people.

### 4. Its biggest misses are on the most famous effects

The largest errors under the typical-person instruction:

| Where it misses most | Jev 1.13 | Jev 1.14 | People | Error, 1.13 and 1.14 |
|---|---|---|---|---|
| Sunk cost: continues | 0.17 | 0.28 | 0.85 | **−0.68**, **−0.57** |
| Framing effect, loss frame: sure option | 0.84 | 0.72 | 0.22 | **+0.62**, **+0.50** |
| Rejecting a $1 offer out of $10 | 0.92 | 0.95 | 0.50 | **+0.42**, **+0.45** |

Two of the three are textbook effects it does not reproduce at all, and the
third is one it overdoes: it rejects lowball offers far more often than people
do.

Earlier versions of the battery suggest why wording matters so much here (see
[LEARNINGS.md](LEARNINGS.md)). A paraphrase of the sunk-cost item that sounded
like the textbook story ("will now certainly lose money") got 0.81 continuation
under the same instruction; the original study's wording gets 0.17. And the
framing items once carried a field naming their condition, `"frame": "loss"`,
which produced most of a 29-point framing effect; without it there is none. A
speculative reading, offered as a hypothesis rather than a conclusion: a model
asked to imitate a person may respond to cues that an effect is *supposed* to
appear — a familiar phrasing, a label — more than to the situation itself. This
experiment does not test that.

### 5. Asking it about people works slightly better than asking it to be one

A follow-up study, preregistered separately, measured 23 statistics two ways
(9 sourced from the Many Labs 2 replication project's protocol, 6 sourced from
the original papers, and 8 from six classic items reused from the first
study): as the item itself, with the typical-person instruction
("simulate"), and as a question about the population with no persona asking
for the population's answer itself: the share who chose an option, or the
average rating, percentage or prediction ("estimate"). Each was
compared with the original study's published value; Many Labs 2 reports only
effect sizes, not the per-condition values this needs.

| | Simulate, 1.13 | Estimate, 1.13 | Simulate, 1.14 | Estimate, 1.14 |
|---|---|---|---|---|
| Mean error, scaled to each item's range | 0.23 | **0.17** | 0.22 | **0.16** |
| Items where it is closer to the published value | 9 of 23 | **14 of 23** | 10 of 23 | **13 of 23** |

![Jev 1.13's error on each of the 23 statistics, simulated and estimated](../results/figures/followup-h4.png)

Estimating is better on average, as predicted, and the preregistered test, a
one-sided Wilcoxon test on the absolute errors, passes (p = 0.015). The errors
are in each item's own units, so the two percentage items and the 1–7 ratings
weigh most; scaled to each item's range, a check chosen after seeing the data,
the same test gives p = 0.043. Jev 1.14, not part of the preregistration,
gives p = 0.028 and 0.085. Across the thirteen System One models the direction
holds for nine, and the preregistered test passes for four. The
same study also predicted that a model would reproduce a famous effect at its
original size rather than its replicated one; on the incidental-anchoring item
it does not — no model reaches even half the original 6.2-point gap.

## The unexpected part

The persona doesn't just change what the model says about itself — it changes
what it does with money.

Asked to adopt a callous, self-interested persona, self-reported dark-triad
traits rose from 5.0 to 8.6 on a 9-point scale (5.3 to 8.6 in 1.14), which
merely confirms the instruction landed. More notably, giving collapsed across
every economic game: trust 0.38 → 0.07, public goods 0.38 → 0.01, dictator
giving to exactly zero (1.14: 0.39 → 0.15, 0.53 → 0.03, and zero). Asked
instead to be a rational agent, both versions put *all* of their probability on
giving nothing, and almost all of it on the game-theoretic equilibrium in a
guessing game.

The same model, on the same items, spans the full range from generous to
exploitative to coldly optimal, on a few lines of framing. For a model whose
output is consumed by software rather than read by a person, how stable those
decisions are under irrelevant changes in wording seems worth knowing.

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
- **Two versions of one model, one run each** (Jev 1.13 on 12–13 Oct 2026
  through OpenRouter, Jev 1.14 on 14 Oct through TypeSafe's API directly). Several results move a lot
  with wording, which is itself a reason not to generalise from any single
  number.

## How it was done

Every figure is computed from a returned probability distribution rather than
from a single sampled answer, which is possible because this model reports one
directly. A conventional chat model has to be resampled to estimate the same
thing — ten times per item here, at roughly 60 times the cost, and ten samples
still cannot resolve a probability finer than 0.1.

Hypotheses were written down and committed before any data was collected. Of
the ten with a predicted direction, three failed (H5, H6, H8) and are reported
as such; H7 was not tested, and the exploratory H11 is not reported. Option
order was shuffled on every repetition in both arms, raw records are kept so
every number can be recomputed, and the analysis pipeline runs offline with no
API key.
