# Does a "System One" model behave like human System 1?

A behavioural-economics and psychometric battery run against TypeSafe's Jev,
with an ordinary chat model and published human values as comparison points.

> [!IMPORTANT]
> **This is a personal project, done out of curiosity and to learn how to build
> an evaluation.** It is not research, not a product review, and not the work of
> anyone with professional standing in psychometrics, experimental economics or
> model evaluation. **No claims are made** about any model, company or product.
> What follows is a set of numbers recorded from a public API on 12–13 October
> 2026, and a description of how they were produced. Everything
> is recomputable from `data/raw/`. It is not peer reviewed, it uses instruments
> well outside the contexts they were validated in, and it is probably wrong
> somewhere. Full caveats in [PREREGISTRATION.md](PREREGISTRATION.md#what-this-is-and-what-it-is-not).
> Not affiliated with or endorsed by anyone. Corrections welcome.

---

## The question

TypeSafe describes Jev as a **System One model**: it returns a typed,
probabilistic decision in a single pass rather than generating text token by
token.

That name comes from dual-process theory. In Kahneman's framing, System 1 is
fast, automatic and associative; System 2 is slow and deliberate. Most classic
results in behavioural economics are demonstrations that human System 1 produces
confident, systematic, *predictably wrong* answers where deliberation would
produce right ones.

So there is a question that is at least fun to ask: **does a model that is
architecturally System 1 — one forward pass, no chain of thought — reproduce the
behavioural signature of human System 1?** And if you simply *ask* it to answer
like a person, what happens?

## Why this model is an unusually convenient subject

Work of this kind normally has to estimate how a model would answer by
resampling the same prompt many times at temperature and counting outcomes. That
estimate mixes the model's response tendency with the sampler's noise, and costs
N calls per item.

Jev returns a **probability distribution over the answer set in one call**. So
every number here is computed from the returned distribution, never from the top
answer — discarding the distribution would throw away the only reason this was
worth doing.

The contrast showed up in the run itself, at **$0.14 against $8.84** for the
identical grid.

![How one item becomes a number](results/figures/how-it-works.png)

The comparison arm returns near-identical answers on most items: in 83% of its
cells all ten samples agreed. That is genuine low-entropy behaviour rather than
a defect — temperature is demonstrably active, and genuinely ambiguous items do
come back mixed. Two caveats follow that the cost comparison alone obscures.
Ten samples cannot resolve a probability finer than 0.1, and ten agreeing
samples license "at least 0.78" at 95% (a Jeffreys interval), not 1.00. And the arms do not measure
the same quantity: Jev reports a credence, whereas resampling recovers a
sampling frequency, and a model can be internally uncertain while emitting the
same token every time. The cost asymmetry is real; the graded-versus-saturated
contrast is partly an artifact of comparing two different things.

## What I observed

14,800 observations at $8.99, recorded on 12–13 October 2026: 147 probes × 5
prompt conditions × 10 replicates through Jev, plus the same grid through
`claude-sonnet-5.5`, resampled ten times per cell, and 100 more calls on 13
October for the population questions added to the follow-up study (see
below). No transport errors; 3 of
6,800 scorable comparison-arm replies (0.04%) could not be resolved to an
option, and every cell kept at least 8 of its 10 samples. Full tables in
[docs/RESULTS.md](docs/RESULTS.md).

Where a human value is quoted it is a published reference point, listed with
its source in [docs/BENCHMARKS.md](docs/BENCHMARKS.md). Two are looser matches
than the rest: the base-rate figure counts Bayesian answers rather than answers
in a band, and the anchoring study asked a different question, so only its
20-point gap between anchors is compared.

The charts below put Jev next to three other System One models from the
[model comparison](docs/MODELS.md) — GPT-6 Luna Decisions, Cloudflare's Clef
and Liquid AI's d1 — so its results can be read against its peers'. The text is
about Jev; each chart is followed by the same chart for Jev alone, and all
twelve models are in docs/MODELS.md.

### With no instruction, it does not look like human System 1

![Four System One models against people on seven decision-making tests, with and without the typical-person instruction](results/figures/models-decisions.png)

![Jev alone on the seven decision-making tests, with and without the typical-person instruction](results/figures/jev-decisions.png)

On most classic biases it sits closer to the normative answer than the published
human value. On Frederick's three Cognitive Reflection Test items it put
**0.99** probability mass on the correct answers (human reference ≈ 0.41), and
across all six CRT items **0.01** on the intuitive lures the items are built to
attract. It continued the sunk-cost project with probability **0.04** (human ≈
0.85), put **0.61** on the base-rate item's correct band (about 0.15 of people
give a Bayesian answer), and moved **1.6 percentage points** between anchoring
conditions where humans move about 20.

