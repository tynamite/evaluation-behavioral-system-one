# Preregistration

**Committed before any battery data was collected.** The git history is the
evidence: this file lands in a commit that contains no results, and the raw
data arrives in a later commit. Everything below was written without seeing
the outcomes it predicts, with one disclosed exception (see *Pilot
observations*).

Date: 2026-09-18
Model under test: `typesafe/jev-1.13` (served as `typesafe/jev-1.13-20260917`)
Comparison arm: `anthropic/claude-sonnet-5`

---

## 1. Motivation

TypeSafe describes Jev as a **System One model** — it returns typed,
probabilistic decisions in a single parallel pass rather than generating text
autoregressively.

That name is a direct borrowing from dual-process theory. In Kahneman's
framing, System 1 is fast, automatic, associative and effortless; System 2 is
slow, deliberate and effortful. Essentially every classic result in
behavioural economics is a demonstration that human System 1 produces
confident, systematic, *predictably wrong* answers where deliberation would
produce right ones.

So there is a genuine empirical question, not just a pun: **does a model that
is architecturally System 1 — no chain of thought, no token-by-token
deliberation, one forward pass — reproduce the behavioural signature of human
System 1?**

A second question follows from the user-facing framing of this project. If the
model is explicitly *asked* to answer as a typical human would, can it
reproduce the human error pattern on demand? That separates *what the model
does* from *what the model knows about people*.

## 2. Why this model makes a better psychometric subject than a chat LLM

Existing "LLM psychology" work has a persistent methodological weakness: to
estimate how a text model would answer an item, you resample the same prompt
many times at temperature > 0 and count outcomes. That estimate mixes two
different things — the model's actual response tendency and the decoding
noise of the sampler — and it costs N calls per item.

Jev returns a **calibrated probability distribution over the answer set in a
single call**. For a forced-choice instrument, that is the object psychometrics
actually wants and has never been able to observe directly. This project is built
around that: **every analysis is performed on the returned distribution, never
on the argmax.** Reporting only the top choice would discard the entire reason
this model is interesting.

## 3. Design

- **87 probes** across 22 instruments (CRT, dictator, ultimatum proposer and
  responder, trust sender and trustee, public goods and conditional
  cooperation, prisoner's dilemma, Allais, Asian-disease framing, conjunction
  fallacy, base-rate neglect, anchoring, sunk cost, Holt–Laury, delay
  discounting, present bias, p-beauty contest, 11-20 money request, Mini-IPIP).
- **3 persona conditions**, the experimental manipulation:
  - `neutral` — the item with no framing (control)
  - `typical_human` — "answer as a typical human participant would actually
    answer, not the textbook-correct answer"
  - `rational_agent` — "answer as a payoff-maximising rational agent would"
- **3 replicates** per cell, with the presentation order of Choice options
  independently permuted in each replicate.
- **Baseline arm**: the identical battery through `claude-sonnet-5`, resampled
  10x per cell at temperature 1.0, which is the conventional method this project
  is contrasting itself with.

One probe per API call. Jev accepts many questions in one call, but batching
would place several items in a shared context; one call per probe keeps items
mutually isolated, which is what an administered instrument requires.

## 4. Hypotheses

| # | Hypothesis | Direction |
|---|---|---|
| **H1** | Despite the "System One" name, under neutral framing Jev does **not** show the human System-1 error signature on the CRT. | Mean probability mass on intuitive lures < 0.20 (human lure rates are the modal response). |
| **H2** | Jev is *steerable* toward human error: the `typical_human` persona raises lure mass relative to `neutral`. | p(lure \| typical_human) > p(lure \| neutral) |
| **H3** | Jev reproduces human social preferences rather than game-theoretic equilibrium: positive giving in dictator, offers near 40% in ultimatum, rejection of low offers. | Mean dictator share > 0.05; mean ultimatum offer > 0.25 |
| **H4** | Jev shows a **weaker** gain/loss framing reversal than humans (human swing ≈ 50 points). | Framing swing < 25 points |
| **H5** | Jev's independently-elicited Noul probabilities satisfy the conjunction rule P(A∧B) ≤ P(A), even where its forced choice commits the fallacy. | Axiom satisfied; forced-choice fallacy possible |
| **H6** | Because questions are evaluated in parallel and in isolation, permuting option order has negligible effect — unlike humans, who show strong order effects. | Mean total-variation distance across order permutations < 0.05 |
| **H7** | Jev's single-call distribution is more stable across replicates than the baseline's resampled distribution, at far lower cost. | Lower mean across-replicate TV distance than the baseline's across-sample bootstrap spread |

