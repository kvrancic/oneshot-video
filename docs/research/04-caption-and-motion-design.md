# 04 · Captions and motion design for lecture and podcast clips (September 2026)

Research brief for a Remotion (React) renderer that edits lecture and podcast clips of a speaker. Audience: tech, AI, founders. Tone: smart, understated, a little ironic, never hype. Output: a caption taxonomy, the cheap-versus-premium line, seven presets with full specs, an overlay style system, transition grammar and sound design.

Conventions used below:

- Frames are 1080x1920 (9:16) and 1920x1080 (16:9). Render at 30 fps; durations are given in ms and in frames at 30 fps (`f`).
- "Sourced" numbers carry a link. Numbers marked **(rec)** are my recommendation, derived from the sources plus measurement. Where a source is a vendor blog or a third-party breakdown, treat it as an operator claim, not a study.
- Character widths were measured with the Inter variable font (Google Fonts build, opsz and wght axes) using PIL. Mixed-case Inter averages 0.44 to 0.47 em per character including spaces; all caps is about 24% wider (0.57 to 0.58 em).
- Spring numbers were computed with Remotion's own closed-form spring (`packages/core/src/spring/spring-utils.ts`). One consequence matters for every preset: when damping ratio ζ ≥ 1, Remotion switches to the critically damped formula with ω0 = √(stiffness/mass). So `{damping: 200}` does not mean "slower than damping 50"; it means "critically damped". Only stiffness and mass set the speed.

---

## 0. The one-paragraph answer

What reads as premium in 2026 is restraint with precise timing: one sans family in two weights, mixed case, a warm off-white with a soft shadow in place of a thick stroke, one accent color per video used on at most one word per caption page, captions pre-laid-out so nothing jitters, entries of 200 to 450 ms on a decelerating curve with exits shorter than entries, plus one "spent" moment per clip (a takeover phrase or a word behind the speaker). What reads as cheap or AI-generated is the 2023 preset look that every clipping tool still ships by default: all-caps Montserrat or Komika with 8 to 12 px black strokes, yellow and green highlights on every other word, every word bouncing, emojis, whooshes on every cut, captions over the face. The AI-researcher audience has seen that look ten thousand times on "guru" content; Dwarkesh Patel's clip guidelines explicitly ban "super cringe and distracting popping text and emojis" ([dwarkesh.com](https://www.dwarkesh.com/p/clips-competition)).

---

## 1. Taxonomy of caption styles in use now

### 1.1 Summary table (1080x1920 unless noted)

| Style | Font / weight | Size | Case | Words per chunk | Lines | y position | Base / active / emphasis | Stroke / shadow / background | Animation | Emoji | Emphasis rule |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Hormozi ("Mozi") | Montserrat Black 900; alternates Anton, Bebas Neue, TheBoldFont | 80–120 px | ALL CAPS | 1–3 | 1 | 60–70% | #FFFFFF / same / #FFD93D yellow or #39FF14 green (also #F7C204, #02FB23) | 8–12 px black stroke; shadow 4 px offset, 80% opacity, 0 blur | instant snap, scale ≤105%; many presets add ±3–5° rotation and a 1.0→1.15→1.0 pop | frequent, above the line | exactly one keyword per phrase |
| MrBeast / "Beasty" | Komika Axis (italic comic display) | 90–120 px | ALL CAPS | 1–2 | 1 | ~55–65% | white / green or yellow keyword / glow | heavy stroke, keyword shadow or glow | fast pop with overshoot per word | common | keywords colored, high frequency |
| Ali Abdaal "clean" | TT Fors or Inter-like grotesk | 50–64 px | sentence case | phrase (4–8) | 2–4 | side column or lower third | sober neutral; spoken words fade; yellow keyword | often a rounded rectangle behind | word-by-word fade, no rotation | none | few, yellow |
| Iman Gadzhi | Montserrat Light → Bold | 56–66 px | lowercase | 2–5 | 1–2 | 60–70% | white only | subtle shadow, no stroke | each word goes light→bold as spoken | none | none by color; weight is the highlight |
| Karaoke highlight box | Montserrat/Poppins/Inter 800 | 64–80 px | either | 3–6 (whole page visible) | 1–2 | 65–72% | white or 60% white / box color behind active word | box radius ~0.2 em, padding ~0.08×0.25 em | box snaps or slides word to word | varies | every word gets the box in turn |
| Podcast (DOAC grammar) | condensed bold | 80–100 px | UPPER (standard) / lowercase (emotional) | 1–3 | 1 | 60–70% | host yellow, guest white | heavy black outline; emotional clips use soft shadow, no yellow | hard cuts | none | speaker color, not word color |
| Editorial serif | Instrument Serif Italic (hero) + Inter / Instrument Sans (base) | serif 72–110 px, sans 54–64 px | lowercase or sentence | 2–5 | 1–3 | column or center | cream #F2EAD8 / white / scene accent | screen blend or soft shadow, no stroke | x-glide 10 px over 550 ms; hero per-letter 22 ms stagger | none | one serif word per 1–2 pages |
| Minimal lowercase ("dynamic minimalism") | Inter / SF-style 500–600 | 52–62 px | lowercase or sentence | 3–6 | 1–2 | 62–72% | off-white / brand color keyword | soft shadow only | fades, no pops | none | rare, brand color |
| Apple keynote | SF Pro Display → Inter Display 600–800 | 64–96 px body; hero 140+ | sentence | phrase, few words held long | 1–2 | center | white / dim others to 35% / #8AB4FF fallback accent | none, dark plate | phrase wipe 400 ms expo-out or deblur 800 ms | none | one hero word, the rest dims |
| Typewriter / terminal | VT323, JetBrains Mono, Geist Mono | 34–48 px | as spoken | streaming | 3–6 in a panel | docked panel | #BFEEFE on rgba(2,14,22,.62) / cyan #66E0FF / magenta #FF5FD6 | panel, caret | 25–35 ms per character, caret blink | none | apex word decodes from glyph noise |
| Takeover / "stomp" | condensed or display grotesk 800–900 | 140–260 px | either | 1–4 | 1–3 | full frame | white on dimmed or solid plate | none | hard cuts per word after a short void | none | the whole card is the emphasis |
| Text behind subject | display grotesk 800 or serif italic | 300–420 px | either | 1–2 | 1 | behind head/shoulders | off-white or accent | plate dimmed ~16% | rise or wipe, ≥1 s dwell | none | once per clip, the apex |

