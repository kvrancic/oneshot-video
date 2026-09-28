# Choosing the moments

Clip choice is where every tool fails. Independent tests of Opus Clip throw away 13 to 40 percent of its output: cuts mid-sentence, missed punchlines, a joke with no setup, a moment that needs the previous five minutes. In the one controlled study (Rhapsody, 13k podcast episodes, ground truth from YouTube's "Most replayed" data) zero-shot GPT-4o found 26.5 percent of the real highlights. Reading carefully and gating hard beats asking a model for "viral moments".

## Genre first

Decide what the footage is before deciding what counts as evidence.

- **Content in the words** (lecture, talk, interview, podcast, commentary): the moment is what was said. Judge from the transcript; delivery matters second.
- **Reaction-driven** (panel, live stream, audience Q&A): laughter, interruptions and energy spikes point at the moment. Look at `[pause]` gaps and audience words in the transcript and at the frames.
- **Visual-driven** (demo, screen share, whiteboard): the transcript is thin; the moment is what appears. Look at stills (`assets.py frame`).

## The gate (before any score)

A candidate must hit at least one of these hard. Pleasant, well-spoken and on-topic is not a clip.

1. **An unexpected turn.** A reveal, a contradiction, a pattern nobody saw, the speaker undercutting their own claim.
2. **A strong claim or position** people would argue with or send to someone.
3. **New or useful information** a viewer would save: a number, a mechanism, a result, a broken misconception.
4. **A story with a turn**, told from setup to consequence.
5. **A line that survives being quoted alone.**

Fewer, harder clips. A weak clip costs the account more than a missing one.

## Head and tail (the part that separates this from every clipper)

- **The head is where a stranger can follow.** The first sentence must make sense cold. If it opens on a pronoun with no antecedent ("he", "this", "that one"), an answer to an unheard question, "so anyway", or "as I said", move the start back to where the idea begins, or add one context segment from earlier, or drop the clip.
- **Fix context by moving the start earlier, never by cutting the ending short.** A clip that loses its payoff to gain context has traded down.
- **The tail is after the payoff lands.** Include the beat after it: the laugh, the pause, the "and it kind of makes you think". End on a complete sentence. Never end on a comma, a "but", or a setup for the next thought.
- **Jokes are units.** Setup and punchline together, or neither. A clip where the room laughs but the punchline is missing is never acceptable.
- **Never quote-mine.** The clipped meaning must match what was meant. Stitching two passages is fine only when nothing between them reverses or qualifies the point ("but", "however", "except").
- **The first 3 seconds** must earn the next 3: a claim, a number, a named person, a question, a concrete image. If the strongest line is buried, use a cold open (below) or move the start.

## Cold opens

When the payoff sits after the midpoint, propose a cold open: play the payoff line (3 to 8 s) first, then cut to the setup and let the clip run; the line plays again in full at the end, now earned. Keep the pulled line short, cut it on a word boundary and mark the rejoin with a framing change (the alternating cut zoom does this). This is the strongest hook a talk has and no clipping tool does it automatically.

## Scoring and ranking

For each candidate, write one short sentence per axis instead of trusting a number:

| axis | question |
|---|---|
| hook | Would the first 3 seconds stop a stranger scrolling? |
| complete | Head starts a thought, tail finishes it, no missing context? |
| payoff | Is there a turn, a reveal, a punchline or a usable takeaway? |
| density | Does every sentence earn its place, or can it be tightened? |
| audience | Is this new or pointed for these viewers (for an AI-literate audience, basics are not news)? |

Then score 1 to 5 on each and **rank all candidates against each other**; absolute scores cluster and predict little (Opus's 64-point clip beat its 87-point clip in one test). Keep diversity: no two clips making the same point, telling the same story or landing the same joke.

## Length and format by content

| content | length | format |
|---|---|---|
| one sharp claim, a joke, a one-liner | 15 to 40 s | 9:16 (person is the content) |
| a claim with its argument, a short story | 40 to 90 s | 9:16 and 16:9 |
| a comparison, a list, a montage of people | 90 s to 3 min | both; stage layout |
| an explanation that needs the slides | 1 to 3 min | 16:9 first; 9:16 with stage layout |
| a full section | 5 to 25 min | 16:9, chapter cards |

Platform ceilings (2026): TikTok up to 10 min (Creator Rewards pay only on 60 s or more); Reels are recommended to non-followers only up to 3 min; YouTube Shorts up to 3 min; X free accounts 140 s (Premium much longer); LinkedIn up to 10 min, 30 to 90 s performs. Keep 9:16 clips under 3 minutes unless the user says otherwise.

## Directed requests

When the user names a moment ("the part where I compare the CEOs"), search the transcript for the names and terms, read two minutes either side and build that clip first. Offer a short cut (the sharpest 45 to 60 s) alongside the full passage when the passage runs past 2 minutes.

## Tightening inside a clip

- Cut restarts, false starts, stumbles, "um/uh" and "like" when it is filler; keep "like" when it is part of the rhythm and cutting it would leave a stub.
- Pauses over about 0.7 s are cut by default (`edl.py --max-pause`); keep the pause before a punchline or after a dry line (`"keepPauses": true` on that part). For this kind of speaker the pause is often the joke.
- A cut that changes a number, a negation or a qualifier is a meaning change. Do not make it.
- Every internal cut becomes a jump cut; the camera alternates its framing (1.00 / 1.12) at each cut so it reads as a second camera. Keep internal cuts to what the clip needs; 1 every 3 to 6 seconds is the ceiling for a talk.

## candidates.json

```json
[
  {
    "id": "c01",
    "title": "Seven AI leaders, one uncomfortable pattern",
    "edit": [{"words": [5764, 5782]}, {"words": [5072, 5098]}],
    "hook": "the uncomfortable pattern is that the optimist camps are the CEOs whose companies are valued at billions",
    "payoff": "the concern camp are researchers with no equity stake",
    "standalone": "names every person it discusses; the pattern line needs no earlier context",
    "format": ["9x16", "16x9"],
    "preset": "lecture",
    "graphics": "stance board: each leader lands on a speed-up / slow-down axis; reveal regroups by who holds equity",
    "scores": {"hook": 5, "complete": 5, "payoff": 5, "density": 4, "audience": 5},
    "flags": ["commentary on named public figures"]
  }
]
```

`candidates.py` resolves each `edit`, prints its exact first and last sentences and duration and flags weak openers, comma endings, dangling references, doubtful words and platform-length problems. Read its output before presenting anything.

## Presenting picks

AskUserQuestion, multiSelect, up to four options per question. Label: `Title (1:24)`. Description: the hook line in quotes and one clause on why it works. Put the recommended ones first and say so. If there are more than four strong picks, ask twice (top four, then the next four), or say "I'll also cut these three unless you say no".

## Optional: audience data

If the talk is already on YouTube, `ingest.py --youtube URL` pulls the "Most replayed" heatmap; peaks there are real viewer behaviour and a better prior than any rubric. Clip performance after posting can be logged in `DIR/performance.md` (views, retention, saves per clip) and read before the next selection.
