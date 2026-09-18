# Preregistration — Follow-up study: fame, replication status, and simulated human behaviour

*Committed before any item in this battery has been run and before the five
new items below have been built — the git history is the evidence. The
[preregistration for the first project](PREREGISTRATION.md) explains why this
matters and what it does and doesn't establish.*

Date: 2026-09-19
Model under test: `typesafe/jev-1.13` (or whatever is current when run)
Comparison arm: a chat model on the same terms as the first project
Human reference: **Many Labs 2** (Klein et al., 2018, *Advances in Methods and
Practices in Psychological Science*), 28 preregistered replications across 125
samples, ~15,300 participants, one shared protocol. Project:
[osf.io/8cd4r](https://osf.io/8cd4r/) · effect-size table:
[osf.io/h6dra](https://osf.io/h6dra/) · full protocol (item wording and
original-study numbers for every effect):
[projectimplicit.net/nosek/ML2protocol.pdf](https://www.projectimplicit.net/nosek/ML2protocol.pdf)

## 1. What this corrects in the first project

The first project's headline claim — "asked to imitate a person, the model
gets closer to real human behaviour, but overshoots the famous illusions" —
has fame, response format, and effect size all moving together. It also
scored against literature values from unrelated samples and decades. This
design fixes both: one shared protocol for the human numbers, and pairs of
items matched on format and magnitude that differ mainly in fame.

## 2. The sharper question that fell out of reading ML2's own numbers

Some textbook-famous effects barely replicated in ML2: incidental anchoring
(Critcher & Gilovich), d = 0.30 originally, **d = 0.04 replicated** —
essentially gone. Some obscure effects replicated strongly: moral typecasting
(Gray & Wegner), d = 0.80–0.85 originally, **d ≈ 0.95 in ML2's own summary**.
Fame and *current, real effect size* are therefore not the same axis, and the
design tests both:

- **H-fame**: simulated-human error scales with an item's fame, independent of
  its ML2-replicated effect size.
- **H-currency**: the model's simulated answer tracks the *original textbook*
  number rather than the *ML2-replicated* number, even where the two now
  disagree sharply (anchoring is the decisive case: does simulating "a typical
  participant" reproduce something close to Critcher & Gilovich's original
  gap, or the near-zero gap ML2 actually found?).

H-currency is the more damaging test for "the model knows how people behave,"
and it did not exist in the first project's design.

## 3. Design

**Three elicitations per item, all on existing primitives — no schema
changes:**

| Elicitation | Framing | Primitive |
|---|---|---|
| Own answer | neutral | `Choice` / `Score` |
| Simulate | "answer as a typical participant would" | same |
| Estimate | "what proportion of participants gave answer X?" | `Noul` or `Score` band |

**Fame index**, computed before any model call and independent of anything the
model outputs: (a) citation count of the canonical paper on Google Scholar,
(b) a binary presence/absence flag in each of three named books — *Thinking,
Fast and Slow*, *Predictably Irrational*, *Nudge* — via index lookup, (c) one
separate model-rated familiarity item per effect ("how well-known is this
finding to a general audience", `Score` 1–5), averaged over 5 replicates.
Items where the three disagree by more than one tier are dropped rather than
argued over.

**Pairing rule**, fixed before any data exists so no pair is chosen after
seeing results: within each response-format group (`Choice`-binary,
`Score`-rating), rank items by ML2-replicated proportion/effect size and by
fame index; pair each item with its nearest neighbour on magnitude from the
*opposite* fame tercile. This is a matching algorithm, not a hand-picked list
— the item pool below is fixed, but which items pair with which is decided by
the rule, applied once the fame index is in.

**Unit of analysis**: paired difference in absolute error between the two
elicitations (simulate, estimate) against the human value, tested with a
Wilcoxon signed-rank test given the small N (no assumption of normality with
12–16 pairs).

**Exclusions**: same as the first project — transport errors reported and
excluded, no other exclusions.

## 4. Item pool

### 4.1 Reused verbatim from the first project (already built, already sourced)

No new construction. Human values already in `benchmarks.py`.

| Item | Primitive | Human value | Source |
|---|---|---|---|
| CRT (6 items) | Choice | 0.41 correct | Frederick 2005 |
| Framing / Asian disease | Choice | 0.72 gain / 0.22 loss | Tversky & Kahneman 1981 |
| Conjunction fallacy (Linda) | Choice | 0.85 | Tversky & Kahneman 1983 |
| Sunk cost | Choice | 0.85 continue | Arkes & Blumer 1985 |
| Allais paradox | Choice | 0.80 / 0.35 | Kahneman & Tversky 1979 |
| Base rate (mammogram) | Choice | 0.15 correct | Eddy 1982 |

### 4.2 New — sourced from the original papers directly

| Item | Primitive | Human value | Source |
|---|---|---|---|
| Intentional side effects (Knobe) | Choice or Noul, 2 items | 0.82 harm / 0.23 help | Knobe 2003 |
| Trolley: switch vs. push | Choice, 2 items | 0.89 permit switch / 0.11 permit push | Hauser et al. 2007 |
| False consensus (sign-wearing) | Noul or Score band | wearers predict 0.61 / non-wearers predict 0.30 | Ross, Greene & House 1977 |

### 4.3 New — sourced from ML2's own preregistered protocol (this pass)

Every number below is quoted from the ML2 protocol itself, which describes
exactly which study, condition and dependent variable ML2 replicated —
removing any ambiguity about which of a paper's several studies is the right
one to match.

**Moral typecasting** (Gray & Wegner 2009, Study 1a, N=69). A man or a baby
knocks over a tray of glasses, harming the other. `Score`, 1–7, "how
responsible is [X] for the behaviour" (7 levels, fits the primitive directly).

| Condition | Human mean (1–7) | SD |
|---|---|---|
| Man commits the act | 5.29 | 1.86 |
| Baby commits the act | 3.86 | 1.64 |

Secondary DVs from the same study, for a robustness check rather than the
primary test: intentionality (man 4.05 / baby 3.07) and pain felt by the
victim (man-as-victim 4.63 / baby-as-victim 5.76 — the *baby* is seen as
feeling more pain).

**Position and power** (Giessner & Schubert 2007, Study 1a, N=64). A manager's
org chart shows a short (2cm) or long (7cm) line to their team. `Score`, 1–7,
composite of 5 items ("dominant", "strong leader personality",
"self-confident", "a lot of control", "very high status").

| Condition | Human mean (1–7) | SD |
|---|---|---|
| Long line | 5.01 | 0.60 |
| Short line | 4.62 | 0.81 |

**Choosing vs. rejecting** (Shafir 1993, Study 1, N=170). A custody case:
Parent A has uniformly average features, Parent B has a mix of strongly
positive and strongly negative features. `Choice`, binary, asked as two
separate probes ("award custody" / "deny custody") exactly as ML2 framed them.

| Framing | Chose the extreme parent (B) |
|---|---|
| "Award custody to which parent?" | 0.64 |
| "Deny custody to which parent?" | 0.55 |

(The sum exceeds 1.0 by design — that is the finding: B is both chosen and
rejected more than A.)

**Categorization** (Norenzayan, Smith, Kim & Nisbett 2002, Study 2, "belongs
to" condition, pooled across cultures — the condition and pooling ML2
replicated). Target object with 4 binary features; Group 1 shares one
feature with all exemplars (rule-based), Group 2 looks more similar overall
but has no single defining rule. `Choice`, binary.

| Question | Rule-based choice |
|---|---|
| "Which group does the target object belong to?" | 0.67 |

**Incidental anchors** (Critcher & Gilovich 2008, Study 2, N=207). A
smartphone is called the "P97" or the "P17"; participants estimate its US
market share. `Choice` over percentage bands, matching the existing anchoring
item's format exactly.

| Condition | Human mean estimate | SD |
|---|---|---|
| "P97" | 58.1% | 19.6% |
| "P17" | 51.9% | 21.7% |

This is the decisive item for H-currency: the *original* gap is 6.2 points
(d=0.30); the *ML2-replicated* gap is d=0.04, essentially nothing. Simulating
"a typical participant" should track one number or the other, not both.

## 5. Hypotheses

| # | Hypothesis | Direction |
|---|---|---|
| **H1** | Simulated-human error correlates with fame index, controlling for response format. | positive correlation |
| **H2** | Simulated-human error does *not* correlate with fame once ML2-replicated effect size is held constant (via the matched pairs). | near-zero partial correlation |
| **H3 (currency)** | On the anchoring item, simulated and estimated answers track the *original* 6.2-point gap rather than the near-zero ML2 gap. | simulated/estimated gap > 3 points |
| **H4** | The *estimate* elicitation ("what % of participants...") is more accurate than the *simulate* elicitation, because it does not require role-play. | lower mean absolute error for estimate |
| **H5** | Where H1–H4 disagree with the pattern found in the first project (allocation games near-exact, illusions overshot), that pattern was partly an artefact of unmatched effect sizes rather than a real fame effect. | — (exploratory, stated as a falsification condition, not a predicted direction) |

H2 and H5 are the ones most likely to overturn the first project's framing,
and are stated that way deliberately.

## 6. What would falsify the interesting claim

If simulated-human error is fully explained by ML2-replicated effect size and
fame index adds nothing once magnitude is controlled, "the model overshoots
famous effects" is wrong — it merely overshoots *large* effects, and fame was
a confound in the first project, not a finding.

## 7. Cost and effort remaining

- Item construction: 5 new probes, following the existing pattern in
  `src/jevbench/instruments/`. Estimated half a day including tests.
- Fame index: citation counts and book-index lookups for ~16 items, plus one
  model-rated item per effect. An hour.
- Run: ~16 items × 3 elicitations × 10 replicates ≈ 480 Jev calls, about
  $0.01. A comparison arm adds roughly $1–2, with the token cap and reply
  parser built generous from the first call rather than discovered the hard
  way a third time.

Total new spend: **under $2**. Nothing has been run. This document is the
complete plan; the next action, if approved, is building the five items and
the fame-index script, not collecting data.
