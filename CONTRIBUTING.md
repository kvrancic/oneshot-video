# Contributing

oneshot-video is a skill: a set of instructions an agent follows (`SKILL.md`, `workflows/`, `references/`) plus the tools it calls (`scripts/`, `renderer/`). Most improvements are one of three kinds, and all three are welcome:

1. **Craft**: a better rule for choosing a clip, cutting a sentence, placing a caption or mixing sound. These live in `references/*.md` and the `workflows/`. A good craft PR says what went wrong on a real video and what the new rule does instead.
2. **Tools**: a fix or a new capability in a script (`scripts/*.py`) or the renderer (`renderer/src`).
3. **Reach**: a new export target, a new harness, Linux support, a new caption preset or graphic.

## Found a bug?

Ask your agent to *"report a oneshot-video bug"*. It runs `scripts/report.sh`, which drafts an issue with your versions and the doctor output, scrubs your paths, user name and emails, shows you the draft and files it only when you say so. Or open an issue by hand with the bug template.

## Make it yours

Forking to fit your own channel is the intended use. The places to change:

| You want | Change |
|---|---|
| Your own caption look | `renderer/src/captions/` (presets) and `references/captions.md` (when to use which) |
| Your brand colours and fonts | `renderer/src/theme.ts`, `renderer/public/fonts/` |
| Different clip lengths, platforms, safe zones | `references/platforms.md` |
| How aggressive the full edit is | `workflows/full-edit.md` (intake defaults) and `references/longform.md` |
| What counts as a good clip for your audience | `references/selection.md` |
| New motion graphics | a component in `renderer/src/graphics/`, registered in the composition, documented in `references/graphics.md` |

The agent reads the docs every run, so a changed rule in a reference file changes the next edit. No retraining, no rebuild.

## Develop

```bash
git clone https://github.com/<you>/oneshot-video && cd oneshot-video
scripts/install.sh     # venv, models, Remotion, sound kit, matte tool, skill links
scripts/doctor.sh
```

Every script is a standalone CLI with its usage in its docstring (`.venv/bin/python scripts/edl.py --help`). The plan JSON files are the interface between the agent and the tools: the agent writes plans, the scripts resolve and render them. Keep it that way: a new capability is a plan key the scripts understand plus a paragraph in the reference that tells the agent when to use it.

Test on real footage. Put your test media and work folders outside the repo (`work/` and `oneshot-video/` are ignored if you keep them inside).

## Pull requests

- One change per PR, described by what it changes for the person editing.
- Say how you checked it: which mode, what source, what you looked at. Before/after stills help.
- Match the style around your change: short functions, plain names, comments that explain why.
- Do not commit media, transcripts, models or `node_modules`.

By contributing you agree your work is released under the MIT license of this repository.
