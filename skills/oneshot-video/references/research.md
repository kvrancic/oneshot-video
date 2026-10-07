# Research summary (September 2026)

Four deep reports sit in `docs/research/` (commercial apps and editing craft; about 60 open-source tools and Claude skills; the technical stack benchmarked on an M3 Pro; caption and motion design). This page is what they add up to.

## What the clipping apps do

| app | distinctive | where it fails |
|---|---|---|
| Opus Clip | ClipAnything (prompted selection), ReframeAnything, virality score, AI B-roll, auto hook card, brand templates, caption presets (Karaoke, Beasty, Mozi, Deep Diver, Pod P, Glitch Infinite ...), XML export to Premiere/DaVinci, an MCP server and a Claude connector since 2026-09-11 | testers discard 13 to 40 percent of clips: cuts mid-thought, missing context, a joke without its setup, off-topic tangents rated high; score weakly predictive (a 64 beat an 87); B-roll wrong 4 times in 11; only 6 percent of its 13.5M exports use B-roll |
| Submagic | 42 caption templates (Hormozi 1 to 5, Beast, Iman, Ali, Devin ...), magic zooms, magic B-roll, auto transitions and SFX, hook titles, progress bar | the preset look now reads as "clip farm"; effects applied by timer, not by meaning |
| Captions.app | AI Edit styles (Prism, Bloom ...), eye contact, AI Shorts, Clips Chat | full-edit styles, little control over choice of moment |
| Vizard, Klap, Munch, Reap, Choppity, quso, Spikes, 2short, Eklipse | variants of the same pipeline; Reap is agent-first (MCP, CLI, clips from non-adjacent parts) | multi-speaker framing breaks on crosstalk; slides get cropped; captions drift |
| Descript, Riverside, CapCut, VEED | editors with clip features (Underlord, Magic Clips, auto reframe) | good editors, weak at finding moments in a long lecture |

What professional editors do that the tools do not: pick the moment by reading it; cold open on the payoff; keep the pause that carries the joke; change framing at every jump cut; sparse, meaningful graphics; dry audio for talks; 3 to 6 s visual cadence (DOAC measured a cut every 4 to 6 s, 2.5 to 3 s near the payoff); no emojis, no loud presets for serious speakers.

## Effects that matter (and how oneshot-video produces them)

| effect | how |
|---|---|
| subject-following reframe | YuNet faces at 6 to 8 fps, track linking that ignores faces on slides, a virtual operator with holds, eased moves and follow sections; cropped from the 4K original |
| persistent punch-ins, pushes | per-frame crop size from the original (sharp), alternating cut zoom at every jump cut, planned punches and pushes on the lines that matter |
| animated captions | nine presets in Remotion, word-timed, laid out in advance (no jitter), re-timed on the finished voice track |
| motion graphics | React components driven by word references: stance board with reveal, takeover, quote card, name tag, hook card, chips, footnote, chapter and end cards |
| stage layout | 9:16 visual panel over the speaker, 16:9 panel beside a second virtual camera; graphics never cover a face |
| slides | the speaker's own deck pages, crisp, highlighted as read |
| B-roll | Pexels (licence recorded), Wikimedia Commons portraits (licence recorded), frames from the talk |
| sound design | synthesized kit (whoosh, tick, pop, thud, riser, paper, marker), placed on graphic events, -20 to -26 dB |
| music | optional, 18 to 25 dB under the voice, ducked from the transcript |
| mix | speech chain, limiter, two-pass loudnorm to -14 LUFS / -1 dBTP in linear mode |
| grain | seeded film grain over the whole composite |

## Stack decisions

| stage | choice | why |
|---|---|---|
| words | Whisper large-v3-turbo (whisper.cpp, Metal) with a context prompt | right names in a reverberant hall; 16x realtime |
| timing | Parakeet TDT 0.6B v3 (ONNX, CPU), merged by sequence alignment, gaps re-aligned, captions re-timed on the final voice | Whisper's word times run 100 to 300 ms late; Parakeet's onsets are within about 50 ms |
| faces | YuNet (OpenCV, 230 KB) | finds a 110 px face in a 4K lecture frame in about 40 ms; MediaPipe crashes on macOS arm64 and misses small faces |
| camera path | greedy holds with lookahead eases, smoothed follow for walking | same effect as L1-optimal paths (most frames perfectly still), no solver |
| render | Remotion 4 (React), hardware H.264, muted; mix in ffmpeg | best-looking type and motion; deterministic; about 4.4 minutes for a 2:45 9:16 clip |
| selection | Claude reading the whole transcript, word indices only, gates in code, relative ranking | the only approach that holds heads and tails; zero-shot "find viral moments" found 26.5 percent of real highlights in the Rhapsody study |

Rejected: MoviePy (slow, ugly text), ffmpeg + libass for finals (Homebrew's ffmpeg 9 dropped libass; ASS cannot do springs or layout), MediaPipe (crash, small faces), ultralytics YOLO (AGPL; not needed on 4K close cameras), ElevenLabs and other paid APIs (the user wants local; Scribe v2 would be the paid upgrade for timing).

## Where oneshot-video goes beyond the tools

1. Clips chosen by reading the whole talk against a gate, with every head and tail printed as text before anything renders.
2. Cold opens built in.
3. Word references instead of timestamps, so edits cannot drift; two ASR models checking each other; captions re-timed on the audio that ships.
4. The camera crops the 4K original, punch-ins included and knows the future (moves start before the subject leaves the frame).
5. Multi-camera ingest: the closest 4K camera becomes the picture, others are synced by audio.
6. Stage layout and the speaker's own slides instead of cropped projections.
7. Graphics built from what was said, with a reveal, not stock templates.
8. QA in code (loudness, black and frozen frames, dead air, captions vs face) plus a fresh-eyes critic before render.
9. Clean exports per format with covers, SRT, credits and post copy and a review page.

## Known limits

- Faces under about 40 px (a back-of-hall 1080p shot) are not found; use the close camera or a 4K original.
- Two people in one frame need one tracking run per person (`--hint`); automatic active-speaker detection is not built.
- Text behind the speaker needs a person matte (Apple Vision can make one at about 10 ms per frame); planned.
- Music generation is not local; beds come from the user's library or the platform at posting time.
