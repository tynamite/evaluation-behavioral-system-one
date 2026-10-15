# More models through the same battery

The [main write-up](../README.md) is about one System One model, TypeSafe's
Jev. Eleven more models are on OpenRouter's decisions route, all on the same
`/v1/systemone` contract, so the battery runs on them unchanged. This page puts
them side by side with Jev and two chat models, Claude Sonnet 5.5 and Claude
Haiku 5.5, resampled ten times per item.

The same caveats as the main write-up apply in full: this is a hobby project,
the human values are not a control group, and **no claims are made about any
model, company or product.** These are numbers recorded from a public API on
12–13 October 2026, and how they were produced.

## What was run

Every model got the same grid: 147 probes × 5 prompts × 10 replicates, 7,350
calls. On 13 October the ten System One models were also asked the ten
population questions added to the follow-up study (no persona, 10 replicates:
100 calls each, appended to the same files); the costs below include them.

Drex 1.5 and Drex 2.0 (Nace AI) were added on 15 October with the battery as it
stands now: 6,850 calls each. The difference is the follow-up study's 15
population questions, which the battery now asks under the neutral prompt only;
the 12–13 October runs also asked them under the other four prompts (600 calls
each). No comparison on this page uses those 600 calls.

| Model | Type | Cost |
|---|---|---|
| `typesafe/jev-1.13-20260917` | System One | $0.14 |
| `openai/gpt-6-luna-decisions-20261006` | System One | $0.17 |
| `microsoft/microsoft-decision-1-20261009` | System One | $0.05 |
| `perplexity/pplx-decider-v1.1-27b-20261006` | System One | $0.03 |
| `inception/mercury-decide-20260930` | System One | $0.03 |
| `liquid/d1-20260930` | System One | $0.05 |
| `upstage/solar-decide-flash-20261008` | System One | $0.17 |
| `upstage/solar-decide-20260928` | System One | $0.17 |
| `cloudflare/clef-flash` | System One | $0.05 |
| `cloudflare/clef` | System One | $0.12 |
| `nace-ai/drex-v1.5-20261009` | System One | $0.04 |
| `nace-ai/drex-v2.0-20261009` | System One | $0.06 |
| `anthropic/claude-sonnet-5.5` | chat, resampled | $8.84 |
| `anthropic/claude-haiku-5.5` | chat, resampled | $0.84 |

The README's main charts carry four of these models — Jev, GPT-6 Luna
Decisions, Clef and d1 — and this page has all of them.

Reproduce:

```bash
jevbench compare data/raw/run_live_*.jsonl
```

## Read the health table first

[`results/comparison/health.csv`](../results/comparison/health.csv) exists to
stop silent holes being read as results.

![What the health table caught](../results/figures/health-checks.png)

**GPT-6 Luna Decisions refuses some items.** 300 of its 7,450 calls (4%) came
back `OpenAI refused to answer question "answer"`, across 30 item × prompt
cells: the trolley, Knobe, categorisation, false-consensus and
choosing/rejecting (custody case) estimates, five of the ten population
questions added later (framing gain, Allais pair 1, Linda, base rate, sunk
cost), the false-consensus choices
themselves, and one Dirty Dozen item (`dd_09`). The route reports a refusal as
HTTP 502; the client records it as a refusal and does not retry it. None of
the refused items feeds the comparison below, but 39% of its yes/no (`Noul`)
calls are refused, leaving it with no answer in 30 item × prompt cells, mostly
the follow-up study's estimate items.

**Neither Solar model can answer the p-beauty contest.** That item has 101
options (0–100), and the route rejects a `Choice` with more than 26. This is a
documented limit of the route rather than a model behaviour, and it costs each
of them one item.

**Both Clef endpoints intermittently reject one item.** On the average-speed
reasoning item, a few calls came back HTTP 400 with Cloudflare reporting the
request itself as malformed. The same request succeeded on other attempts, so
this is the provider's rather than the item's; `jevbench run --resume` retried
the failures until every call succeeded. Both committed runs have no errors.

**Solar Decide is throttled by its provider** to about 25 calls a minute, so
its run took about two hours against minutes for the others. Runs write each
record as it completes, and `--resume` finishes an interrupted one.

### How a chat model's reply becomes an answer

A System One model answers in a typed distribution, so there is no text to
misread (it can still refuse or reject an item, as above). A chat model answers
in text, so the chat arm's results depend on how that text is read, and the
[how-it-works figure](../results/figures/how-it-works.png) shows each step:

