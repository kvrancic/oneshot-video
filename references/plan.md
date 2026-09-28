# plan.json

One file per clip, `DIR/clips/NN-slug/plan.json`. Claude writes it; `edl.py` adds `segments`; `render.py` does the rest. Everything that can change is in here, so a re-cut is an edit to this file.

## Time references

Anything that happens at a moment (`from`, `to`, `at`, `until`, zoom `t`) takes a reference instead of a number whenever it is tied to speech:

| form | meaning |
|---|---|
| `"#5096"` | start of word 5096 |
| `"#5096.e"` | end of word 5096 |
| `"#5096+0.3"`, `"#5096-0.2"` | with an offset in seconds |
| `"#5096@2"`, `"#5096@last"` | the second / last time that word plays (a cold open repeats material) |
| `12.5` | 12.5 s of the finished clip (edit time) |
| `"end"`, `"end-2"` | the clip's end, minus seconds |

A reference to a word that was cut is an error, not a silent drift.

## Schema

```jsonc
{
  "id": "01-leaders",                       // folder name; output files use it
  "title": "Seven AI leaders, one uncomfortable pattern",
  "source": {
    "video": "/abs/path/CAMERA_A.MOV",       // the picture: the best camera original
    "audio": {"path": "/abs/zoom-recording.mp4", "stream": 0,     // the microphone (from project.json)
              "offset": -76.28, "drift": -1.4e-5, "ref": 1746.9},  // audio time = picture time + offset + drift * (t - ref)
    "words": "work/talk/close.words.json"  // transcript the indices refer to
  },
  "formats": ["9x16", "16x9"],               // 9x16, 16x9, 1x1, 4x5
  "palette": "paper",                        // paper | slate | editorial | nightlab | mono

  // ---- the edit (word ranges in playing order)
  "edit": [
    {"words": [5764, 5782], "note": "cold open"},
    {"words": [5072, 5098]},
    {"words": [5275, 5321], "keepPauses": true},   // keep the pause before a punchline
    {"words": [5520, 5544], "maxPause": 1.2}
  ],
  "cut": [5773, 5781],                       // words removed from the audio (filler, a stumble)
  "segments": [ ... ],                       // written by edl.py: [{a, b, w: [first, last]}]

  // ---- captions
  "captions": {
    "preset": "lecture",                     // see captions.md
    "fixes": {"5241": "Amodei.", "5199": "self-driving", "5200": ""},  // index -> text ("" hides it)
    "drop": [5452],                          // hidden from captions only (audio keeps it)
    "emph": {"5096": "accent", "5311": "serif"},   // at most one per caption page
    "breaks": [5140],                        // force a page break after this word
    "speakers": {"6012": "B", "6040": "A"},  // LEDGER: speaker changes at these words
    "zones": {"9x16": [{"from": "#5301", "to": "#5313.e", "hide": true}]},  // hide / move (y) / dim
    "off": false
  },

  // ---- camera (all optional)
  "camera": {
    "faceFrac": 0.17,                        // face width / crop width (9:16 medium shot ~0.17)
    "eyeLine": 0.36,                         // eyes at this fraction from the top
    "deadZone": 0.18,                        // half-width of the hold zone, fraction of crop width
    "cutZoom": [1.0, 1.12],                  // framing alternates per segment; [] turns it off
    "hint": "1250,620",                      // follow the face nearest this source pixel (multi-person)
    "zooms": [
      {"t": "#5135", "z": 1.12, "kind": "punch"},                  // instant, until the next cut
      {"t": "#5762@2", "z": 1.08, "kind": "push", "dur": 4},       // eased push-in
      {"t": "#5400", "until": "#5420", "z": 1.1, "kind": "push", "release": "ease"}
    ]
  },

  // ---- layout per format: spans in time
  "layout": {
    "9x16": {"spans": [
      {"from": 0, "to": "#5072", "mode": "speaker"},
      {"from": "#5072", "to": "#5801", "mode": "stage", "visual": {"kind": "graphic", "graphic": "StanceBoard", "props": { }}},
      {"from": "#5801", "to": "end", "mode": "speaker"}
    ]},
    "16x9": {"spans": [ ]}
  },

  // ---- overlays
  "hook": {"text": "Seven AI leaders.\nOne uncomfortable pattern.", "to": "#5072", "treatment": "paper"},
  "overlays": [
    {"type": "NameTag", "from": 2.3, "to": "#5072-0.3", "props": {"name": "Alex Rivera", "role": "guest lecture"}},
    {"type": "Takeover", "from": "#5301-0.2", "to": "#5313.e+0.3", "props": {"words": [{"text": "Imagine", "at": "#5301"}], "size": {"v": 104, "h": 96}}},
    {"type": "QuoteCard", "from": "#6100", "to": "#6130.e", "props": {"lines": ["..."], "who": "Charles Baudelaire, 1859"}, "formats": ["9x16"]}
  ],
  "end": {"text": "From a guest lecture", "handle": "@yourhandle", "from": "end-2"},
  "progress": false,
  "grain": 0.06,

  // ---- sound
  "audio": {"clean": "auto"},                // auto (by measured SNR) | light | strong | rnn | off
  "sfx": [{"at": "#5091", "file": "tick", "gain": -24}],
  "music": {"file": "music/bed.mp3", "gainDb": -22, "duckDb": 8},

  // ---- packaging
  "cover": 1.0,                              // edit seconds of the cover still
  "post": {"x": "...", "linkedin": "...", "tiktok": "...", "shorts_title": "...", "youtube_title": "..."},
  "flags": ["commentary on named public figures"],
  "overrides": {"16x9": {"captions": {"preset": "lecture"}}}   // per-format differences
}
```

## Layout modes

- `speaker`: the camera plate fills the frame.
- `stage`: a visual shares the frame with the speaker. 9:16: panel on top (`panelH` default 820 for graphics, 608 for 16:9 images and slides), speaker below with the face placed at 30 percent of the remaining height; captions move to the bottom band. 16:9: panel left (1000x900) and `render.py` renders a second camera, a speaker-only shot for the right third (820x1080) from the original.
- `visual`: the visual fills the frame; the voice continues (B-roll, a full-screen slide, a takeover of the frame).

Visuals: `{"kind": "graphic", "graphic": "StanceBoard", "props": {...}}`, `{"kind": "slide", "src": "assets/slide-57.png", "highlight": {"x": .1, "y": .6, "w": .5, "h": .08, "at": "#5137"}}`, `{"kind": "image", "src": ..., "kenburns": {"from": [1.02, 50, 50], "to": [1.1, 50, 45]}}`, `{"kind": "video", "src": ..., "trimBefore": 2.0}`.

Adjacent spans with the same mode continue without a transition; a mode change animates in 14 frames and out in 12.

## Overlay types

`HookBar`, `NameTag`, `KeywordChip`, `QuoteCard`, `Takeover`, `Footnote`, `ChapterCard` (props in `graphics.md`); every overlay may carry `"formats": [...]` to appear only in some formats. Graphics used as a stage or visual: `StanceBoard`.

## Worked example

`examples/01-leaders.plan.json` is the full plan of a 2:45 clip from an MIT lecture: cold open on the payoff, seven people introduced on a stance board with a reveal, one takeover line, quiet ticks as chips land, a loop ending. Read it once before writing a plan with graphics.
