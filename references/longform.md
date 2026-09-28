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
