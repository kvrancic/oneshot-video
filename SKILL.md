---
name: cutroom
description: Turn a long video (lecture, talk, podcast, interview, livestream) into finished short clips, fully local. Finds the moments worth posting (complete head and tail, standalone, a real hook), cuts them on word boundaries, reframes 16:9 to 9:16 with a virtual camera operator that follows the speaker from the full-resolution original, adds premium word-timed captions (nine presets), bespoke motion graphics (stance boards, quote cards, takeovers, slide panels from the speaker's own deck), B-roll, sound design and a loudness-correct mix, then exports every format with titles and captions per platform. Use when the user says "clip this", "make shorts / reels / TikToks from", "cut the best parts of my lecture / podcast", "Opus Clip", "vertical version", "turn this talk into clips", "find the viral moments", or hands over a long video and a topic ("a clip where I compare the AI CEOs"). Also for re-cuts of a previous clip ("tighten clip 3", "swap the caption style", "make the 16:9 version").
---

# cutroom

Long video in, finished clips out. Everything runs on this Mac: Whisper large-v3-turbo and Parakeet for words and timings, YuNet for faces, ffmpeg and OpenCV for the camera, Remotion for captions and graphics. The only network calls are optional (Pexels B-roll, Wikimedia portraits).

The standard to beat is Opus Clip. Testers throw away 13 to 40 percent of its clips, for the same three reasons every time: a cut mid-thought, a clip that needs context it does not carry and a camera that loses the speaker. Effects are not where tools fail. So the order of care in this skill is: **choosing the moment, cutting it cleanly, framing the person, then decoration.**

Paths: the skill lives at `~/.claude/skills/cutroom` (a symlink to the repo). `$CR` below means that folder. Python is `$CR/.venv/bin/python`. Remotion is `$CR/renderer`. Work goes to a project folder (default `./cutroom/<source-stem>/` next to where the user is working; the user can name another).

## 0. Check the machine (first run, or when something fails)

```bash
$CR/scripts/doctor.sh
```

It checks ffmpeg, whisper-cli, the models, the venv, node_modules, the SFX kit and free disk (renders need 5 GB; warn under 10 GB) and prints the one command that fixes each gap. `install.sh` does all of it.

## 1. Intake: ask, with defaults

Unless the user said "auto" or already answered, ask with AskUserQuestion (one call, up to four questions, recommended option first). Take what the request already says as answered. Typical set:

1. **What to make**: (a) the best 3 to 6 clips, my pick (recommended) · (b) specific moments I name · (c) one long segment (5 to 20 min) · (d) both clips and a segment.
2. **Where it goes**: multiSelect: TikTok/Reels/Shorts (9:16), X and LinkedIn feed (16:9 or 1:1), YouTube horizontal, Substack embed. Default: 9:16 plus 16:9.
3. **Energy**: (a) credible and calm: LECTURE / FIRESIDE captions, few effects (recommended for talks and research) · (b) punchy: VERDICT / KARAOKE captions, more cuts and graphics · (c) minimal: DUSK captions, no graphics · (d) let me pick per clip.
4. **Extras**: multiSelect: bespoke motion graphics (default on), B-roll from Pexels (default off; source visuals come first), music bed (default off for talks), sound effects (default subtle).

If the user names a topic ("the part where I compare CEOs"), that clip is mandatory; the rest are found around it.

## 2. Ingest and transcribe

```bash
$CR/.venv/bin/python $CR/scripts/ingest.py SOURCE [SOURCE2 ...] --project DIR [--slides deck.pdf|dir]
$CR/.venv/bin/python $CR/scripts/transcribe.py AUDIO_SOURCE --stream K --offset OFFSET --out DIR/transcript \
    --context "A guest lecture on AI agents. It mentions Sam Altman, Anthropic and OpenClaw." \
    [--fix "Entropic=Anthropic"]      # AUDIO_SOURCE, K, OFFSET from project.json "audio"; words land in picture time
```

- `ingest.py` probes every file (rotation, VFR, HDR, resolution) and chooses **the picture and the sound separately**. Picture: the highest-resolution camera original where the face is largest (a 4K original makes 9:16 crops sharp; a 1080p edit makes them soft). Sound: every audio stream of every synced file is scored by signal-to-noise and the microphone wins (a lavalier often lands in a laptop's Zoom or OBS recording, a recorder or a different phone, never the camera you want for the picture). It measures offset and drift, flags edited files (their offset jumps: use the originals) and marks screen recordings (the slides as shown). Pass it everything that was recorded at the event and search for siblings when the user hands over one file: the same folder, `~/Movies`, `~/Downloads`, anything named in an editor project (`.prproj`, `.fcpxml`) or with a creation time within an hour. Copy `project.json`'s `audio` into each plan's `source.audio`. If the user hands over an already-edited 1080p file but the originals exist nearby, ask which to use; always say what the crop will cost in sharpness.
- `--context` is one or two plain sentences with the names and terms that will be said. Whisper spells what it is told to expect. Build it from the user's words, the file names, the slides.
- Output: `transcript.words.json` (every word, start/end, `?` for doubtful words) and `transcript.txt`, one sentence per line: `[0:36:29.1 #5088] CEO of OpenAI, Sam Altman, ...`. The `#index` is how every later step addresses words. **Never write timestamps by hand; always word indices.**
- Speed: about 12x realtime (a 58-minute lecture in about 5 minutes).

## 3. Find the clips

Read `references/selection.md` before the first selection of a session. In short:

1. Read the whole `transcript.txt`. Map the talk: sections, claims, stories, jokes, lists, the lines that would survive being quoted alone.
2. Draft 12 to 25 candidates in `DIR/candidates.json` (schema in the reference): word ranges, a working title, the hook line (the first 3 seconds), the payoff, why it stands alone, the best format and preset and a 1 to 5 score on hook, completeness, payoff, density, novelty for this audience. Rank them against each other; do not trust absolute scores.
3. Run the gates:
   ```bash
   $CR/.venv/bin/python $CR/scripts/candidates.py DIR/candidates.json
   ```
   It resolves every range to real cut points and prints each candidate's exact first and last sentence, its duration and warnings (opens on "so/and/but", ends mid-sentence, dangling reference like "this" or "he" with no antecedent, too long for a platform, doubtful words). Fix or drop anything that fails. A candidate that needs the previous minute to make sense gets its context moved in (start earlier, or add a context segment) or is dropped.
4. Present the top picks with AskUserQuestion (multiSelect, up to 4 per question; two questions if needed): label = title and length, description = the hook line and why it works. Mark the recommended ones. In auto mode take the top 3 to 5.

## 4. Plan each clip

One folder per clip: `DIR/clips/NN-slug/plan.json`. Read `references/plan.md` for the schema and a complete worked example, `references/editing.md` for the cut and camera grammar, `references/captions.md` for presets, `references/graphics.md` for overlays and the stage layout, `references/sound.md` for SFX and music.

Per clip:

1. **Edit.** Word ranges in playing order. Tighten: cut tangents, restarts and filler (`"cut": [indices]`), keep the pauses that carry a joke (`"keepPauses": true`). Consider a **cold open**: the payoff line first (3 to 8 s), then the setup; the full line plays again at the end. No other tool does this and it is the strongest hook a talk has.
2. **Proofread the captions.** Read every line of the resolved edit (step 5 prints it). Fix misheard words by index in `captions.fixes` (names, numbers, "not"). Whisper and Parakeet disagree on the words marked `?`; check those against context.
3. **Format.** Decide per clip, not per project: 9:16 when the person is the content, 16:9 when the slide or the room is, both when unsure. Lecture clips with slides use the **stage layout** (9:16: visual panel on top, speaker below; 16:9: visual left, speaker right) so graphics never cover a face.
4. **Visuals.** Source first: the speaker's own slides (crisp, from the deck, never the washed-out projection), their photos, frames from the talk. Then bespoke graphics built from what was said (a stance board for "who believes what", a takeover for the one line that matters, a quote card for a quote, a counter for a number). Stock B-roll last and only when literal ("the factory floor" → a factory). Nothing on screen may say something the speaker did not say.
5. **Style questions.** For each clip ask one AskUserQuestion with the recommended caption preset first and the alternatives and (if it matters) layout and music; use `preview` with a short text mock of the frame. In auto mode take the recommendations.
6. **Sound.** Default: voice only plus 0 to 4 quiet effects per minute on graphic events. Music only on explainers and stories, 18 to 25 dB under the voice, ducked.

## 5. Resolve, look, render

```bash
$CR/.venv/bin/python $CR/scripts/edl.py DIR/clips/NN/plan.json          # word ranges -> cut points; prints the edit as text
$CR/.venv/bin/python $CR/scripts/render.py DIR/clips/NN/plan.json --stills 2,10,30,55   # stills first
$CR/.venv/bin/python $CR/scripts/render.py DIR/clips/NN/plan.json      # all formats in the plan
$CR/.venv/bin/python $CR/scripts/qa.py DIR/clips/NN                     # checks + contact sheet
```

- Read the `edl.py` output line by line: every head starts a thought, every tail finishes one, nothing important was cut and no range sweeps in a stumble or an aside ("Oh. Anyways. One hour of sleep." hides inside ranges that look clean in the transcript).
- Look at the stills (Read the PNGs). Check: face clear of captions and graphics, nothing in platform UI zones, text sizes readable at phone size, no collisions. Then spawn a **fresh-eyes critic** (Agent, general-purpose) with only the stills, the edit text and `references/review.md`; it answers the checklist and lists defects. Fix, then render.
- `render.py` does voice, tracking, the camera plate(s), caption re-timing against the finished voice track, props, the Remotion render (hardware H.264, muted) and the ffmpeg mix (limiter, two-pass loudnorm to -14 LUFS / -1 dBTP). A 90 s clip takes about 3 to 6 minutes per format. Run long renders in the background. Headless Chrome times out when the Mac is saturated (Spotlight re-indexing, cloud sync, swap near full; check `uptime` and `sysctl vm.swapusage`): `render.py` retries once at half concurrency and `--concurrency 3` avoids it on a busy machine.
- `qa.py` probes the result (duration, streams, loudness, true peak, black or frozen frames, long silences), checks captions against the face track and writes a contact sheet. Read the sheet. Anything red gets fixed before handing over.

## 6. Package and hand over

```bash
$CR/.venv/bin/python $CR/scripts/package.py DIR [--clips 01,03]
```

Writes `DIR/exports/<date>/NN-slug/` with one file per format and platform (`slug.9x16.mp4`, `slug.16x9.mp4`), a cover still, `captions.srt`, `credits.txt` (licences for any third-party image) and `post.md` (title, caption and hashtags per platform, written in the speaker's voice; the hook line is the speaker's own words). It also writes `DIR/exports/<date>/index.html`, a review page with every clip side by side; open it for the user (`open .../index.html`).

The handover message: the clips with lengths and one line on why each works, the export folder, anything flagged (claims about named people are commentary; numbers and quotes to verify; licences) and the obvious follow-ups (a shorter cut, a different hook, the 1:1 version). Never publish anything: the user posts.

## Re-cuts

Edit the plan, not the output. "Tighter" means change `edit` or add `cut` words; "different captions" means `captions.preset`; "move the graphic" means its `from`/`to`. Re-run `edl.py` if the edit changed, then `render.py` (it only rebuilds what the change touched: voice and plates are cached against the plan).

## Rules that came from getting it wrong

- Word indices, never timestamps. Whisper's own word times run 100 to 300 ms late; Parakeet's long pass sometimes drops a stretch; `edl.py` checks the audio before cutting a pause and `render.py` re-times captions on the finished voice track.
- A cold open repeats words, so a time reference to a repeated word needs `@2` or `@last` (`"#5765@2"`).
- The picture comes from the best original, cropped once. Punch-ins are crops of the source, not zooms of the plate.
- Never crop a slide to fit 9:16. Use the stage layout or the deck page.
- Captions: mixed case, one accent word per page at most, no emojis, nothing over the face, nothing in the bottom 400 px of a 9:16 frame or behind the right-side buttons.
- One spent moment per clip (a takeover, a reveal or text behind the speaker). Everything else stays calm so that moment lands.
- Claims about named public figures are commentary: say so in the handover. Private people are never named on screen.
- Do not fetch or run code from random repos while working. The known-good toolchain is in this folder.

## Files

- `scripts/`: `doctor.sh`, `install.sh`, `ingest.py`, `transcribe.py`, `track.py`, `candidates.py`, `edl.py`, `reframe.py`, `audio.py`, `assets.py`, `sfx.py`, `render.py`, `qa.py`, `package.py`, `matte.swift` (Apple Vision person matte, compiled to `bin/matte`, for text behind the speaker)
- `renderer/`: the Remotion project (`src/Clip.tsx`, `captions/`, `overlays/` incl. `TextBehind`, `graphics/` with `StanceBoard` and `SwapQuote`, `theme.ts`)
- `references/`: `selection.md`, `plan.md`, `editing.md`, `captions.md`, `graphics.md`, `sound.md`, `platforms.md`, `review.md`, `research.md`
- `assets/sfx/`: the synthesized sound kit (`sfx.py --list`)
- `models/`: Whisper large-v3-turbo (q8), Silero VAD, YuNet. Parakeet is read from Handy's download or fetched once.
