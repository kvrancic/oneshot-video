# The oneshot-video trailer

The 34-second trailer at the top of the repo's README, made with from-scratch mode: the film's source as it was rendered.

- `src/Main.tsx`, `src/timing.ts`: the film. Drop them into a project made with `scripts/film.sh DIR` (which supplies `index.ts`, `Root.tsx`, the kit, fonts and the sound kit).
- `music.py`: the music, synthesized (a 128 BPM groove, E C G D, a roll into the drop at 5.6 s, silent while the opener plays its own song, a build into the hit at 30 s), so it carries no licence: `.venv/bin/python music.py DIR/public/audio/groove128.wav`.
- Footage it expects in `public/footage/`: `cold.mp4` and `clipA-C.mp4` (3.9-second excerpts of 9:16 clips cut by clips mode from two CC BY talks, see the main README's credits) and `reveal_a.mp4`, `reveal_b.mp4` (excerpts of the Boston opener). Swap in your own.

Render: `scripts/master.sh DIR` (-14 LUFS, -2 dBTP). Editor layers: `scripts/film_layers.py DIR --fcpxml`.