It shows **no framing effect at all**: it picks the sure programme in the
disease problem at 0.85 when it is worded as lives saved and 0.84 when worded
as lives lost, where people go from 0.72 to 0.22. No System One model shows
people's 50-point reversal without being asked, and only Solar Decide comes
near it when asked:

![The framing reversal by model](results/figures/framing-contrast.png)

![Four System One models against people in the economic games](results/figures/models-games.png)

![Jev alone in the economic games, with no instruction](results/figures/jev-games-neutral.png)

The social preferences are a partial exception: it gave **0.15** of the pie as
dictator (human ≈ 0.28), offered **0.41** in the ultimatum game (human ≈ 0.40)
and rejected a $1 offer at **0.49** (human ≈ 0.50). Positive giving is not
equilibrium play, so on these items it lands nearer people than game theory.
Not everywhere: it cooperated in a one-shot prisoner's dilemma at **0.03**,
against people's 0.37.

### Asked to answer like a person, it moves on some effects and not others

The `typical_human` condition puts this in front of every item, verbatim:

> Answer the way a typical human participant in a psychology or economics experiment would actually answer — not the textbook-correct answer, and not an idealised one. Give the response the average person would give.

Some effects appear on request. The conjunction fallacy went from **0.10 to
0.93** against people's 0.85, CRT accuracy fell from **0.99 to 0.32** (people
0.41) with lure mass up from **0.01 to 0.41**, and the games moved almost onto
the human values: dictator **0.27** (0.28), trust **0.48** (0.50), public goods
**0.51** (0.50).