- **The prompt lists the options and asks for exactly one key** and nothing
  else. Haiku 5.5 replied with exactly a key 99% of the time, Sonnet 5.5
  91%; most of Sonnet's other replies reason first and then commit.
- **A reply that is not exactly a key is read for the option it names**: the
  last one mentioned, so reasoning that restates the problem's numbers before
  committing is read for the commitment, except that a leading `key:` wins
  (`$1: Offer $1, keep $9` is $1).
- **A true/false item takes only a bare true or false.** "I can't answer this
  with true or false" is not *false*.
- **Unresolved replies are dropped and counted**, never guessed:
  `n_unresolved` in [`health.csv`](../results/comparison/health.csv) — 3 for
  Sonnet 5.5 and 16 for Haiku 5.5, of 6,800 scorable replies each.
- **Eleven follow-up items ask what proportion of people said yes** (the
  trolley, Knobe, false-consensus, choosing/rejecting and categorisation
  estimates). Asked of a System One model, `P(true)` stands for that
  proportion. A chat model is asked the same question and told to reply true
  or false, which cannot carry a number: ten replies are a vote on whether
  most people said yes, not an estimate. Those 550 records per chat model are
  left out of every chat-arm statistic and counted as `n_not_measurable`.
- **Room to reason.** Both models reason before answering on some items, and
  the reasoning counts against the reply cap, so the cap is 4,096 tokens.

Answers are re-read from the stored reply text every time a run is loaded.

## Closeness to human values

![Models against human values](../results/figures/models-scatter.png)

