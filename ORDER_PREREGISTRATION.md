# Preregistration — Addendum: option order, and Jev 1.14

*Committed before any run described below. The git history is the evidence.
The [first preregistration](PREREGISTRATION.md) explains what this does and
doesn't establish.*

Date: 2026-10-14
Models under test: Jev 1.13 (`jev-1.13.0`) and Jev 1.14 (`jev-1.14.0`), both
called directly on TypeSafe's endpoint (`https://api.typesafe.ai/v1/systemone`).
On this date TypeSafe's models page lists 1.14 as the `jev-preview` alias and
1.13 as `jev-latest`, so 1.14 is reported as a **preview release**.

## 1. Why this addendum, and what has already been seen

The README's results are pinned to Jev 1.13, run through OpenRouter on 12–13
October 2026, and they stay that way. This addendum is reported separately.

The first preregistration's H6 asked how much shuffling a multiple-choice
item's options moves Jev's answer distribution. On the committed 1.13 run, the
core battery's 415 shuffled cells (83 items × 5 personas) have a mean total
variation (TV) distance of 0.063 between repeats. A quarter of the cells are
above 0.10. That figure has two weaknesses, and both were found by looking at
the data, so they are stated here before any new data exist:

1. **The noise floor is borrowed.** The 0.027 that the 0.063 is compared with
   comes from items that are never shuffled: rating scales and yes/no items. No
   multiple-choice item has ever been repeated with its options in a fixed
   order, so how much of the 0.063 is order, and how much is ordinary
   repeat-to-repeat variation, is unknown.
