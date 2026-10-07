# Cut and camera grammar

## Cuts

- **Hard cuts are the default.** Crossfades only for passage of time and into an end card. A crossfade between two parts of the same speech reads as a mistake; a framing change reads as an edit.
- **Every internal cut changes the framing.** The camera alternates `cutZoom` (1.00 / 1.12) per segment, so a jump cut looks like a second camera. Turn it off (`"cutZoom": []`) only for a single continuous take.
- **Cut on words, land in silence.** `edl.py` puts the head 0.02 to 0.45 s before the first word at the quietest 10 ms and the tail 0.06 to 0.6 s after the last word, then fades 12 ms at every join so nothing clicks. It refuses to cut a pause that is not quiet.
- **Pauses:** cut those over about 0.7 s by default; keep the ones before a punchline, after a dry line and in reflective material (`keepPauses`). A clip with every breath removed sounds like a machine.
- **Cadence for talks:** something visual changes every 3 to 6 s (a cut, a punch, a panel change, an overlay), tighter (2 to 3 s) in the 5 to 10 s before the payoff, holds of up to 8 to 10 s on a strong line. A caption page change does not count. 1.5 s cadence reads as frantic to an AI-literate audience.
- **Speed:** 1.0 for lectures. Podcasts on X can take 1.05 to 1.1 with pitch preserved; never on a lecture where credibility matters.

- **Filler inside a sentence: hide it, do not cut it.** Cutting every "like" leaves 0.6 s segments and a jump cut a second. Put the word in `captions.drop` (hidden, still heard) and keep the take continuous; cut from the audio only fillers that sit at a clause boundary or a stumble.
- **Minimum segment:** about 1.2 to 1.5 s. Shorter runs read as a glitch. `"minRun": 1.2` in a plan rejoins pieces that were split off only by a pause or filler; for the rest, drop an orphaned connective with the stumble beside it, or restore a tiny self-correction instead of cutting around it.

## Camera (reframe.py)

The virtual operator holds a locked shot while the subject stays inside a dead zone (default half-width 18 percent of the crop) and when the subject leaves it, eases to a new framing that starts before they reach the edge (it knows the future). Runs of short holds (someone walking) become a smooth follow. Every cut restarts the shot.

- **Framing, 9:16:** face width about 17 percent of the crop (a medium shot), eyes at 36 percent from the top, face centred horizontally ±60 px.
- **Framing, 16:9 speaker shot:** face about 9 percent of width (the room stays in frame); the stage layout's speaker shot uses 20 percent.
- **Resolution:** every crop comes from the source pixels. From a 4K original a 9:16 medium shot is a 1.6x upscale; from a 1080p file it is 3x or more and looks soft. `reframe.py` prints `max upscale`; above 2.0 say so and prefer a wider framing (`faceFrac` 0.12) or the stage layout.
- **Punch-ins:** 1.08 to 1.15 on a line that matters (hook, claim, punchline, section turn). They hold until the next cut. Use 2 to 4 per minute at most; loudness-triggered zooms end up at 8 per minute and read as a twitch.
- **Pushes:** 1.00 to 1.05 to 1.08 over 2 to 4 s while a thought builds; then a hard cut back.
- **No simulated handheld shake**, no rotation, no spin transitions.
- **Several people:** run `track.py` once per person with `--hint x,y` (source pixels), give each a plan span and cut on turns. Keep every shot at least 1.5 to 2 s; ignore one-word interjections ("right", "exactly") when deciding whose turn it is. If two faces fit one crop, frame both.

- **Wide shots leak.** A wide frame shows whatever is on the projector: numbers never said, a video-call popup, the answer to your own reveal. For 16:9 speaker spans use a follow shot (`"layout": {"16x9": {"mode": "follow", "faceFrac": 0.06}}`) unless the slide is the point, and look at the slide in every wide still.

## Slides and screens

- Never crop a slide or a screen to fit 9:16. Use the stage layout with the slide in the panel, or a `visual` span.
- Use the speaker's own deck (`assets.py deck deck.pdf --out assets/`) instead of the filmed projection; the projection is washed out and keystoned. A slide may be pushed in to 1.6 to 2.2 on the region being discussed when it comes from the deck; a filmed projection never past 1.3.
- Highlight the phrase being read (`visual.highlight`), 3 to 6 frames before it is spoken.

## Cold opens and loops

- A cold open is 3 to 8 s of the payoff, cut on words, then a hard cut to the setup with a framing change. The hook card sits over it.
- A loop ending: end on a line that flows into the first line (Shorts count every replay as a view). No end card on a looping clip.

## Transitions (budget: one per clip, each with a reason)

| transition | when |
|---|---|
| match cut | same gesture, framing or word across a cut (best in a montage of people) |
| J-cut | the next speaker's audio leads the picture by 6 to 12 frames |
| whip | a change of place or source |
| zoom blur | going into a slide or a screen |
| glitch | only when the content is about something breaking |
