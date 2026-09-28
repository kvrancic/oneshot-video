# Graphics and overlays

The rule under all of it: **show what the speaker made the viewer imagine, on the word and nothing they did not say.** One overlay besides captions at a time. One spent moment per clip (a takeover, a reveal, text behind the speaker). Silence in the graphics is what makes the next one land.

## What the speaker says → what to show

| speech | show | component |
|---|---|---|
| names a person the viewer should know | portrait, name, role, their stance in the speaker's words | `StanceBoard` card, or `NameTag` for the speaker |
| compares several people or positions | each lands on an axis as named; a reveal regroups them when the speaker states the pattern | `StanceBoard` (stage) |
| a number that is the point | the number, counted up, landing as it is said | `NumberCallout` |
| a list | an item heading per item, a segmented progress bar | `index` caption preset + `ChapterCard` |
| a quote from someone | the quote on a paper card, attributed, verbatim | `QuoteCard` |
| "swap X for Y and it sounds like today" | the quote, with X struck and Y written above it as it is said | `SwapQuote` (stage) |
| the one line that matters | the words take the frame, landing on their spoken frames | `Takeover` |
| a qualification of their own claim | a footnote a beat later ("*the tests it wrote itself") | `Footnote` |
| a slide being discussed | the deck page, crisp, in the panel; highlight the phrase being read | stage `slide` visual |
| a concrete object or place ("a factory floor") | a B-roll cutaway, 1.5 to 3 s | `visual` span, `image` or `video` |
| a term the audience may not know | a chip beside the head | `KeywordChip` |

If a sentence answers none of these, leave the frame alone.

Words on a graphic quote the speaker exactly ("then does essentially nothing different", not a paraphrase). A group label on a reveal lands when the speaker names that group, not before, and a person the pattern does not fit stays neutral instead of being forced into a group.

## Components (props)

- `HookBar {text, collapseAt?, persist?, treatment: "paper"|"float"}`: top-left headline for the first 3 to 6 s; `\n` splits lines; cold-reader words, one number at most. It is fully drawn on frame 0 (the first frame is the thumbnail) and ends before the name tag starts: never both at once.
- `NameTag {name, role?, y?}`: once per clip, 2 to 6 s in, on a quiet beat; hairline in the accent, mask reveal.
- `KeywordChip {text, x?, y?, dot?}`: beside the head on the empty side, 100 to 200 ms before the term.
- `QuoteCard {lines[], who?, y?}`: paper card, serif italic, opening mark hung in the margin; verbatim only.
- `Takeover {words: [{text, at, serif?, accent?}], size?: {v, h}, align?, dim?}`: after a 4 to 8 frame void; words land on their spoken frames (`at` references); hide captions for its span (`captions.zones ... hide`).
- `Footnote {text}`: bottom-left, a hairline then the line; at most one per clip.
- `NumberCallout {value, land, prefix?, suffix?, label?, decimals?, x?, y?}`: counts up over 0.8 s and lands on `land` (a word reference to the spoken number's end); an accent underline draws after. Count only meaningful digits ("300k", not 300,000 rolling).
- `ChapterCard {num?, title}`: section changes in long segments.
- `TextBehind {text, y?, size?, accent?, serif?}`: the spent moment, one huge word behind the speaker (Apple Vision person matte, cut by `render.py` for just that span). Speaker layout only, steady framing, no cut inside its span, 1.5 to 3 s. The word must be wider than the person so it reads around them. Dim the captions for its span (`captions.zones ... dim: 0.55`).
- `EndCard` via `plan.end {text, handle, from}`: where the full thing lives; skip it on looping clips.
- `SwapQuote` (stage or visual): `{lines[], who?, lineAt?[], swaps: [{word, to, at}]}`. A quote on paper that gets proofread live: at each swap the word is struck through and its replacement lands above it in the accent. For "an old complaint that reads like today's" (Baudelaire on photography, swapped to AI and coder). Nothing reflows.
- `StanceBoard` (stage or visual): `{title, axis: {left, right}, people: [{id, name, role, photo, x 0..1, row -1|1, group, at, stance, note?: {text, at}, years?: {label, values[], at[]}}], reveal?: {at, title, groups: {key: {label, color: "accent"|"cool"}}}}`. Opens with a large heading and an empty axis, shrinks the heading when the first person lands, stamps and strikes years (a promise made three times) and on the reveal dissolves the axis and regroups the chips by group with a count ("4 of 7").

## Stage layout

The default for lecture clips with visuals. 9:16: panel on top (820 px tall for graphics, 608 for 16:9 slides and images), speaker below, captions at the bottom. 16:9: panel left (1000x900, rounded card), a second camera renders a speaker-only shot for the right third. Graphics never cover the face in this layout, which is why it is the default.

## Portraits and images

1. The speaker's own material first: a portrait cropped from their slide (`assets.py portrait slide.jpg --out assets/name.png --scale 1.9`).
2. Wikimedia Commons with a free licence (`assets.py commons "Geoffrey Hinton" --out assets/`); the licence lands next to the file and in `credits.txt`.
3. Typographic monogram (initials on a dark disc) when rights are unclear: leave `photo` out.
Never a fake tweet, fake headline or fake screenshot. A real post is shown as a real screenshot with its date.

## Style system

- Palettes (`theme.ts`): `paper` (universal, accent #FF7A4D), `slate` (builder, #8AB4FF), `editorial` (thinker, #E07A5F), `nightlab` (safety, #FFB23F), `mono`. One accent per clip.
- One radius (12), one hairline (2 px), one card shadow; everything enters upward on an expo-out curve; three durations (6, 12, 21 frames); springs only for chips and pops, never bouncy.
- Film grain over the whole composite at 0.06 so graphics sit in the footage (`plan.grain`; 0 turns it off).

## Adding a graphic

Put a component in `renderer/src/graphics/`, register it in `Clip.tsx` (`VisualView`), take `w, h, palette, t0, vertical` plus its props, drive everything from `useCurrentFrame()` (no CSS animations, no wall-clock time), convert absolute edit seconds to local frames with `t0` and add a row to the table above. Render stills at its key moments before a full render.
