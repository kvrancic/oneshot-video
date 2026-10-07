# From-scratch mode

A brief in, a finished film out: a conference opener, a launch trailer, a product promo, an event recap, an explainer. Little or no footage of the user's own: the picture comes from stock (Pexels), the motion graphics kit and whatever the user has (a logo, one phone clip, a song). The result is a mastered MP4 and, if the start menu asked for it, the same film as editable layers for Premiere, Final Cut or Resolve.

Tools: `scripts/film.sh` (new project), `scripts/stock.py` (Pexels), `scripts/beats.py` (beat grid, song edit), `scripts/mapsvg.py` (maps), `scripts/master.sh` (render and master), `scripts/film_layers.py` (editor hand-back). Components: `renderer/src/kit/` (`Film`, `Seg`, `Sfx`, `Music`, `Shot`, `Finish`, `Flash`, `MaskLines`, `Slam`, `Label`, `Scrim`, `Checker`, `Board` with `planFromLocks`, `BuildTo`, `ShoutWord`, `Burst`, `RouteMap`). Read the components' comments before using them; each states its rule.

## 1. Intake

Look at everything the user gave first: `ffprobe` each file, a contact sheet of every clip (`ffmpeg -vf fps=1/2,scale=480:-2,tile=6x4`), transcribe any clip with speech (`transcribe.py`, with the names in `--context`). Then one AskUserQuestion (skip what the brief answers):

1. **Length**: 15 to 30 s (social), 45 to 60 s (opener, recommended for live events), 75 to 90 s (trailer). Follow the answer even when you recommended another.
2. **Music**: the user's track (they own or licensed it) · royalty-free (they pick from Pixabay Music, YouTube Audio Library or Uppbeat, or name one) · no music (voice and sound design only).
3. **Where it plays**: big screen in a room (type at least 40 px, nothing important in the bottom fifth, which is lost behind heads) · phone feeds (make a 9:16 version too) · both.
4. **What must be in it**: logo, the one clip, dates, a call to action, names. Ask for the logo as a vector or a large PNG and the clip at its original resolution.

Stock: if `PEXELS_API_KEY` is set (env, `.env` in the work folder, or `~/.config/oneshot-video/.env`) use `stock.py search`. If not, ask once whether they want to add a free key; otherwise search in the browser (below). Never scan the machine for keys.

## 2. Concept and beat sheet

Write `DIR/TIMELINE.md` before any code: the story in one line, then a table of beats (time, music event, picture, text on screen, sound effect). It is the brief for the critics too.

- **A film is a build to one peak.** Mystery or promise, escalation, the hit, then 4 to 5 s of payoff, then out. An opener ends on its peak (build, impact, payoff card), never on a calming fade.
- **Write the story onto the music.** Lyrics and hits carry the meaning: a line about a story starts the board; the held note is the board taking the screen; the hit is the reveal.
- **Order clues from obscure to obvious** and hold back the answer (letters, map highlights, recognisable shots) until the music gives it.
- **Spend the brand colour twice**: the opening and the payoff. A brand moment in the middle makes the payoff feel like a repeat. The brand transition (`Checker`) also twice, not on every cut.
- **One spent moment per scene.** Everything else is calm so that moment lands.

## 3. Music edit and timing

```bash
$CR/.venv/bin/python $CR/scripts/beats.py track song.mp3 --out DIR/beats.song.json         # tempo, beats
$CR/.venv/bin/python $CR/scripts/beats.py transient song.mp3 --at 28.45                    # snap a planned cut to the drum hit
$CR/.venv/bin/python $CR/scripts/beats.py splice song.mp3 --keep 0-28.446 45.039-63.2 --out DIR/public/audio/music_edit.wav --beats DIR/beats.song.json
$CR/.venv/bin/python $CR/scripts/beats.py track DIR/public/audio/music_edit.wav --out DIR/beats.edit.json   # check the seam: even intervals
```

- **Cut a song in whole bars** (a multiple of 4 beats apart); `splice` snaps each seam to the transient and crossfades 6 ms. Re-track the edit: the beat interval must stay even across every seam.
- **Never trust word timestamps on singing.** Whisper is off by a second or more on sung vocals and invents text over instrumentals. Pin each lyric hit with `beats.py onset --near T` (vocal-band onset), confirm by transcribing a short snippet around it, and transcribe the rendered mix at the end.
- **`src/timing.ts` holds every time.** Scene starts as beat indices (`B[16]`) or verified lyric times; a supplied clip anchored from the moment that must hit (`clipZero = hit - 5.45` puts the end of a shout on the hit). Components never contain their own times.
- **The hero letter or word must be settled on the hit frame**: start its 3-frame flip 3 frames early, and fire the glow, the pop, the clack and the boom on the same frame. A riser goes where its peak (measure it: `ffmpeg -af silencedetect`) lands on the hit.

## 4. Stock