Mean absolute distance from the published human value over the 14
probability-scale measures (each on 0–1), and the correlation `r` with them
across measures ([`fidelity.csv`](../results/comparison/fidelity.csv)). "As a
person" is the typical-person instruction quoted in the
[README](../README.md#asked-to-answer-like-a-person-it-moves-on-some-effects-and-not-others);
"no steer" is the same instruction without "not the textbook-correct answer".

| Model | No instruction: distance | r | As a person: distance | r | No steer: distance | r |
|---|---|---|---|---|---|---|
| Solar Decide Flash | **0.23** | +0.17 | **0.14** | +0.64 | 0.17 | +0.41 |
| Clef Flash | **0.23** | +0.08 | 0.18 | +0.38 | 0.19 | +0.43 |
| Drex 2.0 | **0.23** | +0.15 | 0.18 | +0.42 | 0.20 | +0.28 |
| Clef | 0.28 | +0.00 | 0.20 | +0.44 | 0.21 | +0.34 |
| Drex 1.5 | 0.29 | −0.01 | 0.28 | −0.03 | 0.28 | −0.06 |
| Mercury Decide | 0.31 | −0.12 | 0.21 | +0.44 | 0.23 | +0.30 |
| Jev 1.13 | 0.31 | −0.21 | 0.18 | +0.39 | 0.20 | +0.25 |
| d1 | 0.31 | +0.03 | 0.23 | +0.41 | 0.28 | +0.29 |
| Decider v1.1 27B | 0.34 | −0.47 | **0.14** | +0.68 | 0.18 | +0.54 |
| GPT-6 Luna Decisions | 0.35 | −0.31 | 0.21 | +0.20 | 0.27 | −0.31 |
| Microsoft-Decision-1 | 0.35 | −0.54 | 0.19 | +0.54 | 0.21 | +0.32 |
| Claude Sonnet 5.5 | 0.37 | −0.22 | 0.20 | +0.80 | 0.15 | **+0.89** |
| Solar Decide | 0.43 | −0.28 | 0.16 | +0.73 | **0.13** | +0.79 |
| Claude Haiku 5.5 | 0.49 | −0.57 | 0.18 | **+0.83** | 0.23 | +0.63 |

The cognitive reflection measure is Frederick's three items and the ultimatum
rejection measure the $1 offer, to match what the human values measure (see
[BENCHMARKS.md](BENCHMARKS.md)).

The pattern from the main write-up holds across every model: **answering with
no instruction, none of them looks like people** (no correlation better than
+0.17, several strongly negative), and **asking for a typical person moves
every one of them closer**, Drex 1.5 only barely. How far differs a lot. The
chat models and Solar Decide learn which effects are strong (r +0.73 to +0.89
under one of the two versions); Decider v1.1 27B, Solar Decide Flash and
Microsoft-Decision-1 come next (+0.54 to +0.68); Jev, Clef, Clef Flash, d1,
Mercury Decide and Drex 2.0 only partly (+0.25 to +0.44); GPT-6 Luna Decisions
hardly at all; and Drex 1.5 not at all. Its distance moves from 0.29 to 0.28
and its correlation stays at zero (−0.03; −0.06 without the steer): the
instruction barely changes its answers.

**The steer matters more for some models than others.** Without "not the
textbook-correct answer", most System One models fit people a little less well
(Jev's r falls from +0.39 to +0.25, Decider's from +0.68 to +0.54), which says
part of their move toward people was the instruction's push. Sonnet 5.5,
Solar Decide go the other way and fit people *better* without it (Sonnet's
distance falls from 0.20 to 0.15), and Clef Flash's correlation rises
slightly. GPT-6 Luna Decisions reverses: with the
plain instruction its correlation is −0.31.

### Why the top of that table should not be read as a ranking

![The framing reversal by model](../results/figures/framing-contrast.png)

Solar Decide Flash and Clef Flash come out closest with no instruction, and the
reason matters more than the ranking. Their answers sit nearer 0.5 than any
other model's (on average 0.20 and 0.16 from it), and most of the human
reference values sit in the middle of the scale too — on average 0.18 from
0.5. A model that hedges everywhere therefore scores a small distance without
reproducing any effect. Drex 2.0, a close third, is the exception: its answers
are 0.26 from 0.5 on average, about as far as Jev's, and it shows the largest
framing effect of any System One model asked with no instruction.

The framing reversal shows it. Humans pick the certain option 72% of the time
in the gain frame and 22% in the loss frame, a 50-point reversal; the main
write-up argues that the contrast, not either level, is the robust quantity.
Gain minus loss, in points:

| | Human | d1 | Solar | Clef | Mercury | Jev | Decider | Luna | Solar Flash | Clef Flash | MS-Decision-1 | Drex 1.5 | Drex 2.0 | Sonnet 5.5 | Haiku 5.5 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| No instruction | 50 | 24 | 26 | 26 | 0 | 1 | 3 | 16 | 10 | 2 | −16 | −24 | **34** | 20 | 0 |
| As a person | 50 | 31 | **60** | 18 | 18 | 4 | 21 | 11 | 0 | 2 | −24 | −55 | 41 | 100 | 90 |
| No steer | 50 | 22 | **60** | 16 | 13 | 7 | 14 | 7 | 2 | 8 | −20 | −45 | 43 | 100 | 100 |

No System One model shows the full human effect without being asked; Drex 2.0
comes closest, at 34 points. Asked to answer as a person, only Solar Decide (60)
and Drex 2.0 (41, or 43 without the steer) come near it. Solar Decide Flash and
Clef Flash, two of the three closest to people by distance, show almost none in
any condition. Microsoft-Decision-1 reverses it, and Drex 1.5 reverses it
strongly once asked to be a person (−55, the largest swing of any System One
model, in the wrong direction). The chat models are near all or nothing once
asked to be a person, 90 to 100 points (resampled answers saturate at 0 or 1). Distance from human levels
and reproduction of human effects are different questions, and this battery's
one summary number answers only the first.

### Other things worth noting

- **The two Solar models are opposites despite sharing a base model** (both
  are built on Solar Mini 4). With no instruction, Flash hedges toward 0.5 on
  everything and lands nearest people, while Solar Decide is the furthest of
  any System One model: it plays the games almost as game theory prescribes,
  sending nothing in the trust game and contributing 1% to the public good
  (people: about half). Asked to answer as a person, both move close to people.
- **The sunk-cost item splits the models.** With no instruction, every model
  abandons the project (≤ 0.16, people 0.85). Asked to answer as a person, in
  Arkes and Blumer's original wording, Sonnet 5.5 continues every time, Haiku
  5.5 (0.80) and Solar Decide (0.76) come close to people, and Jev, d1, Clef
  and Mercury Decide stay at 0.17 or below.
- **The chat models are the most extreme answerers when asked to be a typical
  person**, furthest from 0.5 of any model (Sonnet 0.36 and Haiku 0.31 from it
  on average). In that framing both get Frederick's cognitive reflection items
  right 0% of the time (people: 41%); without the steer, Sonnet gets half of
  them right and Haiku still none.
- **Clef Flash is the only model that over-trusts unprompted**, sending 65% in
  the trust game (people: 50%), and with no instruction it answers Frederick's
  cognitive reflection items correctly least often of any model (66%; people
  41%, every other model 77% or more). It is a fine-tune of Qwen3.5-9B.
- **Only the Clef models, Solar Decide Flash and Drex 1.5 show the conjunction
  fallacy unprompted** — Clef at 0.88 against people's 0.85, Solar Decide Flash
  0.69, Clef Flash 0.59, Drex 1.5 0.58 — and every other model stays at 0.25 or
  below. Asked to answer as a person, all but Luna (0.50) and the two Drex
  models (0.60 and 0.39) reach 0.83 or more.
- **The two Drex versions behave like different models.** Drex 1.5 barely
  responds to being asked to answer as a person, and when it does respond, it
  responds the wrong way on framing. Drex 2.0 is among the closest to people
  with no instruction, without hedging, and shows the largest unprompted
  framing effect of any System One model.
- **Clef and Clef Flash differ the way the Solar pair do.** Clef (listed on
  OpenRouter as built on Qwen3.8-27B) does not hedge: it shows about half the
  human framing effect with no instruction (26 points) where Flash shows none.

## Simulate or estimate (follow-up H4)

The follow-up study's items are each asked two ways: as the item itself with the
typical-person prompt ("simulate"), and as a population question with no persona
("estimate"). Its preregistered H4 predicts that estimating is more accurate.
Each statistic is compared with the original study's published value (Many
Labs 2 reports only effect sizes): 15 from the new items and 8 from the six
items reused from the first project, whose population questions were asked on
13 October. The preregistered test is a one-sided Wilcoxon signed-rank test on
the absolute errors, in each item's own units, so the percentage items and the
1–7 ratings weigh most. The mean errors, and the second p value, scale each
error to its item's range instead; that check was chosen after seeing the data
([`followup_h4.csv`](../results/comparison/followup_h4.csv)):

