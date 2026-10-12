# More models through the same battery

The [main write-up](../README.md) is about one System One model, TypeSafe's
Jev. Since then, eight more models have appeared on OpenRouter's decisions
route, all on the same `/v1/systemone` contract, so the battery runs on them
unchanged. This page puts them side by side with Jev, the original chat
baseline (Claude Sonnet 5), and a second chat baseline (Claude Haiku 5.5).

The same caveats as the main write-up apply in full: this is a hobby project,
the human values are not a control group, and **no claims are made about any
model, company or product.** These are numbers recorded from a public API on
one day, and how they were produced.

## What was run

| Model | Type | Run | Records | Cost |
|---|---|---|---|---|
| `typesafe/jev-1.13-20260917` | System One | Sep 18 (committed run) | 4,680 | $0.09 |
| `anthropic/claude-sonnet-5` | chat, resampled | Sep 18 (committed run) | 4,680 | $2.74 |
| `openai/gpt-6-luna-decisions-20261006` | System One | Oct 12 | 5,880 | $0.13 |
| `microsoft/microsoft-decision-1-20261009` | System One | Oct 12 | 5,880 | $0.04 |
| `perplexity/pplx-decider-v1.1-27b-20261006` | System One | Oct 12 | 5,880 | $0.03 |
| `inception/mercury-decide-20260930` | System One | Oct 12 | 5,880 | $0.03 |
| `liquid/d1-20260930` | System One | Oct 12 | 5,880 | $0.04 |
| `upstage/solar-decide-flash-20261008` | System One | Oct 12 | 5,880 | $0.14 |
| `nace-ai/drex-v1.5-20261009` | System One | Oct 12 | 5,880 | $0.03 |
| `upstage/solar-decide-20260928` | System One | Oct 12 (resumed after an interruption) | 5,880 | $0.14 |
| `anthropic/claude-haiku-5.5` | chat, resampled | Oct 12 | 5,880 | $0.68 |

The Oct 12 runs are 147 probes × 4 personas × 10 replicates; the committed
Sep 18 run predates the 30 follow-up items and has 117 probes. Every measure
compared below comes from items present in both.

Reproduce:

```bash
jevbench compare data/raw/run_live_20260918T230710Z.jsonl data/raw/run_live_20261012*.jsonl
```

Solar Decide was throttled by its provider to about 25 calls a minute, and its
first attempt was stopped by a time limit at 62% with nothing saved, because
records were only written at the end of a run. The runner now writes each
record as it completes; the second attempt was stopped at 81% and finished
with `jevbench run --resume`, which keeps completed records and reruns only
the missing or failed ones. The committed file is the complete grid with no
duplicates.

## Read the health table first

[`results/comparison/health.csv`](../results/comparison/health.csv) exists to
stop silent holes being read as results, and on this run it caught three, two
of which were bugs in this repository.

![What the health table caught](../results/figures/health-checks.png)

**GPT-6 Luna Decisions refuses some items.** 240 of its 5,880 calls (4%) came
back `OpenAI refused to answer question "answer"`: the custody case, the trolley
estimates, the false-consensus and choosing/rejecting estimates, and a Dirty
Dozen item. The route reports a refusal as HTTP 502, so the client first logged
these as transport errors and retried each one five times. A refusal is now
recorded as one and never retried. None of the refused items feeds the
comparison below, but 44% of this model's yes/no (`Noul`) items are refused, so
it has no score on the follow-up study's estimate items.

**Neither Solar model can answer the p-beauty contest.** That item has 101
options (0–100), and the route rejects a `Choice` with more than 26. This is a
documented limit of the route rather than a model behaviour, and it costs each
of them one item.

**Haiku 5.5 truncated on its own reasoning.** It reasons before answering, and
the reasoning counts against the reply cap: on the first run 183 calls spent
all 512 tokens on reasoning and returned nothing, concentrated on the numeric
estimate items — the same shape of hole the main write-up describes for the
first Sonnet runs. The cap is now configurable and recorded per record; the
committed Haiku run used 4,096 and has 3 unresolved replies (0.06%), against
Sonnet's 9 at 512. The truncated run was discarded, not mixed in.

### How a chat model's reply becomes an answer

A System One model answers in a typed distribution and has nowhere to go
wrong. A chat model answers in text, so the chat arm's results depend on how
that text is read, and the [how-it-works figure](../results/figures/how-it-works.png)
now shows each step:

- **The prompt lists the options and asks for exactly one key** and nothing
  else. Haiku 5.5 complied on 98.7% of replies, Sonnet 5 on 93.7%; most of
  Sonnet's other replies echo the option line (`pressure: pressure`).
