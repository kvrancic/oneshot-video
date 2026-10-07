# The oneshot-video trailer

The 32-second trailer at the top of the repo's README, made with from-scratch mode: the film's source as it was rendered.

- `src/Main.tsx`, `src/timing.ts`: the film. Drop them into a project made with `scripts/film.sh DIR` (which supplies `index.ts`, `Root.tsx`, the kit, fonts and the sound kit).
- `music.py`: the music, synthesized (a 120 BPM groove, Am F C G, a build into a hit at 26 s), so it carries no licence: `.venv/bin/python music.py DIR/public/audio/groove.wav`.
- Footage it expects in `public/footage/`: `clip1-3.mp4` (9:16 clips cut by clips mode from a CC BY speech, see the main README's credits) and `reveal_map.mp4`, `reveal_board.mp4` (excerpts of the Boston opener). Swap in your own.

Render: `scripts/master.sh DIR` (-14 LUFS, -2 dBTP). Editor layers: `scripts/film_layers.py DIR --fcpxml`.