2. **A possible pull toward later options.** Probability mass by slot, pooled
   over items, is 0.459 / 0.541 for two-option items and leans to later slots
   for six-option items (0.138 to 0.202 against 0.167 uniform). This was
   noticed after the fact, on one set of permutations, so it is a hypothesis
   here, not a finding. It is also the **opposite** of what TypeSafe reports:
   its [Jev 1.13 jaggedness page](https://docs.typesafe.ai/model-jaggedness/jev-1.13)
   (last reviewed 2026-10-02) lists option order as a known failure mode, with
   1.13 leaning "toward the option that comes first", and says many listed
   failure modes "will be fixed in later versions". On this date there is no
   1.14 jaggedness page and no 1.14 release notes.

Also seen before this was written: one test call per version on a two-option
item that is not in the battery, to check the key and the model IDs. Both
versions answered with the versioned ID requested.

## 2. Runs

All runs use the direct TypeSafe backend, 10 repeats per item × persona, the
five personas of the first project, and the repository's current battery. Each
is made for **both** versions, so every comparison is like for like. The one
addition is a copy of R1 for 1.13 through OpenRouter, for the route check
(section 5).

| Run | Items | Option order | Purpose |
|---|---|---|---|
| R1 | full battery | shuffled, seed 20260918 (the committed runs' seed) | 1.14's numbers next to 1.13's; route check (1.13 also through OpenRouter) |
| R2 | core battery | shuffled, **new seed 20261014** | order effect, slot position |
| R3 | core battery | **fixed** (as written, never shuffled) | the true noise floor |

The core battery is every module except `followup`, as in H6. Because the
permutation is seeded by item, persona and repeat, not by model, both versions
see identical permutations within a run. That makes the version comparison
paired.

**R2 and R3, for both versions, run at the same time.** The four runs are
launched together, with the same number of workers each, so their requests
are interleaved over one time window. Run one after another, a change in how
TypeSafe serves Jev between runs would be indistinguishable from an effect of
shuffling or of version. The runner works through its jobs in a fixed order
(item, then persona, then repeat), the same in all four runs, so a cell's
repeats run close together and each cell is reached at about the same time
in every run. Every comparison in section 4 is made within a cell, so it is
matched in time. The runner's existing timestamp is taken when a call is
first sent, before any retries, so it is extended to also record when the
answer that was kept arrived. As a check that the matching held, each cell's
median arrival time is taken in each of the four runs, and the largest gap
between them is reported (median and maximum over cells), next to the length
of the runs.

R2 uses a new seed because the slot hypothesis (1b) was suggested by the
seed-20260918 permutations. Testing it on the same permutations would not be a
test.

Raw files go in `data/raw/order_study/`, outside the `run_live_*.jsonl` set the
README's analyses read. Seed and fixed-order switches are added to `jevbench
run` for this; the battery and the scoring are not changed.

## 3. Measures

- **Cell spread.** For an item × persona cell, the mean TV distance over all
  pairs of its 10 answer distributions, as in H6 (`order_effects`).
  Distributions are keyed by option label, not slot, so shuffling doesn't
  change what is compared.
- **Item spread.** The mean of the cell spread over the item's persona cells
  (all five, unless section 6 drops some; within a comparison, the same cells
  on every side).
- **Instrument spread.** The mean of the item spread over an instrument's
  items. Instruments, not items or cells, are the unit of every test below.
  An item's five persona cells are not independent, and neither are many
  items: Holt–Laury's 10 items are rows of one lottery menu, discounting's 12
  are rows of one grid, and the ultimatum responder's 11 are thresholds in one
  game. The 83 core multiple-choice items come from **21 instruments**. Treated
  as independent units, those three instruments alone would supply 33 of the
  83 observations.
- **Order excess.** An item's spread in R2 minus its spread in R3, averaged
  the same way up to the instrument.
- **Slot slope.** Within an R2 cell, each option's probability on each repeat,
  minus that option's mean over the 10 repeats, is regressed on its slot
  position, rescaled to 0 (first) … 1 (last) and centred the same way. The
  slope is the change in probability from first slot to last, with each
  option's own pull removed. An item's slope is the mean over its personas,
  and an instrument's the mean over its items.

## 4. Hypotheses and tests

All tests are Wilcoxon signed-rank over the 21 instruments that contain the
core multiple-choice items, and every bootstrap interval resamples
instruments. The five tests are one family, Holm-corrected at α = 0.05. The
same tests over the 83 items are reported beside them as a sensitivity
check, labelled as such.

- **O1 (two tests, one per version). Shuffling moves Jev's answers more than
  repeating does.** Instrument spread in R2 > instrument spread in R3.
  One-sided.
- **O2. 1.14's order sensitivity differs from 1.13's.** Paired over instruments:
  1.14's order excess vs 1.13's. Two-sided: TypeSafe expects to fix listed
  failure modes in later versions but has said nothing about option order in
  1.14. Reported with the median difference and a bootstrap 95% interval.
- **O3 (two tests, one per version). Jev has a slot-position lean.**
  Instrument slot slope ≠ 0. Two-sided, because our exploratory data (later options) and
  TypeSafe's documentation (first option) point in opposite directions. A
  positive slope means later options gain; a negative one means the first
  gains. Reported with the median slope and a bootstrap 95% interval.

If R3 spread is exactly zero (Jev deterministic at fixed input), O1 reduces to
whether R2 spread is above zero. That is reported as such, not as a strong
result.

## 5. Descriptive only (no hypotheses)

- **Jev 1.14 against 1.13** on R1: the README's headline statistics, side by
  side. We make no prediction about whether 1.14 is more or less human-like.
- **Route check:** 1.13 on R1 run directly against 1.13 on R1 run through
  OpenRouter (`typesafe/jev-1.13`, same seed), the two launched together like
  R2 and R3, so a difference is not also a difference of date. With the same
  seed, repeat *r* sends the identical request on both routes, so the check is
  per repeat: the TV distance between the two routes' answers to the same
  request, averaged over a cell's repeats. The reference is R3's cell spread,
  which is likewise a distance between single answers to identical requests
  (not between averages). If the route matters, that is said wherever 1.13
  and 1.14 numbers sit side by side. If OpenRouter no longer serves 1.13, the
  committed 12–13 October run is used instead, and the check is reported as
  one of route and date together, not of route alone.
- The probability-mass-by-slot profile from section 1, on R2, for each
  version.
- The per-persona order effect (on 1.13, antisocial 0.042 against 0.066–0.070
  for the other four), on R2 and R3.

## 6. Exclusions and data quality

- A record counts only if the response reports the versioned model ID
  requested and its distribution passes the existing usability check
  (`distribution_problem`).
- Calls that fail outright (no reply) are rerun with `--resume`. Replies that
  arrive but fail the usability check are **not** retried: they are Jev's
  answer, `--resume` keeps them, and retrying until a usable one came back
  would select the answers. They are counted and reported per version, and
  they count against the threshold below.
- A cell needs at least 8 usable repeats. Every paired comparison (R2 against
  R3 in O1; 1.14 against 1.13 in O2) uses, for each item, only the persona
  cells that qualify on **every** side of that comparison, and the item
  enters only if at least 3 such cells remain. O3 uses the cells that qualify
  in that version's R2, with the same minimum of 3. Dropped items are listed.
- **Matched repeats across versions.** Permutation is the treatment, so
  wherever R2 is compared across versions (O2), a cell's spread on both
  versions is computed from the same repeat IDs: those usable on both. The
  cell qualifies only if at least 8 such repeats remain. The route check
  likewise uses only repeats usable on both routes.
- **Cells with no order variation.** The seeded shuffle does not guarantee
  that every cell's 10 repeats see more than one order. With seed 20261014,
  two cells get the same order on all 10 repeats (`ultimatum_respond_0` and
  `holt_laury_04`, both with `typical_human_plain`; checked from the seed
  alone, before any run). Their slot slope is undefined, so a cell enters O3
  only if, over its usable repeats, at least one option's slot varies.
  Such cells stay in O1 and O2, where they contribute an R2 spread that holds
  order fixed, which works against O1.
- Each run is completed in one go where possible. If any record reports a
  model other than the versioned ID requested (for instance, TypeSafe changes
  what `jev-1.14.0` serves partway through), that run is redone in full as a
  new file, not resumed, and the discarded file is kept and named in the
  report.

## 7. Reporting

A separately labelled section after the README's main results, with its own
chart, built from `data/raw/order_study/`. 1.14 is called a preview release.
The README's headline results stay on 1.13. All five tests are reported
whatever their outcome. Anything not listed here is labelled exploratory.
Deviations are recorded in this file as amendments, as in the earlier
preregistrations.
