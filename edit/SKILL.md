---
name: cutroom-edit
description: Edit a whole recorded talk (lecture, keynote, workshop, panel) into a finished long video, fully local. Syncs every camera, the microphone and the screen recording; cuts fillers, restarts and dead air on word boundaries; proposes section cuts (demos, chatter, weak or failed parts) for approval and marks removed parts on screen; directs a multicam edit that always shows the best angle (speaker, room and audience, the screen, 4K punch-ins); switches to the room mic when the audience speaks; grades the cameras to match; adds an opening title behind the speaker, chapter titles, motion-graphics B-roll and burned-in subtitles; exports YouTube chapters and an .srt. Use when the user says "edit my lecture / talk / keynote", "cut this recording", "multicam edit", "sync my cameras and mic", "make the full video", "remove the filler words", "cut the demo part". For short clips from a talk use the cutroom skill instead.
---

# cutroom-edit

The full-edit sibling of `cutroom`. Same engine (`$CR` = `~/.claude/skills/cutroom`, the repo; Python `$CR/.venv/bin/python`); a different job: **subtract and direct** rather than select. The result should feel like a produced talk: nothing boring left in, always the best angle, clean sound, readable subtitles, a title sequence people remember.

Work folder: `DIR` = `$CR/work/<talk-key>/` unless the user names another.

## 1. Intake (AskUserQuestion, recommended first; skip what the request answers)

- Tightness: tight (sections that do not carry the argument go; typically 60 to 70 percent of the recording) · light (fillers and dead air only) · best-of (35 to 45 min).
- Section cuts: propose and ask (recommended) · cut on my judgement and list them · none.
- Subtitles: sentence subtitles burned in (recommended) · word-highlight rail · .srt only.
- Extras: opening title behind the speaker, chapter titles, motion-graphics B-roll, a teaser cold open (all recommended on).

## 2. Ingest, sync, transcribe, signals

```bash
$CR/.venv/bin/python $CR/scripts/ingest.py CAM1 CAM2 SCREEN.mp4 [RECORDER.wav] --project DIR
$CR/.venv/bin/python $CR/scripts/transcribe.py <project.json audio path> --stream K --offset OFFSET --out DIR/transcript --context "..."
$CR/.venv/bin/python $CR/scripts/signals.py DIR/project.json --out DIR/signals.json
$CR/.venv/bin/python $CR/scripts/track.py <picture> --from A --to B --fps 3 --out DIR/track-close.json
```

- Pass every file recorded at the event and look for siblings (same folder, `~/Movies`, editor projects). `ingest.py` picks the picture (largest face in the highest resolution), the microphone (best signal-to-noise of every audio stream), marks the screen recording and flags edited files.
- Transcribe from the microphone (91 percent model agreement on a lavalier against 84 on a room phone). `--context` names the talk, people and terms (read them off the deck).
- `signals.py` finds who speaks when (the speaker's lavalier against the room: audience questions come out as audience turns) and what the screen does (slide changes, busy demo stretches).
- Tracking over a 100 minute talk at 3 fps takes about 15 to 25 minutes; start it early in the background.

## 3. The story pass

Read the whole transcript (or hand it to an agent with this brief) and write `DIR/structure.json` (schema in `longplan.py`'s docstring and `references/longform.md`): `talkStart`, `talkEnd`, `chapters` (from the deck), `proposedCuts` (id, word range, what, why, minutes, recommend, optional on-screen note), `stumbles` (small ranges of restarts to cut), `teaser` (3 or 4 standalone lines for a cold open), `broll` (places where an animated graphic explains better than the camera, with word anchors), `fixes`.

Then **ask**: one AskUserQuestion, multiSelect, one option per recommended section cut (label "Cut: <what> (3.2 min)", description: the reason). Up to four per question; ask twice if needed. Say the expected final length. Cuts the user does not tick stay in. A removed demo or a removed section with a reason gets a short on-screen note at the cut ("Live demos removed for copyright reasons").

## 4. Plan, direct, grade

```bash
$CR/.venv/bin/python $CR/scripts/longplan.py DIR --approve x01,x03 --teaser --title "THE AI LECTURE" --subtitle "Theory · Practice · Philosophy" --byline "Alex Rivera · Conference"
$CR/.venv/bin/python $CR/scripts/edl.py DIR/edit.json          # word ranges -> cuts; fillers and pauses out
$CR/.venv/bin/python $CR/scripts/multicam.py DIR/edit.json     # the shot list
$CR/.venv/bin/python $CR/scripts/grade.py DIR/edit.json --preview   # look at DIR/grade/*.jpg
```

- Fill each B-roll entry's `props` in `edit.json` (graphics: `BigNumber`, `Timeline`, `Tokens`, `NextToken`, `Steps`; props in `references/longform.md`) with beats as word references (`"#5120"`), so every element lands on the word that names it. Only facts the speaker says or the deck shows.
- The director: audience speaking → the room camera; a slide appears → the screen recording for a sentence or two; otherwise speaker angles cycle (medium, wide, tight, room) every 6 to 14 s on sentence ends; cuts inside a shot alternate medium and a 1.12x punch so filler cuts read as camera changes. Override any range with `"angles": [{"from": "#i", "to": "#j", "angle": "screen"}]`.
- Grade: white balance on neutral surfaces per camera, then one look (`natural`, `warm`, `punchy`). Read the before/after stills.

## 5. Preview, then render

```bash
$CR/.venv/bin/python $CR/scripts/longrender.py DIR/edit.json --preview 0-150    # the opening: teaser, title, first chapter
$CR/.venv/bin/python $CR/scripts/longrender.py DIR/edit.json                    # the whole talk (background; 30 to 60 min)
```

Look at the preview (contact sheet via `qa.py`-style frame grabs, or open it) before the full render. The full render reuses shots and sound from the preview. Output in `DIR/out/`: `<id>-full.mp4`, `<id>.srt`, `chapters.txt` (paste into the YouTube description), plus the cut list from `structure.md`.

## Rules

- **Smooth beats complete.** Only cut where the join plays naturally. `"minRun": 1.2` makes the resolver rejoin any piece under 1.2 s that was split off only by a pause or a filler (a lone "But" then a cut sounds broken; "But" and a breath sounds human). After `edl.py`, list pieces under 1 s (`awk 'NR>1 && $4<1.0' DIR/edit.txt`) and fix each: drop an orphaned connective together with the stumble next to it, or restore a tiny self-correction ("kind of the, why") rather than jumping over it.

- Never cut a qualifier, a number or a negation to save time; never leave a dangling reference to removed material ("as you saw in the demo"): cut or fix the reference.
- Audience questions stay when they are good and audible; their audio comes from the room mic, gated in only while they speak.
- Private people are not named on screen; a host's self-introduction is proposed as a cut.
- Subtitles stay on for the whole video; on screen-recording shots they sit on a soft box so slide footers stay readable.
- One spent moment per chapter at most (a title behind the speaker, a B-roll graphic). The talk is the content.
