# Working on oneshot-video

This repo is an agent skill. `skills/oneshot-video/SKILL.md` is what an agent follows when someone *uses* it; this file is for agents *changing* it.

## Layout

- `skills/oneshot-video/SKILL.md`: the router (start menu, modes, report command). Keep it under 500 lines; detail goes in `workflows/` and `references/`.
- `skills/oneshot-video/workflows/`: one file per mode (`clips.md`, `full-edit.md`, `from-scratch.md`).
- `skills/oneshot-video/references/`: the craft (selection, editing, captions, graphics, sound, platforms, review, plan schema).
- `skills/oneshot-video/scripts/`: standalone CLIs, usage in each docstring. Plans (JSON) are the interface between the agent and the scripts.
- `skills/oneshot-video/renderer/`: Remotion. `src/Clip.tsx` (clips), `src/kit/` (from-scratch components), `src/graphics/`, `src/captions/`.
- `skills/oneshot-video/templates/film/`: the from-scratch project template (`scripts/film.sh` copies it).
- `.claude-plugin/`: this repo is its own Claude Code marketplace. Validate with `claude plugin validate . --strict`.
- Runtime (venv, models, node_modules, the matte binary) lives in `~/.oneshot-video` and is symlinked in by `scripts/install.sh`. Never commit it.

## Rules

- A new capability is a plan key the scripts understand plus a paragraph in the workflow or reference that tells the agent when to use it. Behaviour the agent cannot discover from the docs does not exist.
- Check changes on real footage and look at the output (stills, contact sheets, the render). Typecheck the renderer (`cd skills/oneshot-video/renderer && npx tsc --noEmit`).
- Match the surrounding style: plain names, short functions, comments that say why.
- Never commit media, transcripts, work folders or personal paths.
- Exports marked beta (Final Cut, Resolve) say so in the docs until someone confirms an import in that editor.