- **A reply that is not exactly a key is read for the option it names**: the
  last one mentioned, so reasoning that restates the problem's numbers before
  committing is read for the commitment, except that a leading `key:` wins.
  That exception is new. The earlier parser read Sonnet's `$1: Offer $1, keep
  $9` as $9, and the same for one public-goods reply; two cells moved (the
  rational-agent ultimatum offer from 0.18 to 0.10 of the pie and one
  conditional contribution from 0.82 to 0.72), and neither is reported
  anywhere in the write-up.
- **A true/false item takes only a bare true or false.** Haiku five times
  replied along the lines of "I can't answer this with true or false", which
  the earlier parser counted as *false*. These now count as unresolved, as do
  replies naming no option at all (Haiku twice answered `B` where there are no
  lettered options). Haiku's bare `45-55` now matches the band `45-55%`.
- **Unresolved replies are dropped and counted**, never guessed:
  `n_unresolved` in [`health.csv`](../results/comparison/health.csv).
- **Eleven follow-up items ask what proportion of people said yes** (the
  trolley, Knobe, false-consensus, choosing/rejecting and categorisation
  estimates). Asked of a System One model, `P(true)` stands for that
  proportion. A chat model is asked the same question and told to reply true
  or false, which cannot carry a number: ten replies are a vote on whether
  most people said yes, not an estimate. Those 440 Haiku records are now left
  out of every chat-arm statistic and counted as `n_not_measurable`; before
  this, `statistics.csv` listed them as estimates. None fed the comparison
  above, and the Sep 18 Sonnet run predates the items.

Answers are re-read from the stored reply text every time a run is loaded, so
these fixes reach the committed runs without editing them.

## Closeness to human values

![Models against human values](../results/figures/models-scatter.png)

Mean absolute distance from the published human value over the 14 measures on
a shared 0–1 scale, and the correlation `r` with them across measures
([`fidelity.csv`](../results/comparison/fidelity.csv)):

| Model | Neutral: distance | Neutral: r | As typical human: distance | As typical human: r |
|---|---|---|---|---|
| Solar Decide Flash | **0.21** | +0.20 | **0.11** | +0.76 |
| Drex 1.5 | 0.27 | +0.00 | 0.29 | −0.10 |
| d1 | 0.32 | +0.09 | 0.19 | +0.66 |
| Jev 1.13 | 0.32 | −0.15 | 0.14 | +0.76 |
| Mercury Decide | 0.33 | −0.06 | 0.20 | +0.54 |
| GPT-6 Luna Decisions | 0.34 | −0.38 | 0.19 | +0.11 |
| Decider v1.1 27B | 0.34 | −0.42 | 0.15 | +0.67 |
| Claude Sonnet 5 | 0.35 | +0.02 | 0.17 | +0.83 |
| Microsoft-Decision-1 | 0.37 | −0.62 | 0.18 | +0.59 |
| Solar Decide | 0.43 | −0.13 | 0.15 | +0.79 |
| Claude Haiku 5.5 | 0.49 | −0.54 | 0.18 | +0.88 |

The pattern from the main write-up holds across every model: **answering
neutrally, none of them looks like people** (no correlation better than +0.20,
several strongly negative), and **one sentence asking for a typical human
moves nearly all of them a long way toward people.** Two do not move: Drex 1.5
gets no closer, and GPT-6 Luna Decisions gets closer on average but without
learning which effects are strong (r +0.11).

### Why the top of that table should not be read as a ranking

![The framing reversal by model](../results/figures/framing-contrast.png)

Solar Decide Flash comes out closest, and the reason matters more than the
ranking. Its answers sit nearer 0.5 than any other model's, and most of the
human reference values sit in the middle of the scale too — on average 0.18
from 0.5. A model that hedges everywhere therefore scores a small distance
without reproducing any effect.

The framing reversal shows it. Humans pick the certain option 72% of the time
in the gain frame and 22% in the loss frame, a 50-point reversal; the main
write-up already argues that the contrast, not either level, is the robust
quantity. Gain minus loss, in points:

| | Human | d1 | Solar | Mercury | Jev | Decider | Luna | Solar Flash | Drex | MS-Decision-1 | Sonnet 5 | Haiku 5.5 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Neutral | 50 | **54** | 80 | 19 | 29 | 17 | 3 | 9 | −8 | −48 | 100 | 0 |
| As typical human | 50 | 56 | **50** | 34 | 30 | 45 | 21 | 4 | −51 | −10 | 100 | 100 |

On the effect itself, Solar Decide Flash shows almost none, d1 reproduces it
almost exactly under both framings, Solar Decide lands on it exactly when asked
to answer as a person, the two chat models show it at full strength or not at all
(resampled answers saturate at 0 or 1), and Drex 1.5 and Microsoft-Decision-1
reverse it. Distance from human levels and reproduction of human effects are
different questions, and this battery's one summary number answers only the
first.

### Other things worth noting

- **The two Solar models are opposites despite sharing a base model** (both
  are built on Solar Mini 4). Answering neutrally, Flash hedges toward 0.5 on
  everything and lands nearest people, while Solar Decide is the furthest of
  any System One model: it plays the games almost as game theory prescribes,
  sending 1% in the trust game and contributing 2% to the public good (people:
  about half). Asked to answer as a person, both move close to people.
- **Haiku 5.5 is the most extreme answerer when asked to be a typical person**,
  furthest from 0.5 of any model (answering neutrally, only Solar Decide is more
  extreme). In that framing it gets the cognitive reflection items right only 6%
  of the time (people: 41%), and continues the sunk-cost project every time.
- **The sunk-cost item is the one nothing reproduces under neutral framing**:
  every model, System One or chat, abandons the project (≤ 0.07, people 0.85).
- **No model reproduces the conjunction fallacy unprompted** except Drex 1.5
  (0.58) and Solar Decide Flash (0.70); asked to answer as a person, all but
  Luna (0.50) and Drex (0.61) reach 0.83 or more, against people's 0.85.

## Limitations specific to this comparison

1. **Two dates.** Jev and Sonnet were run on Sep 18 and everything else on
   Oct 12. Jev is pinned to a dated version, but the route and gateway may have
   changed in between.
2. **Microsoft-Decision-1 is not reproducible.** Its listing says its weights
   are updated continually while the API stays the same; the served name
   carries a date that does not change when they are.
3. **One summary number is not a ranking**, for the reason above. It is
   reported because it is what the existing analysis computes, not because it
   orders the models.
4. **Fourteen measures** is a small base for a correlation; an `r` of ±0.2 is
   indistinguishable from none.
5. Everything in the [main limitations](../README.md#limitations) applies.
