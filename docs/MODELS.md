# More models through the same battery

The [main write-up](../README.md) is about one System One model, TypeSafe's
Jev. Since then, nine more models have appeared on OpenRouter's decisions
route, all on the same `/v1/systemone` contract, so the battery runs on them
unchanged. This page puts them side by side with Jev, the original chat
baseline (Claude Sonnet 5), and a second chat baseline (Claude Haiku 5.5).

The same caveats as the main write-up apply in full: this is a hobby project,
the human values are not a control group, and **no claims are made about any
model, company or product.** These are numbers recorded from a public API on
two days (Sep 18 and Oct 12, 2026), and how they were produced.

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
| `cloudflare/clef-flash` | System One | Oct 12 | 5,880 | $0.07 |
| `cloudflare/clef` | System One | Oct 12 | 5,880 | $0.42 |
| `upstage/solar-decide-20260928` | System One | Oct 12 (resumed after an interruption) | 5,880 | $0.14 |
| `anthropic/claude-haiku-5.5` | chat, resampled | Oct 12 | 5,880 | $0.68 |

The README's main charts carry four of these models — Jev, GPT-6 Luna
Decisions, Clef and d1 — and this page has all of them.

Drex 1.5 (`nace-ai/drex-v1.5-20261009`) was run on Oct 12 too and has since
been replaced in the comparison by Cloudflare's Clef Flash; its run file stays
in `data/raw/` and `jevbench compare` reproduces its numbers if passed it.

The Oct 12 runs are 147 probes × 4 personas × 10 replicates; the committed
Sep 18 run predates the 30 follow-up items and has 117 probes. Every measure
compared below comes from items present in both.

Reproduce:

