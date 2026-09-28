# cutroom

A Claude Code skill that turns a long video (lecture, talk, podcast, interview) into finished short clips, fully on your Mac.

It reads the whole transcript and picks moments that stand alone (a real head, a finished tail, a hook in the first three seconds), cuts them on word boundaries, follows the speaker with a virtual camera cropped from the 4K original, adds word-timed captions in nine presets and motion graphics built from what was said, mixes the sound to platform loudness and exports 9:16 and 16:9 files with covers, subtitles and post copy.

## Install

```bash
git clone <this repo> ~/Documents/projects/cutroom
~/Documents/projects/cutroom/scripts/install.sh      # venv, models (~1 GB), Remotion, sound kit, ~/.claude/skills/cutroom symlink
~/Documents/projects/cutroom/scripts/doctor.sh       # checks everything
```

Needs macOS on Apple Silicon, Homebrew, Node 20+, about 5 GB free while rendering. Everything runs locally; Pexels (B-roll) and Wikimedia Commons (portraits) are optional network calls.

## Use

In Claude Code:

> Use cutroom on ~/Movies/talk.mov. I want 4 clips for TikTok and X and one about the part where I compare the AI CEOs.

Claude asks a few multiple-choice questions (formats, energy, extras), transcribes, proposes clips, asks which to make, plans each one, shows stills, renders, checks and packages everything into `exports/<date>/` with a review page. Say "auto" to skip the questions.

## Layout

- `SKILL.md`: the workflow Claude follows.
- `scripts/`: ingest, transcribe, track, candidates, edl, reframe, audio, assets, sfx, render, qa, package.
- `renderer/`: the Remotion project (captions, overlays, graphics).
- `references/`: selection doctrine, plan schema, editing, captions, graphics, sound, platforms, review checklist, research summary.
- `docs/research/`: the four full research reports.
- `examples/`: a complete plan for a 2:45 clip with a stance board, cold open and reveal.

Fonts: Inter, Instrument Serif and Geist Mono (SIL OFL). Remotion is free for individuals and companies of up to three people; larger companies need a Remotion licence.