| Model | Simulate: scaled error | Estimate: scaled error | Estimate closer | p (preregistered) | p (scaled) |
|---|---|---|---|---|---|
| GPT-6 Luna Decisions | 0.19 | 0.15 | 11 of 13 | 0.011 | 0.073 |
| Jev 1.13 | 0.23 | 0.17 | 14 of 23 | 0.015 | 0.043 |
| Mercury Decide | 0.23 | 0.20 | 17 of 23 | 0.026 | 0.071 |
| d1 | 0.24 | 0.18 | 13 of 23 | 0.071 | 0.111 |
| Solar Decide | 0.16 | 0.13 | 15 of 23 | 0.143 | 0.188 |
| Drex 1.5 | 0.25 | 0.25 | 14 of 23 | 0.165 | 0.241 |
| Drex 2.0 | 0.20 | 0.20 | 12 of 23 | 0.311 | 0.482 |
| Decider v1.1 27B | 0.15 | 0.14 | 12 of 23 | 0.343 | 0.435 |
| Clef | 0.20 | 0.16 | 12 of 23 | 0.377 | 0.250 |
| Solar Decide Flash | 0.16 | 0.18 | 11 of 23 | 0.482 | 0.710 |
| Microsoft-Decision-1 | 0.18 | 0.19 | 13 of 23 | 0.506 | 0.458 |
| Clef Flash | 0.23 | 0.26 | 11 of 23 | 0.542 | 0.710 |

Estimating has the lower mean scaled error for eight of the twelve models; for
Solar Decide Flash, Microsoft-Decision-1, Clef Flash and Drex 2.0 it is higher
(for both Drex models the two differ by under 0.01). Three clear p < 0.05 on the
preregistered test, and only Jev clears it on the scaled one. The twelve tests
share their items, so they are not independent evidence.
GPT-6 Luna Decisions has only 13 pairs because its refusals leave ten
statistics without an estimate. The chat models are left out: a true/false
reply cannot carry a proportion.

## Limitations specific to this comparison

1. **Microsoft-Decision-1, Clef and Clef Flash are not reproducible.**
   Microsoft-Decision-1's listing says its weights are updated continually
   while the API stays the same; the served name carries a date that does not
   change when they are. Clef and Clef Flash are served as `cloudflare/clef` and
   `cloudflare/clef-flash` with no date at all, so a later run may meet a
   different model under the same name.
2. **One summary number is not a ranking**, for the reason above. It is
   reported because it is what the existing analysis computes, not because it
   orders the models.
3. **Fourteen measures** is a small base for a correlation; an `r` of ±0.2 is
   indistinguishable from none.
4. Everything in the [main limitations](../README.md#limitations) applies.