```bash
jevbench compare data/raw/run_live_20260918T230710Z.jsonl \
  $(ls data/raw/run_live_20261012*.jsonl | grep -v drex)
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
back `OpenAI refused to answer question "answer"`, across 24 item × persona
cells: the trolley, Knobe, categorisation, false-consensus and
choosing/rejecting (custody case) estimates, the false-consensus choices
themselves, and one Dirty Dozen item (`dd_09`). The route reports a refusal as
HTTP 502, so the client first logged these as transport errors and tried each
one five times. A refusal is now
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
committed Haiku run used 4,096 and has 3 unresolved replies (0.05%: two bare
`B` replies and one that still hit the 4,096 cap), against Sonnet's 9 at 512.
The truncated run, and its 183 empty replies, was discarded, not mixed in.

**Not in the table: both Clef endpoints intermittently reject one item.**
The runner logged this one as errors, and they were cleared before the run
was committed, so `health.csv` shows neither with any. On the
average-speed reasoning item, half of the first 40 calls came back HTTP 400
with Cloudflare reporting the request itself as malformed. The same request,
with the same option order, succeeded on other attempts, so this is the
provider's fault rather than the item's; `jevbench run --resume` retried the
failures until all 40 succeeded, over seven passes. Clef did the same on the
same item (11 of 40 calls, four passes). Both committed runs have no errors.
Both are also served under undated names, and Microsoft-Decision-1 under a
date that does not change when its weights do (see the limitations).

### How a chat model's reply becomes an answer

A System One model answers in a typed distribution, so there is no text to
misread (it can still refuse or reject an item, as above). A chat model answers in text, so the chat arm's results depend on how
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
  the earlier parser counted as *false*. All five were on the proportion
  items below, so they now sit with those as not measurable. Replies naming no
  option at all (Haiku twice answered `B` where there are no lettered options)
  count as unresolved. Haiku's bare `45-55` now matches the band `45-55%`.
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
  below, and the Sep 18 Sonnet run predates the items.

Answers are re-read from the stored reply text every time a run is loaded, so
these fixes reach the committed runs without editing them.

## Closeness to human values

![Models against human values](../results/figures/models-scatter.png)

Mean absolute distance from the published human value over the 14
probability-scale measures (each on 0–1), and the correlation `r` with them across measures
([`fidelity.csv`](../results/comparison/fidelity.csv)):

| Model | Neutral: distance | Neutral: r | As typical human: distance | As typical human: r |
|---|---|---|---|---|
| Clef Flash | **0.22** | +0.07 | 0.17 | +0.48 |
| Solar Decide Flash | 0.23 | +0.20 | **0.12** | +0.73 |
| Clef | 0.28 | −0.02 | 0.16 | +0.70 |
| Jev 1.13 | 0.31 | −0.15 | 0.13 | +0.76 |
| Mercury Decide | 0.31 | −0.07 | 0.20 | +0.56 |
| d1 | 0.32 | +0.08 | 0.19 | +0.67 |
| Decider v1.1 27B | 0.33 | −0.43 | 0.13 | +0.71 |
| GPT-6 Luna Decisions | 0.35 | −0.37 | 0.21 | +0.09 |
| Claude Sonnet 5 | 0.35 | +0.01 | 0.20 | +0.79 |
| Microsoft-Decision-1 | 0.38 | −0.61 | 0.17 | +0.63 |
| Solar Decide | 0.43 | −0.13 | 0.15 | +0.77 |
| Claude Haiku 5.5 | 0.51 | −0.52 | 0.18 | +0.87 |

The cognitive reflection measure is Frederick's three items and the ultimatum
rejection measure the $1 offer, to match what the human values measure (see
[BENCHMARKS.md](BENCHMARKS.md)).

The pattern from the main write-up holds across every model: **answering
neutrally, none of them looks like people** (no correlation better than +0.20,
several strongly negative), and **a short instruction to answer like a typical
human moves nearly all of them a long way toward people** (the instruction is
quoted in the [README](../README.md#asked-to-answer-like-a-person-it-moves-a-long-way);
it also says "not the textbook-correct answer", so it steers as well as asks).
Two move less: Clef Flash gets only a little closer (0.22 to 0.17) and learns
only part of which effects are strong (r +0.48), and GPT-6 Luna Decisions gets closer on average but
without learning which effects are strong (r +0.09).

### Why the top of that table should not be read as a ranking

![The framing reversal by model](../results/figures/framing-contrast.png)

Clef Flash and Solar Decide Flash come out closest, and the reason matters
more than the ranking. Answering neutrally, their answers sit nearer 0.5 than
any other model's (on average 0.17 and 0.20 from it), and most of the human
reference values sit in the middle of the scale too — on average 0.18 from
0.5. A model that hedges everywhere therefore scores a small distance
without reproducing any effect.

The framing reversal shows it. Humans pick the certain option 72% of the time
in the gain frame and 22% in the loss frame, a 50-point reversal; the main
write-up already argues that the contrast, not either level, is the robust
quantity. Gain minus loss, in points:

| | Human | d1 | Solar | Mercury | Jev | Clef | Decider | Luna | Solar Flash | Clef Flash | MS-Decision-1 | Sonnet 5 | Haiku 5.5 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Neutral | 50 | **54** | 80 | 19 | 29 | 27 | 17 | 3 | 9 | 0 | −48 | 100 | 0 |
| As typical human | 50 | 56 | **50** | 34 | 30 | 23 | 45 | 21 | 4 | 17 | −10 | 100 | 100 |

On the effect itself, Solar Decide Flash shows almost none, Clef Flash none
without an instruction and a third of it when asked to answer as a person, d1 reproduces it
almost exactly under both framings, Solar Decide lands on it exactly when asked
to answer as a person, the two chat models show it as 100 points or 0
(resampled answers saturate at 0 or 1), and Microsoft-Decision-1 reverses it. Distance from human levels and reproduction of human effects are
different questions, and this battery's one summary number answers only the
first.

### Other things worth noting

- **The two Solar models are opposites despite sharing a base model** (both
  are built on Solar Mini 4). Answering neutrally, Flash hedges toward 0.5 on
  everything and lands nearest people, while Solar Decide is the furthest of
  any System One model: it plays the games almost as game theory prescribes,
  sending 1% in the trust game and contributing 2% to the public good (people:
  about half). Asked to answer as a person, both move close to people.
- **The two chat models are the most extreme answerers when asked to be a
  typical person**, furthest from 0.5 of any model (Sonnet 0.36 and Haiku 0.35
  from it on average, the next 0.26). In that framing both get Frederick's
  cognitive reflection items right 0% of the time (people: 41%), and Haiku
  continues the sunk-cost project every time.
- **Clef Flash is the only model that over-trusts unprompted**, sending 65% in
  the trust game (people: 50%), and with no instruction it answers Frederick's
  cognitive reflection items correctly least often of any model (65%; people
  41%, every other model 78% or more). It is a fine-tune of Qwen3.5-9B.
- **The sunk-cost item is missed by the widest margin under neutral framing**:
  every model, System One or chat, abandons the project (≤ 0.07, people 0.85).
  The committed runs used a paraphrase of the item that made the loss certain,
  which may account for some of this; see
  [LEARNINGS.md](LEARNINGS.md#method-flaws-found-in-an-audit-before-publishing).
- **Only Clef reproduces the conjunction fallacy unprompted**, at 0.87 against
  people's 0.85; Solar Decide Flash (0.70) and Clef Flash (0.62) come part of
  the way and every other model stays at 0.25 or below. Asked to answer as a
  person, all but Luna (0.50) reach 0.83 or more.
- **Clef and Clef Flash differ the way the Solar pair do.** Clef (listed on
  OpenRouter as built on Qwen3.8-27B) does not hedge: it shows about half the human framing effect under both prompts
  (27 and 23 points) where Flash shows none.

## Limitations specific to this comparison

1. **Two dates.** Jev and Sonnet were run on Sep 18 and everything else on
   Oct 12. Jev is pinned to a dated version, but the route and gateway may have
   changed in between.
2. **Microsoft-Decision-1, Clef and Clef Flash are not reproducible.**
   Microsoft-Decision-1's listing says its weights are updated continually
   while the API stays the same; the served name carries a date that does not
   change when they are. Clef and Clef Flash are served as `cloudflare/clef` and
   `cloudflare/clef-flash` with no date at all, so a later run may meet a
   different model under the same name.
3. **One summary number is not a ranking**, for the reason above. It is
   reported because it is what the existing analysis computes, not because it
   orders the models.
4. **Fourteen measures** is a small base for a correlation; an `r` of ±0.2 is
   indistinguishable from none.
5. Everything in the [main limitations](../README.md#limitations) applies.
