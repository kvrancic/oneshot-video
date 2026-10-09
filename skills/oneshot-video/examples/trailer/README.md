# The oneshot-video trailer

The 40-second trailer at the top of the repo's README, made with from-scratch mode on the author's own talk. This is the film's source as it was rendered.

- `src/Main.tsx`, `src/timing.ts`: the film. Drop them into a project made with `scripts/film.sh DIR`, which supplies `index.ts`, `Root.tsx`, the kit and the sound kit.
- `chip.py`: the music and the 8-bit effects, all synthesized, so they carry no licence. It makes a 128 BPM chiptune that ducks under the voice and goes silent under the Boston opener, plus blips, a coin, a zap, a stamp and a power-up: `.venv/bin/python chip.py DIR/public/audio/chip128.wav` (the effects go to `DIR/public/sfx`).
- What it expects in `public/` is the author's material, so swap in your own:
  - `footage/`: excerpts of the raw talk and of its edit, three 9:16 clips, and the Boston opener
  - `audio/z_*.wav`: the stumbles the edit removed
  - `sprites/`: pixel art from the talk's slides
  - `fonts/`: Jersey 10 and Silkscreen, from Google Fonts (SIL OFL)

The story it tells:
1. A hook: "who says AI video can't be edited in Premiere, Resolve or Final Cut?"
2. The raw recording and the edit, on the same sentence.
3. The stumbles zapped out.
4. The long form, then the short form, then a film from scratch.
5. A callback to the three editor timelines.

Render it with `scripts/master.sh DIR` (-14 LUFS, -2 dBTP). For editor layers, run `scripts/film_layers.py DIR --fcpxml`.