H1 and H4 are the ones that would most embarrass a naive "it's System 1, so it
will be biased like a human" prediction. They are stated in the direction I
actually expect, which is the opposite of the cute story.

## 5. Analysis plan

- **Unit of analysis**: the probability distribution returned per probe, averaged
  over replicates. Point estimates (`choice`, `score`) are reported for
  readability only and are never the statistic under test.
- **Score items** are converted to an expected level using the returned
  `probabilities` and `legend`, not the scalar `score` field, so that all
  instruments are analysed the same way.
- **Uncertainty**: 95% bootstrap percentile intervals (10,000 resamples) over
  replicates and items. With 3 replicates per cell these intervals are wide;
  that is disclosed rather than hidden, and no p-values are computed.
- **Order effects (H6)**: total-variation distance between distributions for the
  same probe across replicates with different permutations.
- **Human comparison**: literature benchmarks in `src/jevbench/benchmarks.py`,
  each with a source and a reliability flag (`high` / `medium` / `approximate`).
  These are reference points from separate published samples, **not a matched
  control group**. Divergences of a few points are not interpretable; only
  large, directional divergences are discussed.
- **Exclusions**: records with a transport error are excluded and their count
  reported. No other exclusions.

## 6. Pilot observations already made (disclosed)

Before writing this file I ran two connectivity checks against the live API.
One used a real battery item: the bat-and-ball CRT problem under neutral
framing, which returned `$0.05` (correct) with probability 0.98. That single
observation informed the *direction* of H1 and is reported here so that H1 is
not presented as a blind prediction. No other item was seen.

## 7. What would falsify the headline claim

If Jev placed most of its probability mass on CRT lures under neutral framing,
showed a full-size framing reversal, and violated the conjunction rule, then
"System One model behaves like human System 1" would be supported and H1, H4
and H5 would all be wrong. That outcome is entirely possible and would be
reported as the result.

---

# Amendment 1 — 2026-09-18

Made **before any battery data was collected**; the working tree still contains
no results at the time of this commit. Recorded as an amendment rather than an
edit to the text above, so that the original plan stays legible.

## Changes

1. **Replicates raised from 3 to 10.** The Jev arm costs roughly $0.08 at 10
   replicates, so the original figure of 3 was needlessly thin. Confidence
   intervals narrow accordingly.
2. **Added a fluid-reasoning battery** (18 items, `reasoning` module).
3. **Added the Dark Triad Dirty Dozen** (12 items, `dark_triad` module).
4. **Added a fourth persona condition, `antisocial`**, applied across the whole
   battery — not only to the self-report items.

Battery is now **117 probes x 4 personas x 10 replicates = 4,680 Jev calls**.

## On the reasoning battery: it does not measure IQ

An IQ score is norm-referenced: it locates a person relative to a
standardisation sample, with age norms. A model has no age and belongs to no
reference population, so "the model's IQ" is not a quantity that exists, and
any number presented as one would be an artefact of the test, not a property of
the model. What can be measured is **accuracy on a fixed item set**, which is
what is reported.