Others do not. The framing effect stays absent (**0.89** and **0.84** sure
choices, a 4-point swing against people's 50), and the sunk-cost item, in Arkes
and Blumer's original wording, gets **0.17** continuation against people's
0.85. Rejection of a $1 offer overshoots, at **0.92** against 0.50.

Across the 14 probability-scale measures, the typical-person instruction cuts
Jev's mean distance from the human values from **0.31 to 0.18**, and its
correlation with them goes from **−0.21 to +0.39**: closer, and partly in the
right order, but only partly. Every model's distance, with and without the
instruction:

![Every model's distance from the published human results, with and without the typical-person instruction](results/figures/models-scatter.png)

### How much of that is the instruction's steer

"Not the textbook-correct answer" does more than ask for a typical person: on
any item with a right answer, it says which way to move. So the battery also
asks the same thing without that clause:

![Jev under the typical-person instruction with and without its steer](results/figures/jev-steer.png)

Without the steer, CRT accuracy is **0.53** instead of 0.32 and lure mass
**0.27** instead of 0.41, and the base-rate item's correct band gets **0.42**
instead of 0.23. The conjunction fallacy barely moves (**0.87**), nor do the
games. So the CRT and base-rate errors are partly the instruction telling the
model to be wrong. The conjunction fallacy and the generous, fair-minded game
play look more like the model's own picture of people.

### The other prompts

Asked to answer as a rational agent, it put **all** its mass on giving nothing
in the dictator game and **all** of it on the Nash equilibrium of 0 in the
p-beauty contest. Asked to adopt an antisocial persona, Dark Triad self-report
rose from **5.0 to 8.6** on a 9-point scale (the manipulation check), and giving
collapsed across every game — dictator 0.15 → 0.00, trust sent 0.38 → 0.07,
public goods 0.38 → 0.01.

![The antisocial persona in the economic games, four models](results/figures/models-antisocial.png)

![Jev alone: the antisocial persona in the economic games](results/figures/persona-antisocial.png)

That the persona reaches consequential allocations and not just self-description
is the part I found most interesting, and it is measurable here only because the
output is a number.

### Where I was wrong

[PREREGISTRATION.md](PREREGISTRATION.md) records eleven hypotheses, ten with a
predicted direction, written down before any data was collected. Six held
(H1, H2, H3, H4, H9, H10). Three failed, which I am reporting because the point
of writing them down first was to be held to them:

| Expected | Observed |
|---|---|
| H5: independently elicited probabilities obey P(A∧B) ≤ P(A) | **Violated**, margin **−0.09** with no instruction and **−0.38** when asked to answer like a person |
| H8: accuracy falls as reasoning depth grows (> 15 points) | **9 points** from 1-step to 3+-step items with no instruction |
| H6: option order barely matters (mean TV < 0.05) | **0.063** mean, median 0.041, on the core battery's multiple-choice items, whose options were shuffled. Answers move 0.027 between replicates with nothing reordered, a rough noise floor, so a large part of that may be noise. The [addendum](#addendum-14-october-2026-option-order-and-the-jev-114-preview) measured it properly: about a third is. The follow-up items, which H6 was not written for, move less (0.025) |

H4 predicted a framing reversal much weaker than people's (under 25 points); it
is 1 point. H7 (Jev's distribution is more stable across replicates than the
resampled chat model's) was never tested: the analysis to compare the two
spreads was not built. H11 was exploratory, with no direction, and is not
reported.

### The follow-up study: estimating people beats imitating them, a little

A second preregistration,
[FOLLOWUP_PREREGISTRATION.md](FOLLOWUP_PREREGISTRATION.md), added 30 items for
eight effects, five of them from the Many Labs 2 replication project's protocol
and three (Knobe, trolley, false consensus) from the original papers. Each
effect was measured two ways: as the item itself under the typical-person
prompt ("simulate"), and as a population question with no persona asking for
the population's answer itself: the share who chose an option, or the average
rating, percentage or prediction ("estimate"). Its central fame hypotheses
(H1, H2) could not be run, because the matched pairs they needed do not exist
in the item pool. Two others could:

- **H4: estimate is more accurate than simulate.** It holds for Jev, but
  only modestly. The test covers 23 statistics, each compared with the original
  study's published value (Many Labs 2 reports only effect sizes, not the
  per-condition values this needs):
  15 from the new items and 8 from the six items reused from the first project
  (CRT, framing, Linda, sunk cost, Allais, base rate). The reused items'
  population questions were built and asked on 13 October, after the main run.
  Estimate is closer on **14 of 23**. The preregistered one-sided Wilcoxon test
  on the absolute errors gives **p = 0.015**. Those errors are in each item's
  own units, so the two percentage items and the 1–7 ratings outweigh the
  proportions. Scaled to each item's range instead, a check I chose after
  seeing the data, Jev's mean error is **0.17** when estimating against
  **0.23** when simulating, and p = 0.043. Across the ten System One models,
  estimating has the lower mean scaled error for **seven**. Three pass the
  preregistered test (GPT-6 Luna Decisions, Jev and Mercury Decide), and only
  Jev passes the scaled one.
  The main run also asked the new items' population questions under every
  prompt; inside the steer-free typical-person prompt, Jev's estimates beat
  its simulated answers on 12 of 15 (p = 0.003; 0.01 scaled). That is not the
  preregistered comparison, and the battery now asks population questions with
  no persona.
- **H3: the model reproduces the original anchoring effect, not the replication.**
  It does not. The original incidental-anchoring study found a 6.2-point gap;
  Many Labs 2 found almost none. No System One model reaches 3 points in the
  original's direction, simulated or estimated; the largest is 2.6 (Jev: 0.3
  and −0.3).

![Jev's error on each of the 23 statistics, simulated and estimated](results/figures/followup-h4.png)

The full table is in [docs/RESULTS.md](docs/RESULTS.md#follow-up-h4-simulate-or-estimate).

The conjunction result looked like the most interesting thing here until I read
the documentation properly. Asked side by side, the model picked the single
statement over the conjunction (fallacy mass 0.10). Asked as two independent
probability questions, it assigned the conjunction *higher* probability than its
own component. That is the shape of the original human finding — but it is also
already documented behaviour, not a discovery. See the next section.

### Addendum, 14 October 2026: option order, and the Jev 1.14 preview

Everything above is Jev 1.13 through OpenRouter, and stays that way. This
addendum was preregistered separately, in
[ORDER_PREREGISTRATION.md](ORDER_PREREGISTRATION.md), before any of its data
existed. It asks whether H6's order effect is real or just repeat noise, and
whether Jev 1.14 behaves differently. On that date TypeSafe lists 1.14 as its
`jev-preview` model; `jev-latest` still points at 1.13. All runs called
TypeSafe's API directly: 10 repeats of each item under each of the five
prompts, plus one copy through OpenRouter to check the route. The exception is
the follow-up study's 25 population questions, which are in the full-battery
runs only and, as the battery asks them, under the neutral prompt alone. That
came to 43,950 calls and cost $0.83. OpenRouter records its $0.13 per call.
TypeSafe's direct API reports tokens but not cost, so the direct runs' $0.70 is
their 16.7 million input tokens at the listed $42 per billion (output is
free); [summary.json](results/order_study/summary.json) has both, run by run.

- **Shuffling the options moves Jev's answers beyond repeat noise, in both
  versions (O1).** With the options in a fixed order, answers move 0.023 (1.13)
  and 0.025 (1.14) between repeats. With the options shuffled, they move 0.067
  and 0.060. Shuffling moves the answers more on 20 of the 21 instruments in
  1.13 (conjunction, barely, is the exception) and on all 21 in 1.14
  (Holm-adjusted p < 0.0001 for both). For 1.13, then, about two thirds of
  H6's 0.063 is option order and one third is repeat noise. The noise floor
  H6 borrowed from rating scales (0.027) turns out to have been close.
- **No difference in order sensitivity between 1.14 and 1.13 was detected
  (O2).** The median difference is −0.001 (95% interval −0.010 to 0.001,
  p = 0.32). The interval still allows 1.14 to be slightly less sensitive, so
  this does not show the two are the same.
- **There is a small lean toward the later options, the opposite of what
  TypeSafe documents (O3).** TypeSafe's
  [Jev 1.13 notes](https://docs.typesafe.ai/model-jaggedness/jev-1.13) say it
  leans toward the option that comes first. Here, an option gains a median
  0.8 percentage points (1.13) and 0.7 (1.14) from first place to last
  (Holm-adjusted p = 0.03 and 0.04). The lean is uneven. In 1.13 the
  discounting items carry most of it, at 30 points. In 1.14 the Holt–Laury
  lottery items lean the other way, at 18 points toward the first option. On
  two-option items the split is 45/55 in 1.13 and exactly 50/50 in 1.14.
  Counted by item rather than by instrument, a check fixed in advance, the lean
  holds for 1.13 (p = 0.0006) but not for 1.14 (p = 0.14).
- **The route makes no visible difference.** Sending the same request through
  OpenRouter instead of directly moves the answer 0.028. Repeating it on the
  same route moves it 0.024. Under half of the item-and-prompt pairs (48%)
  differ between routes by more than their own repeat noise.

The tests compare instruments, not items, because rows of one menu (Holt–Laury,
discounting, the ultimatum thresholds) are not independent. The shuffled and
fixed-order runs ran at the same time: across all four runs, each
item-and-prompt pair was answered within 8 seconds (median 3) of runs that
took about 80 seconds. 1.14's statistics for the whole battery are in
[version_statistics.csv](results/order_study/version_statistics.csv), next to
1.13's, as a description only. The full tables are in
[results/order_study/](results/order_study/), and `jevbench order-study`
rebuilds them and the figure from the raw runs.

![How far option order moves Jev's answers, per instrument, 1.13 and 1.14](results/figures/order-study.png)

## Checked afterwards against the documented behaviour

After the run I read TypeSafe's `model-jaggedness/jev-1.13` page, which
documents known weaknesses of this version. Three of them bear directly on
results above, and reading it earlier would have changed how I designed the
battery.

**"Jev is not a calculator… does not count reliably."** A large part of this
battery is arithmetic: all six CRT items, the number-series and quantitative
reasoning items, the Holt–Laury lottery comparisons, the discounting items, the
base-rate problem and the p-beauty contest. Wherever the model did *badly* on
those, "documented numeric weakness" is at least as good an explanation as
anything about System 1, and probably better. **The Holt–Laury result — 2.1 safe
choices against a human reference of 5.2, which would read as strongly risk
seeking — should not be taken at face value**, because it depends on comparing
probabilities and payoffs numerically. The same caution applies to the
discounting items.

It cuts the other way too: the model answered the CRT's arithmetic word
problems at 0.99 despite arithmetic being a documented weak spot, which makes
the cognitive-reflection result more interesting rather than less.

**"There are many structural invariants one might imagine to hold that simply
aren't guaranteed."** This covers the conjunction-rule violation directly. I
predicted the axiom would hold; the documentation says in advance that such
invariants are not guaranteed. So the finding is consistent with documented
behaviour, and my expectation was simply naive. Presenting it as a surprise
would have been the genuinely embarrassing outcome.

**"Content written to adversarially steer the model… can move the answer."** The
persona-steerability result is likewise consistent with documented behaviour
rather than novel. What this repository adds is a measurement of *how far* it
moves on consequential allocations, not the observation that it moves.

**A guidance violation of my own.** The Score docs say to *"describe situations,
not degrees"*, and warn that each level is judged independently so comparative
language does not help. Every Likert scale here is degrees — "Very inaccurate"
through "Very accurate" — because that is what the instruments specify. The
instrument and the primitive's guidance genuinely conflict, and I followed the
instrument. Someone could reasonably argue I should have done the opposite.

**What did hold up.** The framing is not a misreading: the documentation states
that *"The System One name comes from the concept Daniel Kahneman popularized in
his book Thinking, Fast and Slow"*, and that these models do not "generate
explanations of their reasoning". The Score handling is also right — the score
is defined as each level multiplied by its probability and summed, which is what
`expected_level` computes (on a 1-based scale, so a 5-point item reads 1–5 as
the instrument prints it, where the API's own score is 0-based).

![What a single call returns, four models](results/figures/models-dictator.png)

![What a single call returns, Jev alone](results/figures/dictator-distribution.png)

![Option-order sensitivity, four models](results/figures/models-order-effects.png)

![Option-order sensitivity, Jev alone](results/figures/order-effects.png)


## Running it yourself

```bash
git clone https://github.com/tynamite/evaluation-behavioral-system-one.git
cd evaluation-behavioral-system-one
uv venv && uv pip install -e ".[dev]"

cp .env.example .env        # then add your OpenRouter key
jevbench doctor             # verify credentials and endpoint

jevbench probes             # list the battery, call nothing
jevbench run --replicates 10 --baseline-samples 10
```

That is the committed run's grid: 147 probes × 5 prompts × 10 replicates
through Jev, and the same through Claude Sonnet 5.5, resampled ten times. The
chat arm's reply cap defaults to 4,096 tokens (`JEVBENCH_BASELINE_MAX_TOKENS`),
because models that reason before answering spend it on reasoning first.

A new run is written to `data/raw/` and is not analysed into the committed
results unless you ask: pass it with `--run`, and give `--out` a directory of
your own so `results/` keeps the committed run's output.

```bash
jevbench analyse --run data/raw/run_live_<timestamp>.jsonl --out my-results/tables
jevbench figures --run data/raw/run_live_<timestamp>.jsonl --out my-results/figures
```

`jevbench figures` draws the analysis figures (matplotlib). The figures in this
README are a different set, drawn by `jevbench diagrams` in the house style of
[diagram-design](https://github.com/cathrynlavery/diagram-design): one HTML file
per figure in `docs/diagrams/`, rendered to PNG in `results/figures/`. PNG export
needs `uv pip install -e ".[diagrams]"` and a Chromium: either run
`playwright install chromium`, or point `JEVBENCH_CHROMIUM` at an existing one.
The single-model figures are drawn from the run itself (the newest run with Jev,
or the one `--run` names), analysed afresh, so they never show another run's
numbers; the multi-model figures come from `jevbench compare`'s output. Their
titles and source lines name the committed run (Jev 1.13, 10 repeats, 12–13 Oct
2026), so `diagrams` refuses a run that differs; `jevbench figures` draws any run.

### Adding more models

Results for nine more System One models and Claude Haiku 5.5 are in
[docs/MODELS.md](docs/MODELS.md).

Every System One model on OpenRouter's decisions route shares Jev's
`/v1/systemone` contract, so any of them can be run through the same battery,
one run file per model. Chat models go in the baseline arm, and
`--replicates 0` adds one without re-running a System One arm.

```bash
# check each model implements Choice, Score and Noul before paying for a run
jevbench doctor --model openai/gpt-6-luna-decisions liquid/d1 microsoft/microsoft-decision-1

jevbench run --model liquid/d1 --replicates 10
jevbench run --replicates 0 --baseline-model anthropic/claude-haiku-5.5 --baseline-samples 10

jevbench compare data/raw/run_live_*.jsonl       # -> results/comparison/
```

`compare` reduces each file with the single-run analysis unchanged, then joins
the results on the model that actually served each arm. It writes
`health.csv` (read it first: a model that rejects one primitive shows up there
as an error rate of 1.0 for that kind), `fidelity.csv`, `measures.csv`,
`statistics.csv` and `fig_models_vs_human.png`; the editorial figures come
from `jevbench diagrams`. To analyse one of the new runs on its own without
overwriting the committed results, give `analyse` and `figures` an `--out`
directory.

**No key? Everything still works.** The offline backend is deterministic and
exercises the entire pipeline:

```bash
jevbench run --backend simulator --replicates 2
jevbench analyse && jevbench figures      # -> results/simulated/
```

Simulated output is structurally valid nonsense, tagged `simulated` in the
filename. `load_records` refuses to pool it with live data, and its tables and
figures go to the gitignored `results/simulated/` so they never overwrite the
committed results.

Reproduce the committed analysis without spending anything — the raw records
are committed:

```bash
jevbench analyse                       # the newest run with Jev in data/raw/
jevbench compare data/raw/run_live_*.jsonl
python scripts/gen_results_doc.py
jevbench diagrams
```

The runs behind an earlier version of this write-up are kept in
[data/archive/](data/archive/README.md).

### What is published

Everything except your key. The item wording is in `src/jevbench/instruments/`,
and every raw response — the returned distributions, the chat model's reply
text, cost per call — is committed as JSON Lines in `data/raw/`
([field list](data/raw/README.md)). The files contain no credentials and no
personal data. The only secret is the OpenRouter key in your own `.env`, which
is gitignored, refused by a pre-commit hook and checked for in CI.

## Repository layout

```
src/jevbench/
  cli.py           the `jevbench` command
  config.py        environment, endpoints and output paths
  schema.py        Choice / Score / Noul primitives; normalises all three
                   into one distribution-carrying Answer
  client.py        OpenRouter decisions route + native TypeSafe endpoint,
                   bounded backoff, key redaction on every error path
  simulator.py     deterministic offline backend for CI
  runner.py        concurrent execution, one JSONL record per observation
  analysis.py      statistics; both arms reduced to comparable distributions
  plots.py         analysis figures (matplotlib)
  diagrams.py      the editorial figures in the README, diagram-design style
  compare.py       several models' runs side by side
  benchmarks.py    42 human reference values, each with source + reliability
  fame.py, pairing.py, ml2_effects.py
                   the follow-up study's fame index, pairing rule and
                   Many Labs 2 effect sizes
  instruments/     the battery
scripts/           doc generators (RESULTS.md, BENCHMARKS.md), the figure
                   layout checker, and the follow-up study's reports
tests/             146 tests, all runnable with no API key
data/raw/          committed raw records — every number is recomputable
data/archive/      the runs behind an earlier version of this write-up
results/           generated tables and figures
docs/              findings, results, benchmarks, the model comparison and
                   the figure sources
```

Also at the root: [PREREGISTRATION.md](PREREGISTRATION.md), the plan and
hypotheses for the first run, and
[FOLLOWUP_PREREGISTRATION.md](FOLLOWUP_PREREGISTRATION.md), a follow-up study
whose H3 and H4 are reported above; its fame hypotheses (H1, H2) could not be
run on this item pool. [ORDER_PREREGISTRATION.md](ORDER_PREREGISTRATION.md)
is the plan for the option-order addendum, run on Jev 1.13 and the 1.14
preview and reported above.

## How the instruments map onto three primitives

Jev answers only in `Choice`, `Score` and `Noul`. That turns out to cover
almost every standard response format in the literature:

| Response format | Primitive | Example |
|---|---|---|
| Forced choice | `Choice` | accept/reject, cooperate/defect, which programme |
| Allocation | `Choice` over integers | give $0…$10 — returns the whole histogram |
| Likert | `Score` with 5 or 9 levels | Mini-IPIP, Dirty Dozen |
| Probability judgement | `Noul` | "Linda is a bank teller" |

What it cannot do: free text, reasoning traces, open-ended responses. Items
requiring those are simply not in the battery rather than being approximated.

## Methodology notes

**Distributions, not argmax.** Every statistic is computed from the returned
probabilities. For `Score` items, the expected level is recomputed from the
returned index weights rather than read from the scalar `score` field, so all
instruments are treated identically.

**No answer-key leakage.** `Choice` option keys carry literal content
(`"$0.05"`, `"cooperate"`) and never evaluative labels. A test asserts this.

**Item isolation.** One probe per API call. Jev accepts many questions per
call, but batching would place items in a shared context; an administered
instrument requires them to be mutually blind.

**Order randomisation.** In the System One arm, the options of every `Choice`
item are independently permuted per replicate, which is what makes the
order-invariance claim testable rather than assumed. `Score` and yes/no items
have a fixed order. The chat arm gets the same permutation as the System One
arm on the same replicate.

**Reverse-keyed items.** Each Big Five factor carries both forward and
reverse-keyed items, so answering the surface wording rather than the content
is detectable.

**Reading chat replies.** A chat model answers in text, so its reply has to be
read for the option it names; unreadable replies are dropped and counted, never
guessed, and `summary.json` reports them with per-cell sample coverage.
[docs/MODELS.md](docs/MODELS.md#how-a-chat-models-reply-becomes-an-answer)
describes each step.

The typed arm has never returned an answer that could not be read, across
74,500 calls to ten System One models: a typed decision is a distribution,
so there is no text to misread. What did go wrong there was visible: 300
refusals from one model and 100 calls the route rejected (the p-beauty item,
for both Solar models), each recorded as such ([docs/MODELS.md](docs/MODELS.md#read-the-health-table-first)).

![What the health table caught](results/figures/health-checks.png)

**Learnings.** The bugs found and method fixes made along the way, and what
each one changed, are written up in [docs/LEARNINGS.md](docs/LEARNINGS.md).

## Limitations

The full version is in
[PREREGISTRATION.md](PREREGISTRATION.md#what-this-is-and-what-it-is-not). The
ones that bound the numbers most:

1. **Not expert work, and not peer reviewed.** A hobby project that tries to be
   careful. Instruments are used far outside their validated contexts by
   someone unqualified to validate them.
2. **The human values are not a control group.** They come from separate
   published samples with different populations, stakes, decades and protocols.
   Differences of a few points are not interpretable. Where the human result is
   a *contrast* (the framing reversal, the anchoring gap), the contrast is the
   robust quantity, not the level.
3. **A model is not a participant.** Self-report items were written for people
   with autobiographies. "Do you have frequent mood swings" is not the same
   question when asked of software, and the Dark Triad scale is a manipulation
   check, never a diagnostic claim.
4. **The reasoning set is not an IQ test.** No norms, no standardisation
   sample; it reports accuracy on a fixed list of questions.
5. **Each model run once, on one route.** Every model was run on 12–13
   October 2026, all through a
   third-party gateway via an alpha route that may move. `jevbench doctor` is
   there to say when it has.
6. **Persona conditions are prompt manipulations**, not traits. They show what
   the model can be induced to output, and nothing about what it "is".
7. **The reasoning items were written for this project** and have no
   psychometric validation. Published instruments are used where a free one
   exists, and cited.
8. **Results move a lot with wording.** Several headline numbers shift
   substantially across the five prompts, and an earlier version of the
   battery showed a large framing effect that disappeared once a label naming
   the condition was removed from the input. That is itself a reason to be
   careful generalising from any single one of them.

## Instrument provenance

Every instrument here is public domain or free for research use — a hard
constraint for a public repository, and the reason the commercial inventories
do not appear.

| Instrument | Source | Status |
|---|---|---|
| Cognitive Reflection Test | Frederick (2005); Toplak et al. (2014) | published, widely reproduced |
| Mini-IPIP Big Five | Donnellan et al. (2006) | IPIP items are public domain |
| Dark Triad Dirty Dozen | Jonason & Webster (2010) | free for research use |
| Fluid reasoning | authored here, in ICAR format (Condon & Revelle 2014) | original items, no norms |
| Economic games | Güth et al. (1982); Forsythe et al. (1994); Berg et al. (1995); Fehr & Gächter (2000) | paradigms, wording written here |
| Decision anomalies | Kahneman & Tversky (1979); Tversky & Kahneman (1974, 1981, 1983); Arkes & Blumer (1985) | classic problems, cited; sunk cost in the original wording |
| Risk and time | Holt & Laury (2002); Thaler (1981) | published designs |
| Strategic games | Nagel (1995); Arad & Rubinstein (2012) | published designs |

Deliberately excluded: WAIS, Raven's APM, NEO-PI-R, 16PF, MMPI, PCL-R, PPI-R —
all copyrighted and not reproducible here.

## Security

This repository talks to a paid API and is public, so the key handling is
defensive by construction:

- the key is read from the environment only, never a literal in code
- `.env` is gitignored; a pre-commit hook refuses to commit one
- every error path runs the key through `redact()` before it reaches a log
- CI runs gitleaks and asserts that no `.env` and no key-shaped string is
  tracked

## Licence

MIT — see [LICENSE](LICENSE). Instrument sources retain their own terms; see
the provenance table above.
