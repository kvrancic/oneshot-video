# Captions

Captions are table stakes (about 80 percent of 13.5M exported clips use them); the difference is taste. What reads as premium in 2026 is restraint with exact timing: one sans in two weights, mixed case, warm off-white with a soft shadow in place of a thick stroke, one accent word per page at most, pages laid out in advance so nothing jitters, entrances that decelerate and exits that are shorter. What reads as cheap is the 2023 preset look every clipper still ships: all-caps Montserrat or Komika with a 10 px black stroke, yellow and green on every other word, every word bouncing, emojis, captions over the face.

## Presets

Sizes are for a 1080x1920 frame (9:16) and a 1920x1080 frame (16:9). Fonts are local (Inter, Instrument Serif, Geist Mono; all OFL).

| preset | look | fits | avoid for |
|---|---|---|---|
| `lecture` | Inter 600, 58/48 px, 4 to 7 words, whole page visible, spoken words brighten from 60 percent, text-sized scrim | explainers, lecture excerpts, anything where a missed word loses the argument; the safe default for talks | nothing; it is the rail |
| `verdict` | Inter 800, 76/62 px, 1 to 3 words, chunk springs in (4.9 percent overshoot), one accent word | hot takes, contrarian claims, hooks, clips under 40 s | stories over 30 s (fatiguing) |
| `fireside` | Inter 500, 62/50 px, 3 to 5 words, each word rises from its own timestamp, one Instrument Serif Italic word as the image | stories, anecdotes, "here is what happened" | lists |
| `index` | the lecture rail plus a persistent item heading and a segmented progress bar | lists, frameworks, steps | single claims |
| `epigraph` | Instrument Serif Italic 72/56 px, words etch in slowly | reading a quote, a definition, a line from an essay | fast speech |
| `ledger` | Inter 600, speaker A left-aligned warm, speaker B right-aligned cool, slides in from the speaker's side | two-person exchanges, debates, Q&A | monologue |
| `dusk` | Inter 500 lowercase, 54/44 px, slow fades, no emphasis colour, clears on long pauses | reflective endings, philosophy, slow monologues | anything punchy |
| `karaoke` | Inter 700, 64/52 px, one accent box glides from word to word on a critically damped spring | energetic podcast clips, creators who want motion in the text | serious or sad material |
| `punch` | Inter 900, 92/72 px, two-word punches, one accent word | high-energy hooks, sports-like pacing; the loud option done without strokes | anything over 30 s |

Map by content: hot take → `verdict`; story → `fireside`; explainer → `lecture`; list → `index`; quote → `epigraph`; two people → `ledger`; reflective → `dusk`. A clip can switch preset for its first 3 s (a `verdict` hook over a `lecture` clip) by putting the hook words in `captions.zones` with a different preset; keep it to the hook.

## Placement

- 9:16: baseline of the last line at y 1380 to 1440 (72 to 75 percent of the height), inside x 72 to 1008, clear of the bottom 400 px (platform UI) and of the right 140 px below y 1100 (like and share buttons). In the stage layout, captions sit at y 1480 over the speaker's chest.
- 16:9: baseline at y 984, measure at most 1500 px; in the stage layout they centre under the speaker shot.
- Never over the face. `qa.py` checks captions against the face track.
- Bright backgrounds (a projector, a white wall) need the scrim; `lecture` has it, the others rely on shadow. If a clip sits on a bright plate, pick `lecture` or `karaoke`.

## Emphasis

At most one emphasized word per page and on at most about 20 percent of pages. Emphasize the word that carries the surprise or the claim: a number, a negation ("never", "only", "not"), a named concept, the contrast term. Never "AI" by reflex. `accent` colours the word; `serif` switches it to Instrument Serif Italic (the ironic word, a quoted phrase, an inner thought).

## Words

- Captions show what was said, cleaned: fillers go (`um`, `uh` automatically; "like" via `captions.drop` when it is noise), numbers as digits, names spelled right (fix by index in `captions.fixes`), curly quotes, no em dashes.
- Every name, number and "not" gets checked against the context before render. Words marked `?` in the transcript are where the two ASR models disagreed.
- Timing: pages appear about 100 ms before the first word (a visual that leads sound feels in sync; one that lags by 100 ms feels late), hold about 0.6 s after the last word unless the next page needs the space and never cross a breath break. `render.py` re-times every word against the finished voice track, so the timing matches the audio that ships.

## Implementation notes (renderer/src/captions)

- `layout.ts` groups words into pages on breath and clause (pause over the preset's threshold, sentence end, clause opener after the target duration, character budget), balances two-line pages without orphans and measures every word once with the real font, so words never reflow when they light up.
- `Captions.tsx` animates transform and opacity only; exits are hard cuts when the next page follows immediately, fades otherwise.
- New presets go in `presets.ts`; keep one family, two weights, one accent.