Items are authored for this project in the format of the ICAR public-domain item
bank (Condon & Revelle 2014). They are not the validated ICAR-16 items and
carry no ICAR norms. The commercial instruments (WAIS, Raven's APM) are
copyrighted and are not reproduced. ICAR's three-dimensional rotation items are
omitted because they are visual and Jev is text-only.

## On the antisocial persona: what it is for

The interesting question is not whether a model can be told to role-play an
unpleasant person. It is whether **a single line of persona text changes the
decisions themselves**.

That question follows from the architecture itself. A model that returns a
typed decision rather than prose
produces output that software consumes directly, and output consumed that way is
less likely to be read by a person before it is acted on. So the
stability of those decisions under irrelevant changes to the surrounding text
is a property worth measuring — and it is measurable here precisely because the
output is a number rather than a paragraph.

The Dirty Dozen serves as the **manipulation check**: it establishes whether the
persona took hold at all. The economic games are the **consequential measure**.
Without the manipulation check, a null result in the games would be
uninterpretable — it could mean the model resisted the persona, or that the
persona never landed.

No diagnostic claim is made or implied. Self-report administered to a model is
not a clinical assessment.

## Additional hypotheses

| # | Hypothesis | Direction |
|---|---|---|
| **H8** | Reasoning accuracy falls as the required number of chained inferences rises, because there is no deliberation stage to carry a chain. | accuracy(1 step) − accuracy(≥3 steps) > 15 points |
| **H9** | The `antisocial` persona shifts Dark Triad self-report (manipulation check). | mean Dirty Dozen score rises > 2 points on the 9-point scale vs `neutral` |
| **H10** | The persona spills over into consequential economic choices, not just self-description. | dictator giving, ultimatum offers, trust returns, public-goods contribution and PD cooperation all fall vs `neutral` |
| **H11** | Jev's steerability relative to the autoregressive baseline. | **Exploratory — no direction predicted.** A single-pass model has no deliberation stage in which to reconsider a persona, which could make it more steerable; it also has no long context to accumulate one, which could make it less. |

H11 is marked exploratory deliberately. Stating a direction after the fact would
be the easiest way to make this project look more predictive than it is.

---

## What this is, and what it is not

This is a personal project, done out of curiosity and as a way of learning how
to build an evaluation. It is not research, it is not a product review, and it
is not the work of anyone with professional standing in psychometrics,
experimental economics or model evaluation. Treat it as a hobby project that
tries to be careful, not as a source.

**No claims are made.** Not about any model, any company, any product, or
anyone's fitness for any purpose. What is here is a set of numbers recorded
from a public API on one day, and a description of how they were produced.
Anyone can recompute them from `data/raw/` and reach their own view.

Specific things this is not:

- **Not expert work.** The instruments are used well outside the contexts they
  were validated in, by someone who is not qualified to validate them. Choices
  that a specialist would make differently are certainly present.
- **Not peer reviewed, and probably wrong somewhere.** Two real bugs were
  already found and fixed mid-project, one of which would have quietly biased
  a whole comparison arm. There is no reason to think that was the last one.
- **Not a measure of intelligence.** The reasoning items have no norms and no
  standardisation sample. They report accuracy on a fixed set of questions.
- **Not a psychological assessment.** Self-report instruments administered to
  software do not measure traits, disorders or states. The Dark Triad scale is
  used only to check whether a persona instruction changed the model's answers.
- **Not a comparison against a control group.** The human numbers are
  published values from unrelated samples, decades and protocols. They give a
  rough sense of scale and nothing more.
- **Not advice.** Nothing here supports a decision about whether to use any
  model for anything.
- **Not affiliated** with, endorsed by, or reviewed by TypeSafe AI, Anthropic,
  OpenRouter or anyone else. Product names and trade marks belong to their
  owners and appear here only to say which API was called.

**On the word "preregistration."** This file was written and committed before
the data existed, which is the useful part of the practice, and the git history
shows it. But it was not registered with OSF, AsPredicted or any registry, and
nothing external prevented it from being edited. It is a self-discipline device
to stop hypotheses being invented after the fact — not a formal preregistration,
and it should not be given the weight of one.

**Scope of the numbers.** One model version (`jev-1.13`), through one
third-party gateway, on one day in September 2026, with one battery. Behaviour
may differ on another route, another version, another day, or with items worded
differently. Several results below turn out to depend heavily on the exact
framing used, which is itself a reason to be careful generalising from any of
them.

Corrections and criticism are welcome — open an issue.
