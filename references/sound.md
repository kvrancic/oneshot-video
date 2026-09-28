# Sound

## The voice

The sound comes from the best recording at the event, which `ingest.py` finds by measuring every audio stream (the lavalier in a Zoom recording beat the 4K camera's own microphone by 19 dB on the MIT lecture). `audio.py` re-measures the sync around each clip, cuts the voice on the edit timeline with 12 ms fades at every join, then cleans it by measurement (`"audio": {"clean": "auto"}`, the default):

| measured SNR | chain | typical source |
|---|---|---|
| 24 dB and up | light: high-pass 80 Hz, gentle FFT denoise, 2.5:1 compression | a lavalier, a studio mic |
| 14 to 24 dB | strong: more denoise, presence lift at 3.2 kHz, 3.5:1 compression | a phone near the speaker |
| under 14 dB | rnn: RNNoise (`arnndn`, 85 percent wet) then strong | a phone in a hall with an audience |

Everything ends at -16 LUFS; the mix goes to -14 LUFS later. Force a chain with `"clean": "light" | "strong" | "rnn" | "off"`. For a sound-only change (a better source, a different chain, music) run `render.py --audio-only`: it rebuilds the voice and the mix, remuxes them onto the existing renders in seconds and reports whether the burned-in captions still sit on the new voice.

## Levels (relative to the voice)

| element | level |
|---|---|
| final mix | -14 LUFS integrated, true peak at most -1 dBTP (limiter, then two-pass loudnorm in linear mode; `render.py` reports the mode) |
| music bed under speech | 18 to 25 dB under the voice, ducked a further 8 dB while words play |
| whoosh, transition | -16 to -22 dB |
| tick, pop, click | -20 to -26 dB |
| impact, thud | -14 to -20 dB, rare |

## The kit (assets/sfx, synthesized by sfx.py, no licence questions)

| sound | pairs with | timing |
|---|---|---|
| `whoosh-soft` | hook card, headline, zoom to a slide | starts 2 to 4 frames before the visual |
| `whoosh-long` | a whip or a section change | peaks on the cut |
| `tick` | a chip landing, a list item, a counter landing, a year stamped | on the landing frame |
| `pop-soft` | a badge or chip appearing | on the frame |
| `thud-soft` | a takeover's last word, a reveal | exactly on the frame |
| `riser` | 1.4 s into a reveal | ends on the reveal |
| `paper` | a quote card or document card | on the card's rise |
| `marker` | an annotation drawing on a slide | with the stroke |

Density: 0 to 4 effects per minute for talks; a list may take one per item. None under the first words of the hook, none on caption pages, never meme sounds. If a sound would make someone look up from the caption, cut it.

## Music

Off by default for lectures and podcasts: the speech is the content and an AI-literate audience hears a bed as marketing. Use one for explainers, lists and some stories.

- Character: sparse ambient electronic, felt piano, soft synth arpeggios; 70 to 100 BPM; no vocals; sparse in 1 to 4 kHz; ends on a resolved chord.
- Avoid: corporate ukulele, trap, epic trailer drums, motivational swells, lo-fi study beats, trending platform sounds.
- Source: the user's own licensed library (`"music": {"file": ...}`), or no bed and pick a track in the app at posting (reach, no licence risk). If the user asks for generated music, say it needs a service; the skill itself stays local.
