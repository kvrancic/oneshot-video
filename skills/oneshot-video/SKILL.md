---
name: oneshot-video
description: One-shot AI video studio, fully local on a Mac. Edits a raw talk, lecture, podcast or multicam recording into a finished long video (fillers and dead air cut, best camera angle, grade, titles, chapters, subtitles); cuts it, or any finished video, into standalone short clips with a virtual camera, word-timed captions and motion graphics for TikTok, Reels, Shorts, X and LinkedIn; or makes a promo, opener or explainer from a brief with almost no footage (script, Pexels stock, music edit, Remotion motion graphics). Hands timelines back to Premiere Pro, Final Cut Pro and DaVinci Resolve. Use when the user hands over a video file or folder, or says "edit my talk", "make clips / shorts / reels", "find the viral moments", "multicam edit", "remove the filler words", "make a promo / trailer / opener / reveal video", "export to Premiere / Final Cut / Resolve", or asks to re-cut a previous result. Also "report a oneshot-video bug".
license: MIT
compatibility: macOS on Apple Silicon; ffmpeg, Node 20+, Python 3.12 (installed by scripts/install.sh)
---

# oneshot-video

Footage (or a brief) in, finished video out: the full edit, the clips, the editor project. Everything runs on this Mac; the only network calls are optional (Pexels stock, Wikimedia portraits, GitHub for bug reports).

**Paths.** `$CR` is this skill's folder: `${CLAUDE_SKILL_DIR}` in Claude Code; in other agents, the folder that holds this SKILL.md (resolve symlinks). Set it once per shell command (`CR=...`). Python is `$CR/.venv/bin/python`, Remotion is `$CR/renderer`. Work goes to `./oneshot-video/<name>/` next to where the user is working unless they name another folder; never write work into `$CR`.

## 0. First run

```bash
$CR/scripts/doctor.sh      # prints ok / MISS with the fix for each gap
$CR/scripts/install.sh     # does all of it; heavy files go to ~/.oneshot-video and are linked in, so re-runs after an update take seconds
```

Run `doctor.sh` before the first job of a session and whenever a step fails. If anything is missing, say what and ask before running `install.sh` (it downloads about 1.5 GB).

## 1. Start menu

When the user hands over a file, a folder or a brief, look before asking: `ls` the folder, `ffprobe` the files (duration, resolution, how many cameras and audio sources). Then ask **one** AskUserQuestion call with what the request did not already answer (recommended option first, say why in its description). Skip the menu when the user said "auto" or the request is unambiguous.

1. **What to make** (single choice):
   - **Full edit**: the whole recording, cut tight and produced (fillers, restarts and dead air out, best angle, grade, titles, chapters, subtitles). Recommend for raw recordings over ~10 minutes.
   - **Clips**: standalone short clips (9:16 and 16:9) from any long video, raw or already edited. Recommend for a finished video or when the user mentions shorts, reels, TikTok.
   - **Full edit + clips**: the full edit first, then clips cut from it (one transcript, one sync, consistent look).
   - **From scratch**: a promo, opener, trailer or explainer from a brief, with almost no footage (stock video, music, motion graphics). Recommend when there is no long recording, only a brief, a logo or a few clips.
2. **Hand-back** (multiSelect; ask only for full edit, full edit + clips and from scratch):
   - **Finished MP4s** (always on; mention it).
   - **Premiere Pro project** (FCP7 XML, tested): recommended.
   - **Final Cut Pro project** (FCPXML, beta).
   - **DaVinci Resolve** (imports the XML or FCPXML, beta).

Clips always come out as finished files per platform (`slug.9x16.mp4`, cover, .srt, post copy).

## 2. Run the mode

Read the workflow file for the chosen mode and follow it from its intake step (skip questions the start menu answered):

| Mode | Workflow |
|---|---|
| Full edit | `$CR/workflows/full-edit.md` |
| Clips | `$CR/workflows/clips.md` |
| Full edit + clips | `full-edit.md` to the end, then `clips.md` with the rendered `DIR/out/<id>-full.mp4` as the source (transcribing the finished edit takes minutes and gives clean word times; its sound is already cleaned and levelled) |
| From scratch | `$CR/workflows/from-scratch.md` |

The references in `$CR/references/` hold the craft (selection, editing grammar, captions, graphics, sound, platforms, review checklist); each workflow says which to read when.

## 3. Report a problem

When a step fails in a way the workflow cannot fix, or the user asks to report a bug or suggest an improvement:

1. Draft: `$CR/scripts/report.sh --title "<script>: <one-line symptom>" --step "<what was running>" --log <file with the error output> --note "<what you tried>"`. It prints the issue with versions and the doctor output; home paths, user name, emails and tokens are scrubbed.
2. Show the user the draft and ask before filing. Never include their media, transcripts or file names they did not approve.
3. File it: the same command with `--submit` (uses `gh`; without it, prints a link that opens the pre-filled issue).

Contributions: `CONTRIBUTING.md` in `$CR` explains how to fork, adapt and send a pull request.

## Rules for every mode

- Edit the plan, not the output. Re-cuts change the plan JSON and re-run the step; caches rebuild only what changed.
- Word indices, never hand-typed timestamps. Every cut lands on a word boundary or a pause.
- Look before handing over: read the stills, contact sheets and QA output each workflow produces; spawn a fresh-eyes critic for anything going public.
- Nothing on screen says what the speaker did not say. Private people are never named on screen. Claims about public figures are commentary; flag them in the handover.
- Never publish or upload anything. The user posts.
- Long renders run in the background; tell the user roughly how long and keep working on the next step.