```bash
$CR/.venv/bin/python $CR/scripts/stock.py search "harbor sunset drone" --n 30          # with a key
$CR/.venv/bin/python $CR/scripts/stock.py sheet 31081011 11960240 ... --out DIR/review/stock-1.jpg
$CR/.venv/bin/python $CR/scripts/stock.py frames 31081011 --out DIR/review/px_31081011.jpg --every 3   # choose the in-point
$CR/.venv/bin/python $CR/scripts/stock.py get 31081011 11960240 --out DIR/public/footage --seconds 20
```

**Without a key**, search in the browser (Claude in Chrome or the harness's browser tool): open `https://www.pexels.com/search/videos/<query>/?orientation=landscape`, and collect the ids in the page with JavaScript (`[...document.querySelectorAll('a[href^="/video/"]')].map(a => a.href.match(/-(\d+)\/?$/)?.[1])`). Search pages refuse curl (Cloudflare); file downloads do not, so `stock.py` takes over from the ids. Browser tools cut long output: store results in `window.__ids` and read them in pages of 20.

- **Look at every clip before it goes in** (the sheets). Titles do not prove places: "Boston aerial" returns Prague and Philadelphia. A named location needs a recognisable landmark in frame.
- 4 to 8 searches per scene, 10 to 30 candidates on a sheet, pick by the frame, pick the in-point from `frames`.
- A low-resolution supplied clip stays soft: upscale with Lanczos, a warmer and punchier grade, a tighter push and grain so the softness looks intended, and ask for the original.

## 5. Build the film

```bash
$CR/scripts/film.sh DIR          # template + kit + fonts + sound kit; renders as-is
cd DIR && npx tsc --noEmit       # after every edit
$CR/scripts/master.sh DIR --scale 0.5     # fast draft
```

Replace `src/Main.tsx` scene by scene from the beat sheet, `src/timing.ts` with the real grid (`beats.edit.json`). Fonts: put extra faces in `public/fonts` and add them to `loadFonts` (a display face with a width axis, such as Archivo, makes slams and boards look designed). Maps: `scripts/mapsvg.py us|world --points ... --out src/map.json`, then `RouteMap`.

- **Every shot moves** (`Shot` pushes by default). A held frame on a beat-driven film reads as a stalled player.
- **Text on footage gets a `Scrim`** or a darker plate (`dim`); captions sit over torsos, never faces; check at the maximum push.
- **Reserve layout from the first frame**: a subline that appears later must not shift the hero word.
- **On the frame after an impact the hero word is readable**: burst out from behind it (`Burst` under the word); a covering wipe hides it.
- **Mark footage with `className="plate"`** (`Shot` does) and route audio through `Sfx`, `Music` and `Shot volume`: that is what lets `film_layers.py` split the film into editable layers.
- Sound: the kit in `public/sfx` (tick, whoosh, thud, riser, pop, paper, marker); for anything else, generate or source royalty-free effects and note their licence in `DIR/CREDITS.md`.

## 6. Review loop

For each version write `DIR/review/vN/`: the TIMELINE (or CHANGES), a 2 fps contact sheet, and frame strips around every hit (`ffmpeg -vf "select='between(n,1076,1091)',drawtext=text=%{n}..."`). Check the audio: `ebur128` per section (stacked booms run hot), and transcribe the rendered mix to confirm lyric overlays sit on their words.

Then spawn three critics in parallel (Agent, general-purpose), the same three each round, each with the review folder and its persona: **a film editor** (pacing, cuts, legibility, sync), **the client** (the message, the brand, would they show it), **the audience member** (seated at the back or scrolling: do they get it, do they feel the peak). Each scores 1 to 10 and signs off or lists defects. Apply what two or three ask for; weigh what one asks for. Iterate until all three sign off, then show the user.

The user outranks the critics: a sign-off is not satisfaction. Keep `DIR/review/KEEP.md`, a list of moments the user or the critics praised, and check every fix against it: a change that removes a praised moment needs the user's yes. When the user asks for a variation, copy the project (`cp -R DIR DIR-alt`) and keep the original untouched.

## 7. Master and hand back

```bash
$CR/scripts/master.sh DIR                          # -14 LUFS, -2 dBTP, AAC 320k; prints the measured loudness
$CR/.venv/bin/python $CR/scripts/film_layers.py DIR --fcpxml    # if the start menu asked for editor hand-back
```

`master.sh` trims the 2048 priming samples Remotion's AAC does not flag (otherwise the sound runs 42.7 ms late and every hit misses its frame) and masters in two passes: single-pass loudnorm misses its target, and a -1 dBTP ceiling overshoots after AAC encoding, so -2.

`film_layers.py` renders the plates (footage only, graded and moving), the graphics (ProRes 4444 with alpha, ~1 GB per 10 s) and one stem each for music, effects and voice, and writes the timeline with cuts from `SHOTS` and `SCENES` and markers from `MARKERS`. Check it: overlay plates and graphics at a few frames and compare with the film.

Handover: the film, its length and loudness, the version history in one line each, `CREDITS.md` (stock ids and pages, music licence, effects), anything to verify (places shown, names, dates), and the editor folder if made. Never publish.