Sources for the table: Hormozi specs from [Ascynd](https://ascynd.io/en/blog/hormozi-captions), [Blitzcut](https://blitzcutai.com/blog/best-caption-fonts-tiktok) and [Sendshort](https://sendshort.ai/guides/hormozi-captions/); MrBeast from [Submagic](https://www.submagic.co/blog/how-to-make-captions-like-mrbeast); Ali Abdaal from [Submagic](https://www.submagic.co/blog/make-captions-like-ali-abdaal) and [Sendshort](https://sendshort.ai/guides/ali-abdaal-captions/); Iman Gadzhi from [Submagic](https://www.submagic.co/blog/how-to-make-captions-like-iman-gadzhi); karaoke sub-styles from [videocaptions.ai](https://www.videocaptions.ai/caption-styles/karaoke) and [EchoWave](https://echowave.io/tools/animated-captions/); DOAC grammar from a third-party breakdown at [PandaStudio](https://www.writepanda.ai/blog/how-diary-of-a-ceo-edits-podcast-clips/); editorial, keynote, terminal, takeover and text-behind-subject values from HeyGen's open-source HyperFrames caption catalog ([CATALOG.md](https://github.com/heygen-com/hyperframes/blob/main/skills/embedded-captions/CATALOG.md), DNA files `editorial.json`, `keynote.json`, `documentary.json`, themes `anchor.json`, `terminal.json`); dynamic minimalism from [Joyspace](https://joyspace.ai/hormozi-editing-style-2026-analysis).

### 1.2 Style notes

**Hormozi.** The workhorse of 2022 to 2024. Montserrat Black 900 all caps, 80 to 120 px (10 to 15% of frame height), tracking 0 to −2%, white fill with one yellow (#FFD93D) or green (#39FF14) keyword per phrase, 8 to 12 px black stroke, shadow 4 px offset at 80% opacity with no blur, 1 to 3 words per beat, 200 to 500 ms per word, y ≈ 60 to 70% ([Ascynd](https://ascynd.io/en/blog/hormozi-captions)). The purist rule worth keeping: "Highlighting two or three words in the same phrase destroys the effect entirely; the whole point is that the eye has a single place to land." Every tool ships a preset (Submagic lists "Hormozi 1" through "Hormozi 5" in its [API](https://docs.submagic.co/api-reference/templates); Opus Clip ships "Mozi" in its [brand templates](https://help.opus.pro/api-reference/brand-template)). Joyspace's 2026 analysis says the look now triggers "production blindness": viewers file it as marketing-guru content and swipe.

**MrBeast / Beasty.** Komika Axis all caps, roughly 2 words per line, heavy stroke, green keywords with shadow or glow ([Submagic](https://www.submagic.co/blog/how-to-make-captions-like-mrbeast)). Built for challenge and reaction content. Wrong register for this creator in every respect.

**Ali Abdaal clean.** Sober grotesk, sentence case, no rotation or floating, words fade as spoken, a yellow keyword now and then, sometimes a rounded rectangle; some edits place a multi-line caption column beside the speaker so it reads like a page ([Submagic](https://www.submagic.co/blog/make-captions-like-ali-abdaal), [Sendshort](https://sendshort.ai/guides/ali-abdaal-captions/)). Submagic calls TT Fors "free"; TypeType sells it, so treat it as commercial and substitute Inter or Geist.

**Iman Gadzhi.** Montserrat, lowercase, white only, no colored keywords; each word animates from Light to Bold as it is spoken ([Submagic](https://www.submagic.co/blog/how-to-make-captions-like-iman-gadzhi)). This is the ancestor of the 2026 "luxury lowercase" look. Implementation trap: a weight change widens the word and reflows a centered line on every word. Fix with reserved bold width or a grade axis (section 2.3).

**Karaoke highlight box.** The whole page (3 to 6 words) is visible; the active word gets a color change, a scale bump, a bounce or a colored block behind it ([videocaptions.ai](https://www.videocaptions.ai/caption-styles/karaoke)). Podcast operators report 15 to 30% retention lift for word-by-word highlight over static captions ([Conbersa](https://www.conbersa.ai/learn/podcast-clip-captioning-best-practices); operator A/B claims, not a study). The premium version slides one box between measured word rects on a critically damped spring; the cheap version snaps a saturated box and bounces the word.

**Podcast lower third (DOAC grammar).** Third-party breakdown of Diary of a CEO clips: 1 to 3 words, bold condensed uppercase with heavy outline at 60 to 70% height; emotional clips switch to small mixed-case with soft shadow and no yellow; host lines yellow, guest lines white; a white box with black caps title banner that is gone by about 5.5 s; a hard cut every 4.1 to 6.3 s, 2.5 to 3 s near the payoff; no music, no SFX ([PandaStudio](https://www.writepanda.ai/blog/how-diary-of-a-ceo-edits-podcast-clips/)). The useful ideas are speaker-coded color and the early-exit title banner. The uppercase stroke look is the part to drop.

**Editorial serif.** Instrument Serif (Rodrigo Fuenzalida, 2022, one weight plus italic, OFL) became the default display serif of 2025 across AI-product and institutional brands ([A Type of Amigo](https://atypeofamigo.com/outstanding-fonts-why-is-instrument-serif-conquering-the-world/)). In video it appears as a lowercase italic hero word inside otherwise sans captions. HyperFrames' `editorial` identity: cream `#F2EAD8`, `mix-blend-mode: screen`, words glide in from x −10 px over 550 ms `power2.out`, hero per-letter stagger 22 ms with 1.5 px letter blur, tracking −0.01em. Caveat from several caption guides: serif hairlines vanish at caption size under compression ([Blitzcut](https://blitzcutai.com/blog/best-fonts-for-video-editing-2026), [Recapo](https://recapo.ai/blog/best-caption-styles-for-shorts/)). Use the serif at 72 px or more. Use it as a voice switch (quote, inner thought, the ironic word), never as the body face.

**Minimal lowercase / dynamic minimalism.** Keeps Hormozi's mechanics (word-synced chunks, jump cuts, zooms) while stripping the noise: clean sans, white text with subtle shadows, keywords in brand color, fades instead of pops, massive text only for the first 3 s ([Joyspace](https://joyspace.ai/hormozi-editing-style-2026-analysis)). FontMirror adds that 2026 chunking is slower: 2 to 4 word chunks held 600 to 900 ms. It also finds that "all-caps now reads as either shouty direct-response or visually dated" ([FontMirror](https://www.fontmirror.com/en/typography-trends-shaping-short-form-ai-video-content/)).

**Apple keynote.** Few words, held long, dead center, confidence from mass and stillness. HyperFrames `keynote` DNA: Inter 400/600/800, white `#FFFFFF`, accent fallback `#8AB4FF`, line reveal = horizontal wipe 400 ms `expo.out`, exit 300 ms `power2.in`, hero tracking −0.045em, other words dimmed to 35% while the hero shows. Premium entrance recipes from the same repo: "deblur" `{opacity 0, scale .96, blur 8px} → {1, 1, 0}` over 800 ms `power3.out`; "rise" `yPercent 48 → 0` over 900 ms.

**Typewriter / terminal.** HyperFrames `terminal`: VT323 body at 34 px in a docked glass panel `rgba(2,14,22,0.62)`, text `#BFEEFE`, accent `#66E0FF`, magenta `#FF5FD6`, typed entrance with caret; the apex word "decodes" through glyph reels with a 45 ms lock stagger; plate dimmed 22%, grain 6, RGB shift 4. The Remotion rule for typing is string slicing per frame, never per-character opacity (Remotion skill `text-animations.md`). For this creator the terminal look collides with a stated dislike of "texty tacky hackerish" monospace type (project memory, 2026-09-23). Use it only when the thing on screen is literally a log or code from a run.

**Takeover ("stomp").** Full-frame typographic cards with "a void before the drop" (HyperFrames `stomp`). Built from cuts rather than tweens: each word gets a fixed run of frames and the energy comes from rhythm ([snapcn](https://snapcn.dev/remotion-kinetic-typography)). Good for hooks and manifesto lines. Once per clip.

**Text behind subject.** Became mainstream in 2025 via CapCut and browser tools; the pipeline is segment the person per frame, then composite background, text, person cutout ([tscaps](https://tscaps.io/blog/text-behind-person-effect)). Meta's SAM 3 (released 2025-11-19) added text-prompted video segmentation. HyperFrames' rule: an embed is "the scarce, earned peak: one big word matted behind the subject at the climax, never every line", roughly one per beat, never two visible at once, at most one apex ([HyperFrames](https://hyperframes.heygen.com/prompting/captions-and-talking-heads)). Fails with two speakers, hard cuts and fast camera moves.

### 1.3 What is trending in 2026

1. **Rail plus one embed.** A calm, verbatim lower rail carries the transcript; exactly one peak word or phrase is promoted into the scene (behind the subject, or a takeover card). HyperFrames made this the default after testing; the rail is "deliberately plain": one sans at 500 to 600 weight, size ≈ 0.045 × frame height, fade 150 to 250 ms, no per-word choreography ([rail.md](https://github.com/heygen-com/hyperframes/blob/main/skills/embedded-captions/references/rail.md)).
2. **Mixed-case bold replacing all caps**, slower chunks (600 to 900 ms holds), brand-color keywords in place of generic yellow and green ([FontMirror](https://www.fontmirror.com/en/typography-trends-shaping-short-form-ai-video-content/), [Joyspace](https://joyspace.ai/hormozi-editing-style-2026-analysis)).
3. **Editorial serif accents** (Instrument Serif and kin) mixed into sans captions and title cards.
4. **Hand-drawn annotation layers**: marker highlights, red circles and arrows over slides and screenshots, read as "human attention" ([FontMirror](https://www.fontmirror.com/en/typography-trends-shaping-short-form-ai-video-content/); the Vox and Johnny Harris document-highlight style).
5. **Weight-shift captions** (Iman lineage); HyperFrames ships a `caption-weight-shift` component.
6. **Documentary restraint** for interview content: burn-in reveals, bone on charcoal, no accent (HyperFrames `documentary`, "Errol Morris dignity").
7. **Takeover hooks**: the first 3 s as a typographic card, then a clean rail for the rest.

Usage baseline: Opus Clip's analysis of 13.5M clips found 80.2% use captions and 78.6% use animated captions; static captions are 1.6% ([OpusClip](https://www.opus.pro/research/best-caption-strategy-short-form)). Captions are table stakes; the differentiator is taste.

---

## 2. Dated, cheap and premium

### 2.1 What looks dated or cheap in 2026 (and why)

| Tell | Why it reads cheap now |
|---|---|
| All-caps Montserrat Black / Komika with 8–12 px black strokes | the default output of every AI clipping tool since 2023; signals "guru" or "clip farm" before a word is read; all caps is ~24% wider, so fewer words fit and the eye reads shapes slower |
| Yellow + green + red highlights, rainbow keywords | no hierarchy; "rainbow, jittery, or oversized highlights" read as spammy ([Recapo](https://recapo.ai/blog/best-caption-styles-for-shorts/)) |
| Every word bouncing or scaling | the eye adapts within seconds and stops registering motion; entries under 100–150 ms read as frantic (HyperFrames rules 10–12) |
| Emojis attached to captions | the single loudest AI-tool signature; explicitly banned by Dwarkesh's clip brief |
| `bounce`/`elastic` easing | real objects decelerate, they do not boing; HyperFrames forbids them outside a "playful" cluster |
| Heavy blurred drop shadows | "Heavy, blurry shadows look dated" ([Blitzcut](https://blitzcutai.com/blog/best-caption-fonts-tiktok)); a 20 px 80% black halo muddies the footage |
| Solid white pill behind every line | "A white box behind text is a failure of taste" (HyperFrames rule 3) unless it is a deliberate paper card |
| Captions over the face or mouth | fights the subject; the subject should read first (HyperFrames rule 1) |
| Captions in platform UI zones | cut off by the like column, the description or the progress bar |
| Mixing three families (Montserrat + script + serif) | "the #1 amateur tell" (HyperFrames rule 5) |
| Italic used as generic emphasis | on 24–30 fps motion italic reads as tilted, not stressed (HyperFrames rule 8) |
| Whoosh on every cut, pop on every word | "the audience starts hearing the edit instead of the content" ([Luna Bloom](https://blog.lunabloomai.com/video-sound-effects/)) |
| Meme SFX (vine boom, bruh, XP error) | Remotion's own SFX list includes them; never use |
| Glitch transitions as decoration | glitch "hits hardest when it's unexpected"; used by default it is noise |
| Captioning every filler word | "um", "you know", self-corrections on screen look like an unedited transcript |
| Fixed 3-word chunks regardless of speech | fights cadence; chunk on breath and clause |
| Centered text that jitters as words are appended | the hallmark of cheap build-style captions |
| Tracking left at 0 at display size | display sizes want negative tracking; many presets do the opposite (HyperFrames rule 6) |
| Pure #FFFFFF text and pure #000 strokes on graded footage | looks pasted on; warm off-white sits in the image |
| Fake tweet or fake news screenshot cards | reads as clickbait and can imitate real records; show real posts truthfully or set quotes typographically |

### 2.2 What separates premium from amateur (the craft list)

**Typography**

1. One family, two weights. Hierarchy lives in weight (500 → 800) and size (1.3 to 1.6×), not in a second font (HyperFrames rule 5). One sanctioned exception here: a serif italic as a *voice switch*.
2. Tracking tightens with size: −0.015 to −0.035 em at display sizes (> 40 px on a 1080-wide frame), 0 to +0.01 em at body sizes (HyperFrames rule 6). Inter's variable `opsz` axis (14–32) switches to its Display cut automatically at large sizes when `font-optical-sizing: auto` is on ([rsms/inter](https://rsms.me/inter/)).
3. Line height 1.0 to 1.1 for 1–2 line display captions, 1.15 to 1.25 for rail captions; never the browser default 1.2+ on 80 px bold text.
4. Mixed case (sentence case or lowercase). Measured: Inter 800 at 76 px fits 26 mixed-case characters in 936 px against 21 in all caps.
5. Max characters per line: broadcast target is 32 to 42 ([OpusClip](https://www.opus.pro/blog/youtube-shorts-caption-subtitle-best-practices)). For short-form sizes (rec): ≤ 18 at 76 px, ≤ 28 at 58–62 px, ≤ 34 at 54 px in a 936 px measure (1080 minus 72 px margins).
6. Balanced lines, no one-word orphan line: `text-wrap: balance` for 2-line captions; break at clause boundaries, never leave a dangling one-word line (HyperFrames rail rule).
7. Correct typography in the text itself: curly quotes and apostrophes, numerals as digits, tabular figures (`font-variant-numeric: tabular-nums`) for anything that counts, proper names spelled from a dictionary (OpenAI, Anthropic, GPT-5), no em-dashes in on-screen text (a house style rule), filler removed.

**Color and contrast**

8. One saturated accent per video; everything else is neutrals (HyperFrames rule 9). Warm off-white text (`#F4F1EA`, `#F2EFE9`, bone `#F5EFE6`) looks graded into the image; pure white looks pasted on.
9. Contrast without heavy strokes, in this order: (a) soft layered shadow, (b) 2–3 px dark stroke on a duplicated back layer, (c) a narrow scrim sized to the text box at 30–40% opacity, (d) dim the plate locally 10–15%, (e) a paper card as a deliberate design object (HyperFrames rule 3, adapted). Measured: `#F4F1EA` on a mid-grey `#777` background is only 4.5:1 and on `#BBB` 1.7:1, so bright scenes (luma > ~180) always need (c) or (d).
10. Subtle shadow values that work (rec), CSS `text-shadow` on 1080-wide frames:
    - body: `0 1px 2px rgba(0,0,0,.45), 0 4px 16px rgba(0,0,0,.35)`
    - display: `0 2px 4px rgba(0,0,0,.40), 0 8px 28px rgba(0,0,0,.30)`
    - never a single `rgba(0,0,0,.8)` shadow with 20 px blur.
11. Where a stroke is needed, render the text twice: a back copy with `-webkit-text-stroke: 4px rgba(0,0,0,.55)` and a front copy with fill only. The stroke then sits outside the glyph (a 2 px visible stroke) and does not eat counters.

**Layout and placement**

12. Safe zones. TikTok: top ~130 px, bottom ~250 px, sides ~60 px; Reels: top ~108, bottom ~320; Shorts: avoid bottom 10–15% ([Kreatli](https://kreatli.com/guides/safe-zone-guide)); TikTok's right engagement column needs 120–180 px; Postplanify reports it gained 20 px with the January 2026 "Add to Playlist" button and gives a TikTok safe core of 900×1492 ([Postplanify](https://postplanify.com/blog/social-media-safe-zones-2026-complete-guide), [Zeely](https://zeely.ai/blog/tiktok-safe-zones/)). Working box for all three (rec): x 72–1008, y 160–1520; below y = 1100 keep anything critical left of x = 940.
13. Keep the face clear. In a well-framed 9:16 talking head the eyes sit at 32–38% of height and the chin near 55%. Captions live at 60–73% (chin to chest) and move up into the seam when a slide or split layout is used.
14. Bottom-anchor the caption block: fix the baseline of the last line and let a 2-line page grow upward. The eye's landing spot never moves between 1-line and 2-line pages.
15. Optical centering: trim the text box to cap height and baseline with `text-box: trim-both cap alphabetic` (Chrome 133+, so available in Remotion's headless Chrome; [Chrome for Developers](https://developer.chrome.com/blog/css-text-box-trim)). Pills and chips then center visually rather than geometrically. Hang opening quote marks outside the left edge of quote blocks.
16. Letterbox and pillarbox bars are caption real estate. A 16:9 lecture on a 9:16 canvas leaves bars above and below; put the headline in the top bar and captions in the bottom bar (HyperFrames rule 18).
17. Move the caption zone with the shot: close-up → captions lower or to the side; wide shot → classic lower third on the non-subject side (HyperFrames rule 4). Leave looking room: captions go opposite the speaker's gaze ([layout-heuristics.md](https://github.com/heygen-com/hyperframes/blob/main/skills/embedded-captions/references/layout-heuristics.md)).

**Motion**

18. Animate transform and opacity only on caption text. `letter-spacing`, `font-weight` and blur animations reflow inline text and make lines jump (HyperFrames rule 10). Reserve blur for whole-block entrances.
19. Decelerate in, accelerate out. Entrances ease-out, exits ease-in, exits ≈ 60 to 75% of the entrance duration ([HyperFrames motion](https://github.com/heygen-com/hyperframes/blob/main/skills/embedded-captions/modes/standard/_motion.md); [LottieFiles](https://github.com/LottieFiles/motion-design-skill/blob/main/skills/motion-design/SKILL.md) "Enter > Exit: entrances 30–50% longer").
20. Premium motion personality: 350–600 ms, `cubic-bezier(0.4,0,0.2,1)`, 0% overshoot (LottieFiles "Premium" archetype); overshoot at most 3–5% on anything else. Linear's product motion: 200–350 ms, ease-out-expo; Vercel's: 150–250 ms ease-out, almost no springs ([DesignMD](https://www.designmd.co/blog/linear-vs-vercel-motion)).
21. Stagger is the main expressive axis: 40 ms urgent, 80 ms conversational, 150 ms documentary, 250 ms+ poetic (HyperFrames rule 12). With word-level timestamps, drive each word from its own `startMs` and let speech be the stagger.
22. Never double-fade: a container fade times a word fade gives a non-linear curve that "pops" at about 40% (HyperFrames anti-patterns). Fade one layer.
23. Emphasis budget per clip: about 70% plain, 20% slight lift (color or weight, not both), 8% full emphasis, 2% climax (HyperFrames rule 13). At most one emphasized word per page.
24. Break the rhythm once per ~30 s: a phrase from the other side, one word at 2×, a beat with no caption (HyperFrames rule 14).
25. Silence honored: if the speaker pauses ≥ 1.5 s for effect, clear the caption. The irony often lives in that pause.

**Timing**

26. Captions lead speech slightly. Page enters 80–100 ms before its first word (HyperFrames grouping: `in = w[0].start − 0.08 s`); broadcast guidance is 0.1–0.3 s ([OpusClip](https://www.opus.pro/blog/youtube-shorts-caption-subtitle-best-practices)). Human A/V sync tolerance is asymmetric: detection thresholds are +45 ms (audio early) and −125 ms (audio late) per ITU-R BT.1359 ([Wikipedia](https://en.wikipedia.org/wiki/Audio-to-video_synchronization)). A visual that leads the sound by up to ~100 ms feels in sync; one that lags by 100 ms feels late. Rec: page in at −3 f, active-word change at −1 f.
27. Hold: page stays ~0.6 s after its last word unless the next page needs the space; minimum 0.5 s on screen; no overlapping pages.
28. Segment on breath: break at pauses ≥ 250 ms (strong comma) or ≥ 500 ms (breath), at sentence ends, at discourse resets ("but", "so"); cap at 6 words or 2.5 s ([caption-grouping.md](https://github.com/heygen-com/hyperframes/blob/main/skills/embedded-captions/references/caption-grouping.md)).
29. Edit the words: display 70–85% of the transcript; drop filler and self-corrections; keep meaning (HyperFrames rule 15).

### 2.3 Anti-jitter recipes for Remotion

1. **Pre-lay out the whole page.** Render every word of the page from the page's first frame with `opacity: 0` and reveal by opacity/transform. Appending words to a centered line recenters it on every word; that is the jitter.
2. **Measure once.** Use `@remotion/layout-utils` `measureText()` / `fillTextBox()` after `waitUntilDone()` on the font, with exactly the same font properties as the render. Compute line breaks, word rects and the page box once per page, then animate against fixed coordinates.
3. **Reserve bold width.** If the active or spoken word gets heavier, (a) render each word inside a box sized to its boldest state (a hidden bold duplicate via `::after { content: attr(data-text); font-weight: 800; visibility: hidden; height: 0 }`, the [CSS-Tricks technique](https://css-tricks.com/bold-on-hover-without-the-layout-shift/)); or (b) use a font with a grade axis (Roboto Flex `GRAD` −200 to 150 changes apparent weight without changing advance width; [web.dev](https://web.dev/articles/variable-fonts)); or (c) signal activity with color or opacity instead of weight.
4. **Scale from the baseline.** Active-word pops use `transform: scale()` with `transform-origin: 50% 85%` so the word grows up from the baseline instead of dropping below it.
5. **Slide one highlight box.** For the karaoke box, measure each word's rect, then interpolate one absolutely positioned box's `x` and `width` between rects with a critically damped spring (`{damping: 200, stiffness: 400}` settles in ~10 f, 0% overshoot). A new box per word flickers.
6. **Stable page geometry.** Keep line count stable within a preset (prefer always-1 or always-2) and bottom-anchor. Let `text-wrap: balance` choose breaks at layout time, not per frame.
7. **Rest at integer transforms.** At rest, `scale` should be exactly 1 and translations whole pixels; sub-pixel rest positions shimmer when text moves between frames.
8. **Determinism.** No `Math.random()` or `Date.now()`; use Remotion's `random(seed)`. Captions data is whitespace-sensitive: keep the leading space on each token and render with `white-space: pre` ([Remotion docs](https://www.remotion.dev/docs/captions/create-tiktok-style-captions)).

---

## 3. Seven presets for this creator

### 3.1 Shared tokens

**Fonts** (all free for commercial video use):

- **Inter** (SIL OFL, Google Fonts), variable `wght 100–900`, `opsz 14–32`. The house sans. It sits closest to the system Helvetica stack the website uses (`docs/site-brief.md`) and the existing `/clip` skill already burns captions in Inter. Load via `@remotion/google-fonts/Inter` with explicit weights.
- **Instrument Serif** Regular and Italic (OFL). The voice switch. Only at ≥ 64 px vertical or ≥ 52 px landscape.
- **Geist Mono** (OFL, Vercel) only for literal logs and code.
- Alternates if Inter feels too neutral: **Geist** (OFL), **Satoshi** (Fontshare, ITF Free Font License, free for commercial use in video but files may not be redistributed; [Fontshare](https://www.fontshare.com/licenses/itf-ffl)). For a serif with more weights at caption size: **Newsreader** (OFL, opsz 6–72).
- Avoid: Montserrat Black and Anton (the preset look), Komika, Bebas at body size, Playfair at caption size, anything under 500 weight over busy footage, Pangram Pangram fonts (free for personal use only).

**Palettes** (section 4.2 has full values). Every preset references tokens:

- `--text` `#F4F1EA` (warm off-white on footage)
- `--ink` `#111111` (text on paper cards)
- `--paper` `#F4F1EA`
- `--muted` `#A8A39A` (7.5:1 on #111)
- `--accent` one per video, chosen by lane (builder `#8AB4FF`, thinker `#E07A5F`, safety `#FFB23F`, universal `#FF7A4D`), each ≥ 6:1 against #111
- `--accent-ink` the same hue darkened for paper (`#2F4AE0`, `#9E2A2B`, `#9A5B00`, `#C2410C`), each ≥ 4.5:1 on paper

**Easing and springs** (Remotion):

| Token | Remotion | Behavior (computed) | Use |
|---|---|---|---|
| `ease.enter` | `Easing.bezier(0.16, 1, 0.3, 1)` | expo-out, fast then soft landing | most entrances |
| `ease.exit` | `Easing.bezier(0.7, 0, 0.84, 0)` | expo-in | exits |
| `ease.move` | `Easing.bezier(0.65, 0, 0.35, 1)` | in-out cubic | on-screen moves, zooms, highlighter sweeps |
| `ease.calm` | `Easing.bezier(0.45, 0, 0.55, 1)` | symmetric sine-like | reflective fades, crossfades |
| `ease.premium` | `Easing.bezier(0.4, 0, 0.2, 1)` | LottieFiles "premium" | cards, name tags |
| `spring.snap` | `{damping: 24, stiffness: 300}` | ζ 0.69, 4.9% overshoot, t90 151 ms, settles 11 f | hot-take pops |
| `spring.settle` | `{damping: 18, stiffness: 120}` | ζ 0.82, 1.1% overshoot, t90 280 ms, settles 16 f | chips, markers on an axis |
| `spring.glide` | `{damping: 200, stiffness: 170}` | critically damped, t90 299 ms, settles 15 f | word fade-ups |
| `spring.box` | `{damping: 200, stiffness: 400}` | critically damped, t90 195 ms, settles 10 f | karaoke box, odometer digits |
| `spring.soft` | `{damping: 200, stiffness: 60}` | critically damped, t90 503 ms, settles 26 f | reflective entrances |
| avoid | Remotion default `{10, 100, 1}` | ζ 0.5, 16% overshoot, 26 f | reads bouncy |
| avoid | `{damping: 12, stiffness: 300, mass: 0.8}` ("pop" in some rule packs) | ζ 0.39, 27% overshoot | cartoon |

**Durations** (rec): quick 6 f (200 ms), standard 12 f (400 ms), slow 21 f (700 ms); exits 0.6–0.75× the entrance.

**Chunking with `@remotion/captions`.** `createTikTokStyleCaptions({captions, combineTokensWithinMilliseconds, breakOnSilenceAfterMilliseconds})` groups tokens into pages. A low combine value gives word-by-word pages; 1200 ms is the documented recommendation; `breakOnSilenceAfterMilliseconds` (v4.0.514+) starts a new page after a gap ([Remotion](https://www.remotion.dev/docs/captions/create-tiktok-style-captions)). Every preset below gives both values, plus a max-characters rule enforced with `fillTextBox()`. Emphasis words come from a per-clip JSON produced by an LLM pass and checked by hand.

**Global emphasis rule.** At most one emphasized word per page, at most ~20% of pages; emphasize the word that carries the surprise or the claim (a number, a negation such as "never" or "only", a named concept, the contrast term). Never emphasize "AI" by reflex. Numbers are always emphasized when they are the point.

**Global position anchors** (baseline of the caption block's last line):

- 9:16 standard: y = 1380 (71.9%). Split layout (slide on top, speaker below): y = 810 in the seam, or y = 1480 at the bottom if the seam is too tight.
- 16:9: y = 984 (96 px from the bottom, matching HyperFrames `anchor` `bottomPx: 96`), horizontally centered, measure ≤ 1500 px.
- For X and LinkedIn feed uploads of 16:9 clips add +15% size. A 1920-wide frame on a 390 pt phone is scaled to 0.20; a 1080-wide vertical frame to 0.36; the same pixel size therefore appears about 0.56× as large in landscape.

---

### 3.2 VERDICT (hot take)

The hook and one-liner preset. Hormozi's mechanics with none of the noise.

- **Font:** Inter 800, `opsz` auto (Display cut), sentence case.
- **Size:** 76 px (9:16) / 62 px (16:9). Line height 1.02. Tracking −0.025em.
- **Chunk:** 1–3 words. `combineTokensWithinMilliseconds: 550`, `breakOnSilenceAfterMilliseconds: 180`. Max 16 characters per line, max 2 lines (normally 1).
- **Position:** centered, baseline y = 1380 (9:16); y = 960 (16:9). First 3 s of any clip may run this preset at 1.3× size (≈ 100 px) centered at baseline y = 1200 as the hook.
- **Colors:** base `--text #F4F1EA`; emphasis `--accent`. No active-word state (the chunk is the active words).
- **Legibility:** no stroke. `text-shadow: 0 2px 4px rgba(0,0,0,.40), 0 8px 28px rgba(0,0,0,.30)`. On bright plates add a text-box scrim `rgba(12,12,12,.35)`, radius 12, padding 10/18.
- **In:** per chunk, `scale 0.92→1`, `translateY 10→0`, `opacity 0→1` on `spring.snap` (4.9% overshoot, ~11 f), starting at `startMs − 100 ms`.
- **Out:** hard cut to the next chunk (0 f); final chunk of a sentence exits `opacity→0` over 4 f with `ease.exit`.
- **Emphasis:** the emphasized word changes to accent on its own `startMs − 33 ms` and gets `scale 1→1.06→1` over 6 f from the baseline. One per chunk, ≤ 25% of chunks (chunks are short, so the density matches the global 20%-of-pages rule).
- **Emoji:** none. **SFX:** none on captions; one optional low "hit" (−16 dB rel. voice) on the thesis line.
- **Fits:** hot takes, contrarian claims, the first 3 s of other presets. **Avoid** for stories longer than 30 s (fatiguing) and anything sad.

### 3.3 LECTURE (explainer)

The rail. Every word readable; the energy goes into slides, annotations and one takeover.

- **Font:** Inter 600, sentence case. Emphasis words Inter 700 in a reserved-width box.
- **Size:** 58 px (9:16) / 48 px (16:9, ≈ 0.045 × 1080). Line height 1.18. Tracking −0.005em.
- **Chunk:** 4–7 words, full page visible, karaoke fill. `combineTokensWithinMilliseconds: 1400`, `breakOnSilenceAfterMilliseconds: 300`. Max 28 characters per line (9:16), 46 (16:9); max 2 lines.
- **Position:** centered, baseline y = 1400 (9:16) or y = 810 in split layouts; y = 984 (16:9).
- **Colors:** unspoken words `#F4F1EA` at 55% opacity; spoken words 100%; active word 100% plus accent underline 3 px at 0.12 em below baseline (or no underline for the calmest version); technical term emphasis: accent color.
- **Legibility:** scrim sized to the text box, `rgba(10,10,10,.38)`, radius 14, padding 14/22; text shadow `0 1px 2px rgba(0,0,0,.5)`.
- **In:** page `opacity 0→1`, `translateY 8→0` over 7 f (233 ms) `ease.enter`, at first word `startMs − 100 ms`. Each word brightens 55%→100% over 3 f at `startMs − 33 ms`.
- **Out:** page `opacity→0` over 5 f `ease.exit`, only in the gap before the next page.
- **Emphasis:** named concepts and numbers, first mention only; ≤ 1 per page, ≤ 20% of pages.
- **SFX:** none on captions. **Pairs with:** keyword chips, slide zoom, annotations, chapter cards, progress bar.
- **Fits:** explainers, lecture excerpts, anything where a missed word loses the argument.

### 3.4 FIRESIDE (story)

For the run stories and the "here is what happened" clips. Warm, intimate, one serif word as the image.

- **Font:** Inter 500 base, sentence case. Voice-switch words in Instrument Serif Italic 400 at 1.15× size.
- **Size:** 62 px (9:16) / 50 px (16:9). Line height 1.12. Tracking −0.01em (sans), 0 (serif).
- **Chunk:** 3–5 words. `combineTokensWithinMilliseconds: 1100`, `breakOnSilenceAfterMilliseconds: 250`. Max 26 characters per line; 1–2 lines.
- **Position:** centered, baseline y = 1360 (9:16); y = 960 (16:9).
- **Colors:** base `#F4F1EA`; serif word `#FFFFFF` (the font change is the emphasis; no color).
- **Legibility:** `text-shadow: 0 1px 2px rgba(0,0,0,.45), 0 4px 16px rgba(0,0,0,.35)`; no scrim unless luma > 180.
- **In:** per word from its own timestamp: `opacity 0→1`, `translateY 12→0` over 12 f with `Easing.bezier(0.2, 0.7, 0.2, 1)` (HyperFrames "considered confident"). Page pre-laid-out.
- **Out:** whole page `opacity→0` over 8 f `ease.exit`.
- **Emphasis:** Instrument Serif Italic for quoted speech, inner thought ("I thought: *this is fine*"), a named object in the story, or the ironic word. ≤ 1 per 2 pages.
- **SFX:** none. Music optional (section 6).
- **Fits:** anecdotes, Acme and run stories, "the day the agents…" material.

### 3.5 INDEX (list)

For "three failure modes", "five things the judge never saw". The caption is a rail; the structure lives in a persistent item heading.

- **Caption:** Inter 600 60 px (9:16) / 48 px (16:9), same behavior as LECTURE.
- **Item heading:** Inter 700 (Display) 72 px (9:16) / 60 px (16:9), tracking −0.02em, sentence case, ≤ 4 words, left-aligned at x = 72, baseline y = 300 (9:16, under the top safe zone) or top-left x = 96, y = 150 (16:9). Number in tabular figures, accent color, same size, followed by two spaces. No dash between number and title.
- **Progress:** segmented bar under the heading: n segments, 6 px tall, 6 px gaps, width 936, track `rgba(244,241,234,.18)`, fill `--accent`, linear fill over the item's duration.
- **Item change:** old heading `translateY 0→−16`, `opacity→0` over 8 f `ease.exit`; new heading reveals with `clip-path: inset(100% 0 0 0) → inset(0)` plus `translateY 16→0` over 12 f `ease.enter`, starting 4 f after the old one leaves. Number digits roll (odometer) on `spring.box`.
- **Emphasis:** one key noun per item, accent.
- **SFX:** one soft tick (−22 dB rel. voice) at each item change, landing on the frame the new heading settles.
- **Fits:** lists, frameworks, step-by-step explanations.

### 3.6 EPIGRAPH (quote)

For reading a quote: a paper, a public figure, a line from the Nurture Thesis. Serif carries the quoted words; the attribution stays plain.

- **Font:** quoted words Instrument Serif Italic 400; attribution Inter 500.
- **Size:** quote 72 px (9:16) / 56 px (16:9), line height 1.10, tracking −0.01em; attribution 30 px / 26 px at 72% opacity. (No text smaller than 26 px anywhere in the system; small labels read as clutter.)
- **Chunk:** 5–9 words, 2–3 lines. `combineTokensWithinMilliseconds: 2000`, `breakOnSilenceAfterMilliseconds: 450`. Max 30 characters per line (Instrument Serif Italic averages 0.345 em per character; 38 fit in 936 px at 72 px).
- **Position:** left-aligned at x = 96 with the opening quote mark hung at −0.42 em; block vertically centered on the clean side of the frame, or on a paper card (section 4.5).
- **Colors:** on footage `#F2EAD8` with `0 2px 12px rgba(0,0,0,.45)`; on a card `--ink` on `--paper`, opening mark in `--accent-ink`.
- **In:** "etch": each word `opacity 0→1` over 15 f with `ease.calm` from its own timestamp, no movement.
- **Out:** block `opacity→0` over 10 f `ease.exit`.
- **Attribution format:** "Name, year" or "Name, where, year". Every quote is verbatim and logged in `ledger/facts.md`. It gets the `commentary` flag when the speaker is a named AI leader.
- **SFX:** none, or a paper-card slide at −22 dB when a card is used.
- **Fits:** quotes, readings, definitions, a line from an essay.

### 3.7 LEDGER (debate and contrast between people)

For montages that set different people's stances side by side (for example several AI lab CEOs on the same question) and for two-speaker podcast exchanges.

- **Font:** Inter 600 for speech; speaker names Inter 600 at 32 px / 28 px, 65% opacity, sentence case, shown on the first line of each turn only.
- **Size:** 60 px (9:16) / 50 px (16:9). Line height 1.12.
- **Chunk:** 3–5 words. `combineTokensWithinMilliseconds: 1200`, `breakOnSilenceAfterMilliseconds: 250`. Max 24 characters per line; 1–2 lines.
- **Position by speaker:** speaker A left-aligned at x = 72, speaker B right-aligned at x = 1008 (9:16), both on baseline y = 1380; in 16:9, A at x = 120, B right-aligned at x = 1800, baseline y = 984. The side matches where that speaker sits on screen or on the stance axis.
- **Colors:** speaker A `#F4F1EA`; speaker B `#CFD8E6` (cool off-white); the only saturated color is `--accent` for the one word that carries each side's claim. Speaker coding by position and temperature, never red versus green.
- **In:** `translateX ±24→0` from the speaker's side plus `opacity`, 9 f `ease.enter`. **Out:** back toward the same side, 6 f `ease.exit`.
- **Turn change:** J-cut the incoming speaker's audio 6–10 f before the picture (section 5); the caption follows the audio, not the picture.
- **Pairs with:** portrait chips, the stance axis and the quiet "vs" (section 4.7).
- **Fits:** debate, contrast, "who believes what", Q&A. Students in Q&A stay unnamed (people rule 6).

### 3.8 DUSK (calm and reflective)

For the thinker lane: the cave, the Nurture Thesis, endings. The caption behaves like a slow subtitle.

- **Font:** Inter 500, lowercase (the one preset that uses it; lowercase lowers the voice).
- **Size:** 54 px (9:16) / 44 px (16:9). Line height 1.25. Tracking 0.
- **Chunk:** 5–8 words. `combineTokensWithinMilliseconds: 2200`, `breakOnSilenceAfterMilliseconds: 400`. Max 34 characters per line; 2 lines.
- **Position:** centered, baseline y = 1440 (9:16) or in the bottom letterbox bar; y = 990 (16:9).
- **Colors:** `#EDE7DA` at 92% opacity. No emphasis color.
- **Legibility:** `0 1px 12px rgba(0,0,0,.35)`; a 12–18% vignette on the plate is allowed in this preset only.
- **In:** per word from its timestamp, `opacity 0→1` over 18 f (600 ms) with `ease.calm`, or `spring.soft`. No movement.
- **Out:** only in pauses, 12 f `ease.calm`. Clear the caption entirely for pauses ≥ 1.5 s.
- **Emphasis:** none. At most one Instrument Serif Italic word per clip.
- **SFX:** none. Music optional and very low.
- **Fits:** reflective endings, philosophy, slow monologues.

### 3.9 Optional eighth: LOG (overlay, not a caption preset)

Geist Mono 500, 36 px (9:16) / 30 px (16:9), text `#E9ECEF` on a panel `rgba(11,13,16,.78)`, radius 12, padding 24, max 6 lines, left-aligned; typed by string slicing at 1 character per frame (33 ms) with a caret blinking every 530 ms; the panel enters `translateY 12→0` over 9 f. Use only to show real output from a run (rule 1: every piece is a byproduct of something built), never as decoration.

### 3.10 Content → preset map

| Content | Caption preset | Palette | Overlays that fit | SFX per minute | Music |
|---|---|---|---|---|---|
| Hot take | VERDICT | by lane | hook bar, one takeover | ≤ 3 | none |
| Story | FIRESIDE | by lane | name tag, one text-behind-subject | ≤ 2 | optional bed |
| Explainer / lecture | LECTURE | by lane | slide zoom, annotations, keyword chips, chapter cards | ≤ 5 | optional bed |
| List | INDEX | by lane | item headings, progress, counters | ≤ 6 (one per item) | optional bed |
| Quote | EPIGRAPH | Paper or Editorial | quote card | ≤ 1 | none |
| Debate / contrast | LEDGER | Paper or Night Lab | portrait chips, stance axis, quiet "vs" | ≤ 4 | none |
| Calm reflective | DUSK | Editorial | none, or one serif word behind the subject | 0 | optional, very low |

---

## 4. Motion-graphics style system for overlays

### 4.1 Global rules

- **Grid.** 9:16: side margins 72 px; top safe line y = 160; bottom safe line y = 1520; right UI column keep-out x > 940 for y > 1100. Zones: headline y 170–420, face y 400–1100 (keep clear), captions y 1150–1440. 16:9: title-safe 96 px sides, 54 px top and bottom; caption baseline y = 984; lower-third zone y 800–960, left.
- **Type scale (9:16 / 16:9, px).** Takeover 144 / 128. Big number 220 / 180. Chapter title 72 / 64. Hook headline 60 / 52. Caption 54–76 / 44–62. Name 40 / 36. Meta 30 / 26 (floor; nothing smaller).
- **Shape.** One radius (12 px) for scrims, chips and cards. One hairline (2 px at 1080 width, 2 px at 1920 width). No gradients on UI shapes. Cards are flat paper or translucent ink.
- **Shadows.** Card: `0 20px 60px rgba(0,0,0,.35), 0 2px 6px rgba(0,0,0,.20)`. Text: see section 2.2.
- **Motion signature.** Everything enters upward (`translateY +8…+24 → 0`) on `ease.enter`, exits upward or in place on `ease.exit`; only LEDGER moves laterally. Three durations (6/12/21 f). One spring for bounces that are allowed (`spring.snap`, ≤ 5%).
- **Traffic control.** At most one overlay besides captions at a time. When an overlay needs attention, captions yield: dim to 55% (`anchor` theme `yield.dim: 0.55`) or clear if they collide. The plate dims 12–22% and pushes in 1.0→1.012–1.016 while a takeover or text-behind-subject is up (HyperFrames `anchor` plate `dim 0.16, pushIn 0.012`; `terminal` `dim 0.22`).
- **Restraint rule.** The flow stays clean; the big move and any scene effect happen only at the climax, then clear ([HyperFrames motion](https://github.com/heygen-com/hyperframes/blob/main/skills/embedded-captions/modes/standard/_motion.md)). One spent moment per clip.

### 4.2 Palettes

Each lane gets one palette; the neutrals are shared so every clip still looks like one channel. Contrast ratios computed with the WCAG formula.

| Palette | Lane | Ground / plate | Text on footage | Ink / paper | Muted | Accent on dark | Accent on paper | Hairline |
|---|---|---|---|---|---|---|---|---|
| **Paper & Ink** | universal, matches the site | `#111111` | `#F4F1EA` (16.7:1 on #111) | `#111111` on `#F4F1EA` | `#A8A39A` (7.5:1) | signal `#FF7A4D` (7.3:1) | `#C2410C` (4.6:1) | `#D9D4CA` |
| **Slate** | builder (Acme, runs, revenue) | `#0E1116` | `#FFFFFF` (18.9:1) | `#0E1116` on `#FFFFFF` | `#98A2B3` (7.3:1) | periwinkle `#8AB4FF` (9.0:1) | `#2F4AE0` (6.6:1) | `#232834` |
| **Editorial** | thinker (nurture, creativity, the cave) | `#1B1714` | `#F2EAD8` (14.9:1) | `#1B1714` on `#F2EAD8` | `#A8A39A` | clay `#E07A5F` (6.0:1 on #1B1714) | oxblood `#9E2A2B` (6.2:1) | `#C9A36A` gold |
| **Night Lab** | safety (drift, collusion, sandboxes) | `#0B0D10` | `#E9ECEF` (16.4:1) | `#0B0D10` on `#E9ECEF` | `#7D8793` (5.3:1) | amber `#FFB23F` (10.8:1) | `#9A5B00` (4.8:1) | `#232830` |

Notes: amber for safety reads "caution" without alarm red; periwinkle for builder avoids the Hormozi green of money content; the Editorial palette's gold is for hairlines only (it fails as text on cream). Keep saturated accents off faces and skin.

### 4.3 Grain, texture, vignette

- **Grain** makes graphics sit in the footage. Apply it to the final composite (video plus graphics), not to the video alone. Target a fine 35 mm-like grain at the lowest visible setting: overlay blend at 20–30% opacity, or soft light at 30–50% ([WeVideo](https://www.wevideo.com/blog/how-to-use-film-grain), [HolyGrain](https://www.holygrain.com/blog/premium-film-grain-overlay-features-quality-buying-guide/)). HyperFrames plates use grain 5–6 on its scale. In Remotion, generate a seeded noise frame per frame (`@remotion/noise` or a canvas noise layer keyed to `frame`), or loop a licensed grain plate with `mix-blend-mode: overlay`. Platform encoders smear fine grain into blocks and spend bitrate on it: test an upload. Drop grain in 9:16 exports if it causes macroblocking.
- **Paper texture** on cards: 2–3% noise on `#F4F1EA` for a print feel. No fake folds or coffee stains.
- **Vignette:** radial gradient transparent to 55% radius, `rgba(0,0,0,.25–.30)` at the corners, only while the plate is dimmed for an overlay or in DUSK. Never over paper cards.
- **Light leaks** (`@remotion/light-leaks`): skip; they read as wedding vlog.

### 4.4 Name tag (lower third)

- **When:** once per clip, 2–6 s in, after the hook, on a quiet beat. Hold 3.5–4.5 s. Never over the hook.
- **Layout 9:16:** left-aligned at x = 72; name baseline y = 1090, role baseline y = 1134; captions continue below from y = 1180. **16:9:** x = 96; name baseline y = 820, role y = 862; caption rail stays at 984.
- **Type:** name Inter 600 40 / 36 px, tracking −0.01em, `--text`; role Inter 400 30 / 26 px at 72%. "Alex Rivera" without diacritics. Role lines follow the bio tone (no revenue, no "co-founder" flex): for example "builds companies run by AI agents" or "guest lecturer".
- **Accent:** a 2 px vertical hairline in `--accent` to the left of the block, spanning name cap height to role baseline.
- **Motion:** hairline `scaleY 0→1` from the top over 9 f `ease.enter`; name reveals from a mask (`clip-path: inset(0 0 100% 0) → inset(0)` with `translateY 12→0`) over 12 f starting at f 3; role the same over 10 f starting at f 7. Exit: all `opacity→0`, `translateY 0→−6` over 7 f `ease.exit`.
- **Premium because:** no box, mask reveals, aligned to the same margin as captions and headings, appears once.

### 4.5 Hook headline bar ("title card" that stays)

- **Layout 9:16:** top-left block starting at y = 170, x = 72, width ≤ 936, max 2 lines, `text-wrap: balance`. **16:9 (X and LinkedIn uploads):** top-left x = 96, y = 72, 52 px.
- **Type:** Inter 700 (Display) 60 / 52 px, line height 1.06, tracking −0.022em, sentence case. Content follows the cold-reader rule (plain words, one number max, no internal names).
- **Two treatments:** (a) *Paper*: solid `--paper` card, `--ink` text, padding 20/28, radius 12, card shadow. Highest legibility; the DOAC white-box idea in sentence case. (b) *Float*: no card, `--text` with display shadow, used when the headline sits in a letterbox bar.
- **Duration:** persistent for letterboxed lecture clips ≤ 60 s; otherwise first 5–6 s (DOAC's banner is gone by ~5.5 s), then either exit or collapse to a *mini* state (scale 0.62 from the top-left corner, opacity 0.85) over 12 f `ease.move`.
- **Motion:** card `scaleY 0.9→1` from the top plus `opacity` over 10 f `ease.enter`; text lines mask-reveal with a 3 f stagger. Exit 8 f `ease.exit`.
- **SFX:** optional soft whoosh (−20 dB rel. voice), starting 3 f before the card.

### 4.6 Keyword pop-ups and definition cards

- **Chip:** Inter 600 40 / 34 px, padding 12/18, radius 12, background `rgba(17,17,17,.72)`, 1 px border `rgba(244,241,234,.18)`, text `--text`, optional 10 px accent dot. Placed beside the head on the empty side (gaze-opposite): 9:16 y 420–700; 16:9 y 200–400 on the clean side.
- **Definition card (a thinker signature):** term in Instrument Serif 56 / 48 px, part of speech in Instrument Serif Italic at 70%, one-line definition in Inter 400 30 / 26 px, ≤ 12 words. Hold = max(2.0 s, words ÷ 3.5 + 0.8 s).
- **Timing:** appears 100–200 ms before the term is spoken. ≤ 1 per 12–15 s; never with another overlay.
- **Motion:** `scale 0.96→1`, `translateY 8→0`, `opacity` on `spring.snap`; exit 6 f `ease.exit`.
- **SFX:** soft tick (−22 dB) or nothing.

### 4.7 Kinetic typography for key phrases (takeover)

- **Budget:** once per clip (twice in a 90 s clip at most). It is the apex.
- **Setup:** 4–8 f void (captions clear, plate dims 45–60% or cuts to `--ground`), then the words.
- **Type:** Inter 800 (Display) 132–160 px (9:16) / 120–140 px (16:9), tracking −0.035 to −0.045em, line height 0.95, sentence case or lowercase, 2–6 words, left-aligned at the margin or centered. One word may switch to Instrument Serif Italic 400 at 1.1× size: the ironic word.
- **Motion:** built from cuts. Each word appears on its spoken frame, either burned in (0 f) or with a 4 f rise (`yPercent 30→0`, `ease.enter`). Lines stack. Hold ≥ 1.0–1.5 s after the last word (climax dwell ≥ 1 s, HyperFrames). Exit by hard cut back to the speaker on the next sentence.
- **SFX:** silence before, one low soft impact (−14 to −16 dB) on the last word if anything.

### 4.8 The footnote (a signature device for this creator) (rec)

A caption claim gets an asterisk; 1–3 s later a footnote line appears near the bottom of the safe area and qualifies it. Example: caption "it passed every test\*", footnote "\*the tests it wrote itself". This turns the quieter second thread (what an instrument measured versus what it was supposed to measure) into a recurring visual joke without any loudness.

- **Type:** asterisk in `--accent` at caption size; footnote Inter 500 34 / 30 px, `--text` at 85%, left-aligned at x = 72, baseline y = 1500 (9:16) or x = 96, y = 1040 (16:9); a 2 px hairline 120 px long above it.
- **Motion:** hairline draws left→right 8 f `ease.enter`; text fades up 6 px over 9 f. Hold ≥ 2 s. Exit 6 f.
- **Budget:** ≤ 1 per clip. It only works if it is rare.

### 4.9 Quote cards

- **Card:** `--paper`, width 936 (9:16) / 1100 (16:9), padding 56/64, radius 12 (or 0 for a print feel), card shadow, 2–3% paper noise.
- **Type:** EPIGRAPH values (Instrument Serif 64 / 56 px on the card, `--ink`), opening mark in `--accent-ink` hung outside the text block; attribution Inter 500 30 / 26 px in `#4A4A48`.
- **Depth:** the video behind dims 35% and scales 1→0.97 while the card is up.
- **Motion:** card `translateY 40→0` plus `opacity` over 15 f `ease.premium`; text lines fade with a 6 f stagger; hold for words ÷ 3.3 s + 1 s; exit 9 f `ease.exit`.
- **Rules:** verbatim only, sourced in `ledger/facts.md`, `commentary` flag for takes on named AI leaders. Never draw a fake tweet or fake article; if a real post is shown, show a real screenshot with its date.

### 4.10 Number callouts and counters

- **Type:** Inter 800 (Display), `font-variant-numeric: tabular-nums`, 220 px (9:16) / 180 px (16:9), tracking −0.04em; unit or suffix Inter 600 at 0.42× size aligned to the numeral baseline with an 8 px gap; label Inter 500 32 / 28 px below at 72%.
- **Count-up:** 18–36 f (600–1200 ms) on `ease.enter`, landing 1–2 f before the spoken number ends. Count only meaningful digits ("$300k", not $300,000 rolling through every thousand). Odometer roll for small integers (each digit column translates on `spring.box`). Then a 3 px accent underline draws left→right over 8 f.
- **Placement:** clean side, or centered with the plate dimmed 30%.
- **Rules:** any currency figure triggers the `number` flag (rule 5).
- **SFX:** a single soft tick at the landing frame (−20 dB). No per-digit ticks.

### 4.11 Comparison, "vs" and the stance axis

Built for a clip that sets several tech CEOs' stances on AI against each other.

- **Portrait chips:** circles 132 px (9:16) / 104 px (16:9), grayscale (`filter: grayscale(1) contrast(1.05)`), 3 px ring in `--text` at 30%; name Inter 600 34 / 28 px; stance label Inter 400 28 / 24 px, ≤ 4 words, sentence case; optional short verbatim quote in Instrument Serif Italic 34 / 28 px. Photos must be licensed (press kits, Creative Commons with attribution); fall back to typographic monograms (initials in Inter 600 on a `#1A1A1A` disc) when rights are unclear.
- **Stance axis (9:16):** vertical, because the frame is tall: x = 540, y 380→1300, 2 px `--text` at 40%, ticks every 20%. End labels Inter 500 30 px at 70%, neutral and descriptive (for example "slow down" at the top, "speed up" at the bottom; or "open weights" and "closed"). Chips alternate left and right of the axis to avoid collisions. **16:9:** horizontal axis at y = 560, x 240→1680.
- **Motion:** axis draws over 12 f `ease.move`; chips enter in the order they are spoken, each travels from the axis center to its position on `spring.settle` (1.1% overshoot), 120 ms stagger; the stance label fades 6 f after its chip lands. A speaker's chip ring turns `--accent` while that person is on screen.
- **Quiet "vs":** for two-way splits, a 2 px vertical divider with "vs" in Instrument Serif Italic 48 px at 60% opacity, centered on the divider. Never a red "VS" badge.
- **Premium because:** equal visual weight for every person, no good-versus-bad color coding, a date on every stance (stances move), every quote logged, the take flagged as commentary.
- **SFX:** one soft click as each chip lands (−24 dB) or a single sweep for the whole set.

### 4.12 Progress bar

- **Spec:** 6 px (9:16) / 4 px (16:9); track `rgba(244,241,234,.18)`; fill `--accent` at 90%; linear fill (the one place linear easing is correct). Place it under the headline card or at y = 150, inside the safe area, not at the very top edge where platform chrome sits. Segmented for lists (INDEX).
- **Use:** lists and explainers ≥ 45 s. Vendors claim it lifts completion for lists and tutorials ([EchoWave](https://echowave.io/tools/video-progress-bar/)); the evidence is anecdotal. Skip for hot takes, stories and reflective clips.

### 4.13 Chapter and section cards

- **Use:** long segments (10–25 min) and list sections.
- **Type:** number Inter 500 tabular 40 / 36 px in `--accent`; title Inter 700 (Display) 72 / 64 px, ≤ 5 words, left-aligned at the margin, 9:16 y 820–1000.
- **Plate:** dim 55% or blur the video 12 px behind the card.
- **Motion:** mask-up reveal 12 f `ease.enter`; hold 1.2–1.8 s; exit 8 f `ease.exit`. J-cut the next section's audio in 6–10 f before the card exits.
- **SFX:** optional soft low thump or paper slide (−18 dB).

### 4.14 Text behind subject

- **Budget:** once per clip, on the apex word. Single speaker, steady framing, no hard cut during the effect.
- **Pipeline:** precompute a person matte as an alpha video (MediaPipe selfie segmentation, RVM, `rembg` u2net_human_seg, BiRefNet, or SAM 2/3 for hard cases). HyperFrames found `u2net_human_seg` best for caption layering because it drops thin furniture such as mic booms; BiRefNet was best semantically but ~7 s per frame on CPU. Composite in Remotion as three layers: `<OffthreadVideo>` background, the text, then the matte video with `transparent` (ProRes 4444 or VP9 WebM with alpha).
- **Type:** Inter 800 (Display) 300–420 px (9:16), tracking −0.045em, `--text` at 92% or `--accent`; or Instrument Serif Italic for the thinker lane. The word must be wide enough to read around the body: width > subject width + 400 px (HyperFrames). Check that ≥ 50% of each letter stays visible.
- **Plate:** dim 16% outside the subject; contact shadow under the letters optional.
- **Motion:** rise `yPercent 48→0` over 27 f with `Easing.bezier(0.215, 0.61, 0.355, 1)` (power3.out) or a wipe-up; dwell ≥ 1 s; exit fade 12 f. Rail captions dim to 55% during.

### 4.15 Annotations on slides (highlight, underline, circle, arrow)

- **Highlighter:** rectangle behind the phrase, `--accent` at 38% alpha, `mix-blend-mode: multiply` on light slides or `screen` on dark slides, height 0.9× line height, skew −1°, radius 3 px, `scaleX 0→1` from the left over 10–14 f `ease.move`, starting 3–6 f before the phrase is spoken. (Remotion's skill ships a highlighter-pen word example.)
- **Underline:** SVG path, 6 px stroke at 1080-wide scale, round caps, a seeded hand wobble (roughjs or perfect-freehand with a fixed seed), `stroke-dashoffset` draw over 12 f `ease.calm`.
- **Circle:** hand-drawn ellipse rotated −4°, the stroke overshoots its start by 10–15°, draw 16–20 f.
- **Arrow:** shaft draws 12 f, head appears in the last 3 f.
- **Color:** one accent. Red circles only on the Paper palette (as `--accent-ink`).
- **Budget:** ≤ 1 annotation visible at a time, ≤ 3 per slide; all clear with a 6 f fade on slide change.
- **Sound:** a marker scratch at −26 dB is allowed and suits the ironic register; one per annotation at most.

### 4.16 Zoom-to-slide callouts

- **Move:** scale the slide layer 1→1.6–2.2 with a translate to the region's center over 18–27 f (600–900 ms) `ease.move`; hold while discussed; return over 15 f.
- **Spotlight (optional):** dim outside the region 45% with a rounded-rect mask, radius 16, 24 px feather.
- **Crispness:** render slides from the source deck (PDF to SVG, or PNG at 2–3× the target) so text stays sharp at 2× zoom. Never zoom a video recording of a projected slide past 1.3×.
- **9:16 lecture layout:** slide top (1080×608, y 180–788), speaker crop below (y 820–1520), captions in the seam at y ≈ 810 or at the bottom anchor. The headline, if any, goes above the slide.
- **SFX:** soft air whoosh (−22 dB) on zoom-in only.

### 4.17 End card

- **Duration:** 1.5–2.5 s. Either the last frame dimmed 60% or a full `--paper` card.
- **Content:** one line of Inter 700 56 / 48 px saying where the full thing lives ("The full lecture is on YouTube" or "The essay is linked in the first reply", per rule 12), plus the handle in Inter 500 30 / 26 px. No "like and subscribe".
- **Motion:** fade from the last frame over 12 f `ease.calm`; text rises 8 px over 12 f.
- **Loop option for Shorts:** end on a line that flows into the first line of the clip and cut hard, no card.
- **Audio:** music (if any) resolves; no SFX.

### 4.18 Cohesion checklist

1. One sans (Inter), one voice-switch serif (Instrument Serif Italic), mono only for real logs.
2. One accent per video from the lane palette; shared neutrals across all lanes.
3. One easing signature (`ease.enter` / `ease.exit`), three durations, one allowed spring.
4. One radius (12), one hairline (2 px), one shadow family.
5. Everything aligns to the same margins (72 px / 96 px).
6. Everything enters upward; lateral motion only for LEDGER.
7. One overlay at a time; captions yield.
8. One spent moment per clip (takeover, text behind subject, or footnote).
9. Grain over the whole composite so graphics live in the footage.
10. The same name tag, headline bar and end card on every clip; variety comes from content, not from new templates.

---

## 5. Transition and camera-motion grammar

### 5.1 Default: hard cuts on breath

- Hard cut is the default transition. Trim ~0.2 s into the end of the previous line to kill dead air ([Jupitrr](https://jupitrr.com/how-to/edit-talking-head-videos)), but keep 300–700 ms after a claim or a dry line: for this speaker the pause is often the joke.
- Crossfades only for time passage (≥ 12 f) and into the end card. No dip to black or white mid-clip.
- Speed: 1.0–1.08× (pitch-preserved) for lectures, where credibility matters. Dwarkesh reports 1.10–1.25× helps retention on X clips of podcast conversations ([dwarkesh.com](https://www.dwarkesh.com/p/clips-competition)).

### 5.2 Punch-ins and pushes

- **Punch-in (hard):** 1.00→1.12 on a sentence boundary for emphasis; alternate 1.00 and 1.12 across jump cuts so cuts read as camera changes. Guides quote 115–125% or 115–135% for talking heads ([Valmera](https://valmera.io/tools/add-zoom-effects), [EchoWave](https://echowave.io/tools/zoom-video/)); for this register stay at the low end.
- **Smooth push:** 1.00→1.05 over 2–4 s with `ease.calm` while a thought builds, then a hard cut back to 1.00 at the next section ("gently eased zoom and a hard cut back", [Jupitrr](https://jupitrr.com/how-to/edit-talking-head-videos)). Smooth zooms take 10–20 f when used as a move; snappy punches 3–6 f (EchoWave).
- **Resolution ceiling:** a 9:16 crop from a 1080p 16:9 source is already a 1.78× upscale (608×1080 → 1080×1920). Add at most 1.08–1.10 on top, or record lectures in 4K, which allows 1.5× in 9:16 before softening.
- **Framing in 9:16:** face centered at x = 540 ± 60, eyes at 32–38% of height, headroom 8–12%.
- Reserve punch-ins for the hook, an emotional line, a punchline, a section change, or a point to sit with. Emphasis comes from contrast: "subtle, infrequent zooms might suit long-form educational content" ([Opus](https://www.opus.pro/blog/best-auto-zoom-in-tools)).

### 5.3 Cadence: how often something changes

- 2026 short-form guides range from "a visual change every 1.5–2 s" to "one pattern interrupt every 3–5 s" (for example [Joyspace](https://joyspace.ai/pattern-interrupt-reset-attention-span) and [Edicion Video Pro](https://edicionvideopro.com/en/editing-for-platforms-video-marketing/pattern-interrupts-tiktok-retention-guide/)); none of them cite controlled data. The DOAC breakdown measured a cut every 4.1–6.3 s (2.5–3 s near the payoff, ~5.1 s on emotional material) with no holds longer than ~12 s ([PandaStudio](https://www.writepanda.ai/blog/how-diary-of-a-ceo-edits-podcast-clips/)).
- **For this creator (rec):** something visual changes every 3–6 s (a cut, a punch level, a slide, an overlay, a b-roll insert); tighten to 2–3 s only for the 5–10 s before the payoff; allow holds up to 8–10 s on a strong line; add b-roll or a slide when two sentences pass with nothing changing ([Jupitrr](https://jupitrr.com/how-to/edit-talking-head-videos)). A caption page change does not count as a visual change. The 1.5 s cadence reads frantic for an AI-literate audience.
- Alternate calm stretches with short clusters of cuts: intensity then recovery ([AIR Media-Tech](https://air.io/en/youtube-hacks/advanced-retention-editing-cutting-patterns-that-keep-viewers-past-minute-8)).

### 5.4 Named transitions

| Transition | Spec (30 fps) | When | Budget |
|---|---|---|---|
| Match cut | cut on the same gesture, framing or word | best transition in the kit; for a CEO montage, cut between speakers on the same word ("safety", "AGI") | as many as the material gives |
| J-cut | incoming audio leads picture by 6–12 f (200–400 ms) | speaker changes, section starts; "a J cut every 3–4 exchanges" in dialogue ([CutFast](https://cutfa.st/en/blog/j-cut-l-cut-audio-transition-editing-cutfast-method-2026)) | default for turns |
| L-cut | outgoing audio trails 6–15 f over the new picture | reactions; DOAC cuts to the listener for 1–1.5 s while the speaker continues | frequent in podcasts |
| Whip pan | 8 f total (4 out, 4 in); `translateX` 0→−35% out on `ease.exit`, +35%→0 in on `ease.enter`; directional blur peaking 60–80 px at the cut (tutorials: 8 f at 24 fps, 20 f at 60 fps) | change of place or source (lecture hall → podcast studio) | ≤ 1 per clip |
| Zoom blur | 10 f; outgoing scale 1→1.25 with radial blur, incoming 1.25→1 | "going into" a slide or screen | ≤ 1 per clip |
| Glitch | 3–6 f, RGB split 4–8 px, 2–3 clip-path slices, `steps()` easing | only when the content is about corruption or failure (a model breaking, a measurement that lied) | ≤ 1 per clip; never in safety-lane clips about real incidents; never as hook decoration |
| Crossfade | ≥ 12 f `ease.calm` | time passage, end card | rare |
| Light leak, flash, spin, cube | none | never | 0 |

In Remotion, cuts are sequence boundaries; transitions use `<TransitionSeries>` with `linearTiming` or `springTiming`; overlay effects at a cut use `<TransitionSeries.Overlay>` so the timeline does not shorten (Remotion skill `transitions.md`).

### 5.5 Camera-motion extras

- A slow drift (scale 1.00→1.01 plus 4–6 px translate over 5 s, `ease.calm`) can keep a locked-off lecture shot alive. No simulated handheld shake.
- Plate punch on the apex: 1.0→1.016 decaying over ~10 f (HyperFrames `terminal` `punch 0.016, punchDecay 10`). Only at the climax.

---

## 6. Sound design

### 6.1 Levels

| Element | Level | Source |
|---|---|---|
| Final mix, social | −14 LUFS integrated, true peak ≤ −1 dBTP | [Pure Audio Insight](https://pureaudioinsight.com/blogs/content-production/perfect-youtube-audio-levels-creators-technical-guide), [Luna Bloom](https://blog.lunabloomai.com/video-sound-effects/) |
| Dialogue | normalized around −14 LUFS; short-term −14 to −12 LUFS while speaking (rec, consistent with the −14 target) | [Zella](https://zellahq.com/blog/music-ducking-explained/) |
| Music bed under speech | 18–25 dB under voice (≈ −24 to −20 LUFS short-term against −14 LUFS speech); W3C asks ≥ 20 dB for non-speech under speech; ducking is a 70–85% reduction, not a mute | [Pure Audio Insight](https://pureaudioinsight.com/blogs/content-production/background-music-volume-how-loud-should-it-be), [Zella](https://zellahq.com/blog/music-ducking-explained/) |
| Music in gaps / intro | rise 6–8 dB above the ducked level, still ≥ 10 dB under the next line | rec |
| SFX (whoosh, transition) | −18 to −12 dB relative to the dialogue reference | [Pixflow](https://pixflow.net/blog/cinematic-whoosh-sound-effects/) |
| SFX (UI tick, click, pop) | −24 to −20 dB rel. (quieter than whooshes) | rec |
| SFX (impact, low hit) | −16 to −12 dB rel., rare | rec |

EQ: carve 2–4 kHz on the music bus by 3–6 dB so speech stays clear without pulling the bed down further ([Pure Audio Insight](https://pureaudioinsight.com/blogs/content-production/background-music-volume-how-loud-should-it-be)); high-pass SFX around 80–120 Hz unless the low end is the point.

### 6.2 Ducking

- Sidechain compressor on the music keyed by voice: ratio 3:1 to 4:1, attack 10–20 ms, release 100–300 ms, threshold for 3–5 dB of gain reduction (consensus of mixing guides such as [Unison](https://unison.audio/side-chain-compression/)). Zella's rule of thumb: duck fast when speech starts (attack under ~300 ms) and release slower, so the swell breathes instead of pumping ([Zella](https://zellahq.com/blog/music-ducking-explained/)). With the bed already −20 dB under voice, gentle ducking suffices.
- In Remotion, duck deterministically from the transcript: `<Audio volume={(f) => …}>` where the volume interpolates down over 150 ms before each speech segment and back up over 400–600 ms after it, using word timestamps. No real-time sidechain needed.

### 6.3 SFX pairings

| Visual event | Sound | Level (rel. voice) | Timing |
|---|---|---|---|
| Caption word or page | none | n/a | never |
| Hook headline in | soft air whoosh, 250–400 ms | −20 dB | starts 3 f before the card |
| Keyword chip / definition card | soft tick or nothing | −22 dB | on the frame it appears (or 1 f early) |
| Number count-up landing | single soft tick or "tock" | −20 dB | on the landing frame |
| List item change | soft tick | −22 dB | on the settle frame |
| Chapter card | low soft thump or paper slide | −18 dB | on the reveal |
| Quote card | paper slide or nothing | −22 dB | on the card rise |
| Zoom-to-slide | airy whoosh matching the move | −22 dB | peak at mid-move |
| Whip pan | whoosh | −16 dB | starts 3–4 f before the cut, peaks on the cut |
| Glitch | short digital crunch 100–200 ms | −18 dB | on the glitch frames |
| Takeover / text behind subject | silence before; one low impact at most | −16 to −14 dB | impact on the last word's frame |
| Annotation draw | marker scratch (optional) | −26 dB | with the stroke |
| Footnote | nothing | n/a | the silence is the joke |
| End card | none; music resolves | n/a | n/a |

Timing rules: whooshes lead the visual by 2–4 f so the peak lands on the event; impacts sit exactly on the landing frame; risers end 1 f before the reveal.

### 6.4 Density

- "Overusing sound effects is worse than using none"; reserve them for the 3–5 most important beats per video ([EseCut](https://esecut.com/blog/sound-effects-that-boost-engagement)). DOAC clips use none ([PandaStudio](https://www.writepanda.ai/blog/how-diary-of-a-ceo-edits-podcast-clips/)).
- **For this creator (rec):** 0–4 SFX per minute; lists may reach one per item. None under the first spoken words of the hook. Never the Remotion meme set (vine boom, bruh, XP error). If a sound would make someone look up from reading the caption, cut it.

### 6.5 Music

- **Default: no music** for lecture and podcast clips. The speech is the content; the tech and AI audience reads a bed as marketing. Use a bed for explainers, lists and some stories.
- **Genres that fit (rec):** sparse ambient electronic with a slow pulse (Tycho, Boards of Canada, Jon Hopkins adjacent); felt or prepared piano in the modern-classical vein (Nils Frahm adjacent); soft modular or synth arpeggios for builder-lane explainers; tape and drone textures for safety-lane clips (tension without threat); a brushed jazz trio for ironic stories. Tech-explainer libraries describe the target well: ambient synths, steady pulses, subtle textures, no strong melody ([Melody Loops](https://www.melodyloops.com/music-genres/high-tech/), [Audiobello](https://medium.com/@audiobello/what-is-the-right-background-music-for-a-explainer-video-178b3bc21375)).
- **Musical constraints:** 70–100 BPM, no vocals, sparse in 1–4 kHz, modal or minor-leaning but not sad, no big swells under speech, loops cut on phrase boundaries, ends on a resolved chord at the end card.
- **Avoid:** corporate ukulele and claps, trap and phonk, epic trailer drums, motivational piano swells, lo-fi hip-hop beats (the "study with me" signature), trending platform sounds (rights and tone).
- **Sources:** a licensed library, or bespoke beds from ElevenLabs music generation (the MCP is already connected in this environment), which avoids Content ID claims.

---

## 7. Remotion implementation notes

1. **Data:** ElevenLabs word timestamps → `Caption[]` (leading spaces kept) → per-preset `createTikTokStyleCaptions()` with the preset's `combineTokensWithinMilliseconds` and `breakOnSilenceAfterMilliseconds` → post-pass that enforces max characters per line with `fillTextBox()`, moves breaks to clause boundaries, removes filler, then attaches emphasis flags from `emphasis.json`.
2. **Fonts:** `@remotion/google-fonts/Inter` (`loadFont("normal", {weights: ["400","500","600","700","800"], subsets: ["latin"]})`) and `@remotion/google-fonts/InstrumentSerif` (normal and italic); measure only after `waitUntilDone()`.
3. **Layout:** compute page geometry once (`measureText`), store word rects, bottom-anchor the block, reserve bold widths.
4. **Timing:** drive motion with `interpolate()` plus `Easing.bezier()` over explicit frame ranges; use `spring()` only for pops, chips and boxes; remember that ζ ≥ 1 collapses to critical damping in Remotion.
5. **Page lead:** start each page's `<Sequence>` 3 f before its first token; switch the active word at `fromMs − 33 ms`.
6. **Layers (bottom to top):** video plate (with punch/push transforms) → plate dim/vignette → text-behind-subject text → matte video → overlays → captions → grain over everything.
7. **Transparent matte:** `<OffthreadVideo transparent>` with ProRes 4444 or VP9 alpha.
8. **Audio:** voice at −14 LUFS; music `<Audio volume={duckFromTranscript}>`; SFX as `<Audio>` in `<Sequence>` offsets per section 6.3.
9. **Determinism:** `random(seed)` for grain and hand-drawn wobble; no wall-clock values.
10. **QA pass before review:** the checklist in section 8, then render three frames per clip (20%, 50%, 80%) to check faces, safe zones and caption collisions.

---

## 8. Premium-versus-cheap review checklist

A clip passes when every answer is yes.

1. Does the subject read before the caption?
2. Is the text mixed case (except DUSK lowercase), one family plus at most one serif voice switch, two weights?
3. Is there one accent color, used on ≤ 1 word per page and ≤ 20% of pages?
4. No emojis, no rotation, no bounce or elastic easing, no word-by-word scaling on every word?
5. No stroke thicker than a 2 px visible outline; shadows soft and layered?
6. Warm off-white text, not pure white on pure black stroke?
7. Captions inside x 72–1008, y 160–1520, clear of the face and the right UI column?
8. Nothing jitters: pages pre-laid-out, bold width reserved, baseline anchored?
9. Pages lead speech by ~100 ms, hold ~0.6 s, never cross a breath break?
10. Filler removed; 70–85% of words shown; no `[laughs]`?
11. Entrances 200–450 ms decelerating, exits shorter and accelerating?
12. At most one overlay besides captions on screen at any time?
13. Exactly one spent moment (takeover, text behind subject or footnote)?
14. A visual change every 3–6 s, no hold over ~10 s, no 1.5 s strobe cadence?
15. At most one whip, zoom blur or glitch, each motivated?
16. SFX 0–4 per minute, none on captions, levels 12–24 dB under voice?
17. Music absent or ≥ 18–20 dB under speech and ducked?
18. Every quote verbatim and logged, every currency figure flagged, no private person named?
19. Grain applied to the whole composite? Does the export survive platform compression?
20. Would Dwarkesh's clip editor call any of it "cringe popping text"? If yes, remove it.

---

## Sources

Caption styles and trends
- [Ascynd: Hormozi captions, exact specs](https://ascynd.io/en/blog/hormozi-captions)
- [Sendshort: Hormozi captions guide](https://sendshort.ai/guides/hormozi-captions/)
- [Blitzcut: TikTok caption fonts](https://blitzcutai.com/blog/best-caption-fonts-tiktok) · [Best fonts for video editing 2026](https://blitzcutai.com/blog/best-fonts-for-video-editing-2026) · [TikTok caption styles 2026](https://blitzcutai.com/blog/best-caption-style-tiktok)
- [Submagic: MrBeast captions](https://www.submagic.co/blog/how-to-make-captions-like-mrbeast) · [Ali Abdaal captions](https://www.submagic.co/blog/make-captions-like-ali-abdaal) · [Iman Gadzhi captions](https://www.submagic.co/blog/how-to-make-captions-like-iman-gadzhi) · [Templates API](https://docs.submagic.co/api-reference/templates)
- [Sendshort: Ali Abdaal captions](https://sendshort.ai/guides/ali-abdaal-captions/)
- [Opus Clip brand templates](https://help.opus.pro/api-reference/brand-template) · [Caption strategy, 13.5M clips](https://www.opus.pro/research/best-caption-strategy-short-form) · [YouTube Shorts caption best practices](https://www.opus.pro/blog/youtube-shorts-caption-subtitle-best-practices) · [TikTok caption best practices](https://www.opus.pro/blog/tiktok-caption-subtitle-best-practices) · [Auto-zoom tools](https://www.opus.pro/blog/best-auto-zoom-in-tools)
- [Joyspace: Hormozi style in 2026](https://joyspace.ai/hormozi-editing-style-2026-analysis) · [Pattern interrupts](https://joyspace.ai/pattern-interrupt-reset-attention-span)
- [FontMirror: typography trends in short-form AI video](https://www.fontmirror.com/en/typography-trends-shaping-short-form-ai-video-content/)
- [Recapo: best caption styles 2026](https://recapo.ai/blog/best-caption-styles-for-shorts/)
- [OpenClip: caption styling guide](https://openclip.app/guides/caption-styling-guide)
- [Conbersa: podcast clip captioning](https://www.conbersa.ai/learn/podcast-clip-captioning-best-practices)
- [videocaptions.ai: karaoke style](https://www.videocaptions.ai/caption-styles/karaoke) · [EchoWave animated captions](https://echowave.io/tools/animated-captions/) · [EchoWave progress bar](https://echowave.io/tools/video-progress-bar/) · [EchoWave zoom](https://echowave.io/tools/zoom-video/)
- [PandaStudio: how Diary of a CEO edits clips](https://www.writepanda.ai/blog/how-diary-of-a-ceo-edits-podcast-clips/)
- [Dwarkesh Patel: clips competition guidelines](https://www.dwarkesh.com/p/clips-competition)
- [A Type of Amigo: why Instrument Serif is everywhere](https://atypeofamigo.com/outstanding-fonts-why-is-instrument-serif-conquering-the-world/)
- [Kapwing: aesthetics for 2025](https://www.kapwing.com/resources/aesthetics-for-2025-colors-fonts-and-design-trends-for-video/)
- [tscaps: text behind person](https://tscaps.io/blog/text-behind-person-effect)

Caption design systems and motion references
- HeyGen HyperFrames embedded captions: [CATALOG.md](https://github.com/heygen-com/hyperframes/blob/main/skills/embedded-captions/CATALOG.md), [aesthetic-principles.md](https://github.com/heygen-com/hyperframes/blob/main/skills/embedded-captions/references/aesthetic-principles.md), [anti-patterns.md](https://github.com/heygen-com/hyperframes/blob/main/skills/embedded-captions/references/anti-patterns.md), [motion-vocabulary.md](https://github.com/heygen-com/hyperframes/blob/main/skills/embedded-captions/references/motion-vocabulary.md), [rail.md](https://github.com/heygen-com/hyperframes/blob/main/skills/embedded-captions/references/rail.md), [caption-grouping.md](https://github.com/heygen-com/hyperframes/blob/main/skills/embedded-captions/references/caption-grouping.md), [layout-heuristics.md](https://github.com/heygen-com/hyperframes/blob/main/skills/embedded-captions/references/layout-heuristics.md), [_motion.md](https://github.com/heygen-com/hyperframes/blob/main/skills/embedded-captions/modes/standard/_motion.md), [captions and talking heads](https://hyperframes.heygen.com/prompting/captions-and-talking-heads)
- [LottieFiles motion-design skill](https://github.com/LottieFiles/motion-design-skill/blob/main/skills/motion-design/SKILL.md)
- [DesignMD: Linear vs Vercel motion](https://www.designmd.co/blog/linear-vs-vercel-motion)
- [snapcn: Remotion kinetic typography](https://snapcn.dev/remotion-kinetic-typography)
- [DEmotion: text animation secrets](https://trydemotion.com/blog/text-animation-secrets)

Remotion
- [createTikTokStyleCaptions()](https://www.remotion.dev/docs/captions/create-tiktok-style-captions) · [spring()](https://www.remotion.dev/docs/spring) · [spring-utils.ts source](https://github.com/remotion-dev/remotion/blob/main/packages/core/src/spring/spring-utils.ts) · [display-captions skill rule](https://github.com/remotion-dev/skills/blob/main/skills/remotion-best-practices/remotion-captions/display-captions.md)

Layout, type and web techniques
- [Kreatli safe zone hub](https://kreatli.com/guides/safe-zone-guide) · [Zeely TikTok safe zones 2026](https://zeely.ai/blog/tiktok-safe-zones/) · [Postplanify safe zones](https://postplanify.com/blog/social-media-safe-zones-2026-complete-guide)
- [CapCut: vertical subtitle placement](https://www.capcut.com/create/vertical-video-subtitles-placement-tips)
- [Chrome: text-box-trim](https://developer.chrome.com/blog/css-text-box-trim) · [CSS-Tricks: bold without layout shift](https://css-tricks.com/bold-on-hover-without-the-layout-shift/) · [web.dev: variable fonts (GRAD)](https://web.dev/articles/variable-fonts) · [Chrome: text-wrap balance](https://developer.chrome.com/docs/css-ui/css-text-wrap-balance)
- [Inter](https://rsms.me/inter/) · [Geist on Google Fonts](https://fonts.google.com/specimen/Geist+Mono) · [Fontshare ITF license](https://www.fontshare.com/licenses/itf-ffl)
- [Audio-to-video synchronization (ITU-R BT.1359)](https://en.wikipedia.org/wiki/Audio-to-video_synchronization)

Editing, transitions and sound
- [Jupitrr: editing talking-head videos](https://jupitrr.com/how-to/edit-talking-head-videos) · [AIR Media-Tech: retention editing](https://air.io/en/youtube-hacks/advanced-retention-editing-cutting-patterns-that-keep-viewers-past-minute-8) · [Valmera zoom](https://valmera.io/tools/add-zoom-effects)
- [Whip pan tutorials (tutvid)](https://tutvid.com/premiere-pro/whip-pan-blurring-transition-effect-premiere-pro/) · [xeremy whip pan in Resolve](https://xere.my/tutorials/whip-pan-transition/)
- [CutFast: J and L cuts](https://cutfa.st/en/blog/j-cut-l-cut-audio-transition-editing-cutfast-method-2026) · [Videomaker: transitions that aren't cheesy](https://www.videomaker.com/how-to/editing/editing-technique/6-video-transitions-that-arent-cheesy/)
- [Pure Audio Insight: music level](https://pureaudioinsight.com/blogs/content-production/background-music-volume-how-loud-should-it-be) · [YouTube levels](https://pureaudioinsight.com/blogs/content-production/perfect-youtube-audio-levels-creators-technical-guide)
- [Pixflow: whoosh levels](https://pixflow.net/blog/cinematic-whoosh-sound-effects/) · [Luna Bloom: sound effects guide 2026](https://blog.lunabloomai.com/video-sound-effects/) · [EseCut: SFX that make shorts feel professional](https://esecut.com/blog/sound-effects-that-boost-engagement) · [Unison: sidechain compression](https://unison.audio/side-chain-compression/)
- [WeVideo: film grain](https://www.wevideo.com/blog/how-to-use-film-grain) · [HolyGrain: premium grain](https://www.holygrain.com/blog/premium-film-grain-overlay-features-quality-buying-guide/)
- [Melody Loops: high-tech music](https://www.melodyloops.com/music-genres/high-tech/) · [Audiobello: explainer music](https://medium.com/@audiobello/what-is-the-right-background-music-for-a-explainer-video-178b3bc21375)
