# Long-form edits (cutroom-edit)

## structure.json (the story pass)

```jsonc
{
  "talkStart": 231, "talkEnd": 14980,                  // word indices
  "chapters": [{"title": "Part I · What is AI?", "at": 402}],
  "proposedCuts": [{"id": "x01", "from": 5210, "to": 7400, "what": "Live demos", "why": "tools date quickly; two demos failed",
                    "minutes": 11.5, "recommend": true, "note": "Live demos removed for copyright reasons"}],
  "stumbles": [[812, 814]],                            // restarts inside kept material
  "teaser": [{"from": 9120, "to": 9141, "line": "..."}],
  "broll": [{"kind": "Timeline", "from": 1020, "to": 1188, "idea": "AI winters", "props": { }}],
  "fixes": {"145": "the author"},
  "estimatedMinutes": 64
}
```

## B-roll graphics (full frame, `visual` layout inside an insert)

Beats are word references; the renderer turns them into times on the insert's clock.

| graphic | props |
|---|---|
| `BigNumber` | `value, decimals?, prefix?, suffix?, label, at, title?, sub?, subAt?` |
| `Timeline` | `title?, points: [{year, label, at, level 0..1, winter?}]` (a hype curve that draws itself; winters dip) |
| `Tokens` | `title?, word, pieces[], ids[], at, idsAt?, note?` |
| `NextToken` | `title?, prompt, options: [{word, p}], at, pickAt?, temps?: [{t, at}]` (temperature reshapes the bars) |
| `Steps` | `title?, steps: [{label, sub?, at}]` |

Keep each graphic on screen 6 to 20 s, while the speaker explains exactly that; cut back to the speaker for the punchline.

## Inserts

`edit.json` `inserts`: `{kind, from, to, overlays: [...], layout: [...]}` with word references. `title` (TextBehind + NameTag over the first shot), `chapter` (ChapterCard), `note` (KeywordChip where a section was removed), `broll` (a full-frame graphic). Each is rendered by Remotion over its slice of the picture and laid over the timeline; the voice keeps running underneath.

## Timing

A 100 minute talk: transcription about 10 min, tracking 15 to 25 min, story pass by an agent about 15 min, shots about 1 to 2x realtime of the final length with four parallel hardware encodes, inserts a few minutes, final pass (subtitles, sound) about 10 min.

## Plan keys for awkward rooms (added for the a conference edit)

| key | what it does |
|---|---|
| `edit[].tail` | seconds the part rings out after its last word (applause, a laugh), past the 0.6 s cap |
| `fixedCrops` | `{"close.stage": [x, y, w, h]}` on the source: a framing chosen by eye for a static camera |
| `framing` | zoom per angle (`{"close.medium": 2.8}`) when face-sized crops do not fit (a far camera) |
| `clips` | `[{src, from, to, captionsOff?}]` pre-rendered video laid straight over the picture by ffmpeg, before the subtitles; a `.mov` with alpha (png or prores 4444) keys itself. For pixel art and custom title sequences that Remotion would soften |
| `captionsOff` | on an insert or a clip: no subtitles under it (a title card that already shows the words) |
| `sfx` | `[{at, file, gain}]` in full edits too: kit names (`whoosh-soft`) or paths, at word references |
| `bed` | `{file, at, gainDb}` a pre-composed music bed, or a list of them (not looped, not ducked: it carries its own dynamics) |
| `screenHold` | seconds the deck stays up after a slide change before the speaker cycle may return (default 6) |
| `captions.top` | `[[from, to], ...]` subtitles at the top of the frame over slides with text along the bottom |
| `captions.oneLine` | `[[from, to], ...]` one-line subtitles where a slide has text both top and bottom |
| `audio.chain` | an ffmpeg filter chain for the voice instead of the measured light/strong/rnn choice |
| `angles` with `#i@last` | an angle for one copy of a line the cold open plays twice (the body's copy) |
| `holds` across a cut | a hold on the last word kept before cut words gives the word after the cut that much lead-in, so a removed "Good job." leaves its pause |
| `edit[].outAt` / `inAt` | `"#i+0.145"`: end or start a part inside a word, for a repeat said in one breath; splice at the closure of the same stop consonant in both copies ("chat\|bot"), read at 5 ms first |

Check every join that removes words by reading the render back (whisper on 5 s around it): a clipped word
drops out of the transcript ("chatbot, and 0.3%" read back as "chatbot, 0.3%" was a clipped "and").
A keyword plate on a slide (top or bottom) decides which side the subtitles take: `capcheck.py`-style,
test the subtitle box against the plate on the slide under each subtitle and use the free side.

One camera only: wherever the director wants the room (audience, speaker out of frame) it takes the picture
camera's whole frame. An angle asked for in `angles` is never merged away for being shorter than 2.5 s.

A far camera with a small face: the face tracker may lock onto someone in the audience (a still, well-lit face
wins). Check `track-close.json` against a frame before directing; a lone speaker on a stage tracks better by
background difference (median frame of the stage band, the moving figure is the blob).

## Breaths

`breaths.py SOURCE --words DIR/transcript.words.json --out DIR/voice-debreath.wav --report DIR/breaths.json`
lowers every gap between words by 14 dB (from 120 ms after a word to 40 ms before the next), which takes
inhales, lip noise and PA hiss out while words keep their room. Gaps that hold their own sound (laughter,
an answer, applause) are left alone and listed as reactions. Point `project.json` `audio.path` at the result.
