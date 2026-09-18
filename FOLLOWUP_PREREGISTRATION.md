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

**Three elicitations per item.** *Superseded by Amendment 1 below — the table
here was under-specified for `Score`-format items and is kept only so the diff
shows what was wrong.*

| Elicitation | Framing | Primitive |
|---|---|---|
| Own answer | neutral | `Choice` / `Score` |
| Simulate | "answer as a typical participant would" | same |
| Estimate | "what proportion of participants gave answer X?" | `Noul` or `Score` band |

**Fame index.** *Superseded by Amendment 1 — leg (b) below cannot be computed
with the tools available and is kept only so the diff shows what was wrong.*
computed before any model call and independent of anything the model outputs:
(a) citation count of the canonical paper on Google Scholar, (b) a binary
presence/absence flag in each of three named books — *Thinking, Fast and
Slow*, *Predictably Irrational*, *Nudge* — via index lookup, (c) one separate
model-rated familiarity item per effect ("how well-known is this finding to a
general audience", `Score` 1–5), averaged over 5 replicates. Items where the
three disagree by more than one tier are dropped rather than argued over.

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

---

## 8. Amendment 1 — 2026-09-19

Made **before any of the five new items exist and before anything has run**;
the working tree still contains no probes and no data at the time of this
commit. Two parts of Section 3 turned out to be under-specified rather than
merely estimated wrong, and both are fixed here rather than silently edited.

### 8.1 What was wrong with "estimate"

The elicitation table treated "estimate" as a drop-in third condition
alongside "own" and "simulate", the way `typical_human` is a drop-in persona
alongside `neutral`. It isn't. "Own" and "simulate" are the *same question*
with different instructions prepended — that's exactly what `apply_persona`
already does. "Estimate" is a different question: it asks about the
population, not the respondent. For the two `Score`-format items (moral
typecasting, position and power) I had not decided whether the model would be
predicting a mean rating, a proportion above the midpoint, or something else
— three choices with three different comparison statistics, none of them
written down.

**Fixed specification, split by response format:**

- **`Choice`-format items** (Trolley, Knobe, Shafir, Norenzayan, incidental
  anchors, and the six reused items) — "estimate" is a **`Noul`** question
  asking for the proportion who gave one specific, named option. The target
  option is whichever key the existing analysis already extracts for that
  item (`correct`, `lure`, `fallacy_option`, `cooperative_option`,
  `certain_option`, and so on for the reused items; the extreme-parent option
  for Shafir; the rule-based option for Norenzayan). This adds no new
  bookkeeping — those keys already exist in every probe's `meta`. The
  returned probability compares directly to the published proportion.

  Worked example (Shafir, award-custody framing):

  > *Own / simulate instructions:* "To which parent would you award sole
  > custody of the child?" — `Choice` between Parent A and Parent B.
  >
  > *Estimate instructions:* "In a real study, participants read about these
  > two parents and were asked to award sole custody to one of them. [Parent
  > A and Parent B descriptions, unchanged.] What proportion of participants
  > awarded custody to Parent B?" — `Noul`, compared to the published 0.64.

- **`Score`-format items** (moral typecasting, position and power) —
  "estimate" keeps the **same `Score` primitive and the same criteria** as
  "own" and "simulate"; only the instructions change, from a first-person
  rating to a prediction of the average rating participants gave. This keeps
  all three elicitations on the same 1–7 scale, directly comparable to each
  other and to the published mean, rather than introducing a second statistic
  that would need its own conversion.

  Worked example (moral typecasting, man-commits-the-act condition):

  > *Own / simulate instructions:* "How responsible is the man for his
  > behaviour?" — `Score`, 7 levels, "Not at all responsible" to "Fully
  > responsible".
  >
  > *Estimate instructions:* "In a real study, participants read this
  > scenario and rated how responsible the man was for his behaviour, from 1
  > (not at all responsible) to 7 (fully responsible). What do you estimate
  > the average rating participants gave?" — same `Score` primitive and
  > criteria, compared to the published mean of 5.29.

### 8.2 What was wrong with the fame index

Leg (b), checking whether an effect appears in the index of three named
books, cannot be executed with the tools available. A book's index is
essentially never online as searchable text, and no amount of web search
substitutes for actually reading it. Proposing it as a one-hour task assumed
a capability that doesn't exist, which is a design error, not an estimation
error.

**Fixed fame index — three legs, two of them fully external and objective:**

1. **Citation count** of the canonical paper (Semantic Scholar or Google
   Scholar's citedBy count), recorded with the date it was checked, since the
   number moves.
2. **Wikipedia depth**: does the effect have its own dedicated article (not
   merely a mention on its author's biography page)? If yes, that article's
   word count; if no, zero. Checkable directly, unlike a book index — most of
   the reused famous items already have one (the Trolley problem's article
   alone runs to several thousand words, and the mammogram problem this
   project already uses is the standard textbook example of base-rate
   neglect), and I'd expect most of the five new obscure items not to —
   unverified until the check is actually run.
3. **Model-rated familiarity**, kept from the original design but now
   explicitly sourced from **the comparison arm's model, not Jev** — asking
   Jev to rate how famous an effect is and then using that rating to predict
   Jev's own behaviour on the same effect would be circular. Using a
   different model doesn't eliminate the concern (both are still trained on
   overlapping text), but it removes the direct circularity, and that
   limitation is stated here rather than discovered later.

Items where legs (1) and (2) disagree by more than one tier are dropped,
exactly as before; leg (3) is corroborating rather than decisive, given the
residual circularity concern.

### 8.3 What did not change

The item pool in Section 4, the pairing rule, the hypotheses, and the
falsification condition in Section 6 are unaffected — the flaws were in how
"estimate" and "fame" are *operationalised*, not in what the study is asking.

---

## 9. Amendment 2 — 2026-09-19

Caught while actually building the five items, before any probe was run —
Amendment 1's own fix had a gap.

Section 8.1 sorted "estimate" by **primitive** (`Choice` items get a `Noul`;
`Score` items keep their primitive and reword the instructions). That's the
wrong axis. The real distinction is what kind of statistic the human data
*is*: a **proportion** choosing between options (Shafir, Norenzayan, Knobe,
Trolley — where "what fraction chose X" is exactly what was published), or a
**mean** (Gray & Wegner's and Giessner & Schubert's rating scales — but also
incidental anchors, which is a `Choice`-over-percentage-bands item whose
published statistic is a *mean estimate with an SD*, not a proportion in any
one band). Section 8.1 filed incidental anchors under the `Noul` bucket by
primitive type and got it wrong: there is no single "correct band" to target
a proportion at, because the human number is a mean.

**Corrected rule**: keep the same primitive and criteria for every item, and
only reword the instructions from a first-person answer to a population
prediction — for both `Score` items and mean-type `Choice` items alike. The
`Noul`-targeting-a-named-option construction is used only for genuine
proportion items. Incidental anchors' "estimate" is therefore a `Choice`
over the same percentage bands as "own" and "simulate", asking what the
model predicts the *average* participant estimate was — read off with the
same `expected_numeric` band-midpoint calculation the repository's existing
anchoring item already uses, not a new comparison method.
