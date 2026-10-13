# More models through the same battery

The [main write-up](../README.md) is about one System One model, TypeSafe's
Jev. Nine more models are on OpenRouter's decisions route, all on the same
`/v1/systemone` contract, so the battery runs on them unchanged. This page puts
them side by side with Jev and two chat models, Claude Sonnet 5.5 and Claude
Haiku 5.5, resampled ten times per item.

The same caveats as the main write-up apply in full: this is a hobby project,
the human values are not a control group, and **no claims are made about any
model, company or product.** These are numbers recorded from a public API on
12–13 October 2026, and how they were produced.

## What was run

Every model got the same grid: 147 probes × 5 prompts × 10 replicates, 7,350
calls.

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

**GPT-6 Luna Decisions refuses some items.** 250 of its 7,350 calls (3%) came
back `OpenAI refused to answer question "answer"`, across 25 item × prompt
cells: the trolley, Knobe, categorisation, false-consensus and
choosing/rejecting (custody case) estimates, the false-consensus choices
themselves, and one Dirty Dozen item (`dd_09`). The route reports a refusal as
HTTP 502; the client records it as a refusal and does not retry it. None of
the refused items feeds the comparison below, but 37% of its yes/no (`Noul`)
calls are refused, leaving it with no answer in 25 item × prompt cells, mostly
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
  `n_unresolved` in [`health.csv`](../results/comparison/health.csv) — 9 for
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
| Clef | 0.28 | +0.00 | 0.20 | +0.44 | 0.21 | +0.34 |
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
every one of them closer.** How far differs a lot. The chat models and Solar
Decide learn which effects are strong (r +0.73 to +0.89 under one of the two
versions); Decider v1.1 27B, Solar Decide Flash and Microsoft-Decision-1 come
next (+0.54 to +0.68); Jev, Clef, Clef Flash, d1 and Mercury Decide only partly
(+0.25 to +0.44); and GPT-6 Luna Decisions hardly at all.

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
reproducing any effect.

The framing reversal shows it. Humans pick the certain option 72% of the time
in the gain frame and 22% in the loss frame, a 50-point reversal; the main
write-up argues that the contrast, not either level, is the robust quantity.
Gain minus loss, in points:

| | Human | d1 | Solar | Clef | Mercury | Jev | Decider | Luna | Solar Flash | Clef Flash | MS-Decision-1 | Sonnet 5.5 | Haiku 5.5 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| No instruction | 50 | 24 | 26 | 26 | 0 | 1 | 3 | 16 | 10 | 2 | −16 | 20 | 0 |
| As a person | 50 | 31 | **60** | 18 | 18 | 4 | 21 | 11 | 0 | 2 | −24 | 100 | 90 |
| No steer | 50 | 22 | **60** | 16 | 13 | 7 | 14 | 7 | 2 | 8 | −20 | 100 | 100 |

No System One model shows the human effect without being asked, and only
Solar Decide comes near it when asked. Solar Decide Flash and Clef Flash, the
two closest to people by distance, show almost none in any condition;
Microsoft-Decision-1 reverses it; the chat models are near all or nothing once
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
  abandons the project (≤ 0.08, people 0.85). Asked to answer as a person, in
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
- **Only the Clef models and Solar Decide Flash show the conjunction fallacy
  unprompted** — Clef at 0.88 against people's 0.85, Solar Decide Flash 0.69,
  Clef Flash 0.59 — and every other model stays at 0.25 or below. Asked to
  answer as a person, all but Luna (0.50) reach 0.83 or more.
- **Clef and Clef Flash differ the way the Solar pair do.** Clef (listed on
  OpenRouter as built on Qwen3.8-27B) does not hedge: it shows about half the
  human framing effect with no instruction (26 points) where Flash shows none.

## Simulate or estimate (follow-up H4)

The follow-up study's items are each asked two ways: as the item itself with the
typical-person prompt ("simulate"), and as a population question with no persona
("estimate"). Its preregistered H4 predicts that estimating is more accurate.
Mean error over 15 Many Labs 2 statistics, each scaled to its item's range, and
the one-sided Wilcoxon signed-rank test the preregistration names
([`followup_h4.csv`](../results/comparison/followup_h4.csv)):

| Model | Simulate: error | Estimate: error | Estimate closer | p |
|---|---|---|---|---|
| d1 | 0.22 | 0.16 | 11 of 15 | 0.021 |
| Jev 1.13 | 0.22 | 0.15 | 8 of 15 | 0.165 |
| Mercury Decide | 0.20 | 0.15 | 12 of 15 | 0.047 |
| Solar Decide | 0.15 | 0.12 | 11 of 15 | 0.151 |
| Decider v1.1 27B | 0.13 | 0.10 | 9 of 15 | 0.211 |
| Solar Decide Flash | 0.16 | 0.13 | 9 of 15 | 0.339 |
| Clef | 0.16 | 0.14 | 7 of 15 | 0.445 |
| Clef Flash | 0.21 | 0.20 | 8 of 15 | 0.339 |
| Microsoft-Decision-1 | 0.14 | 0.14 | 9 of 15 | 0.423 |
| GPT-6 Luna Decisions | 0.14 | 0.15 | 8 of 10 | 0.216 |

Estimating has the lower mean error for nine of the ten models, but only d1 and
Mercury Decide clear p < 0.05 on their own, and with ten models tested two or
more would do so by chance about 9% of the time. GPT-6 Luna Decisions is the
exception, and has only 10 pairs because its refusals leave five statistics
without an estimate. The chat models are left
out: a true/false reply cannot carry a proportion.

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
