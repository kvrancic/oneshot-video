# Open-source clippers, reframers, caption engines and agent skills for talking-head video (survey, 2026-09-27)

Purpose: inform a Claude Code skill that turns long talks and lectures into short vertical clips and edits talking-head recordings. It has to beat everything below. Every project listed was read from source (shallow clones under `scratchpad/ref/` and `scratchpad/ref/skillsC/`, or `gh api repos/.../contents/...`). Stars, licences and push dates come from the GitHub API on 2026-09-27. Verbatim excerpts carry their repo and file path; AGPL and noncommercial sources are marked "ideas only".

Coverage: about 60 repositories, of which about 45 were read in depth. They fall into four groups. The reference skill `mariagorskikh/talking-head-reel` is in Part 1. Fourteen end-to-end "long video to shorts" apps are in Part 2. About twenty-five agent skills and agent-first editors are in Part 3. Fourteen renderers, caption engines, reframers and cut engines are in Part 4.

Machine facts that shape the rendering choice (checked on this Mac): Apple M3 Pro, 36 GB RAM, Node 24.9, Homebrew ffmpeg 8.0_1 built with libass, harfbuzz, freetype, vidstab and VideoToolbox, `whisper-cli` (whisper.cpp) installed, no openai-whisper, no mlx-whisper, no ImageMagick.

## Safety first: the category attracts malware

- `yukitorido/short-video-generator-AI` (722 stars in four days, created 2026-09-23) is a loader. `main.py` imports `src/fs.py`, which decodes XOR-obfuscated module names, decrypts a blob and passes it to `exec()` at import time. The rest is unrelated stolen code; its "score" returns `random.uniform(20, 90)`. Do not install.
- `obi19999/smart-video-reframe` points every download link at a zip inside `src/utils/` and tells users to run an `.exe` or `.dmg`. This is the common GitHub lure pattern. Not opened.
- `NovaTaleRise/clip-studio-ex-nexus` and `Trianglezichopper/submagic-core` (200+ stars each, created the same day, zero forks) show the same star-farm pattern. Not opened.
- Consequence for the skill: it must never tell the agent to fetch a reframer or caption tool from a random repo at run time. Everything it runs is vendored, pinned or from a known publisher.

## Commercial benchmark

Opus Clip (the product every open-source clipper names) ships ClipAnything (visual, audio and sentiment cues for moment finding), ReframeAnything (subject tracking to 9:16), a 0 to 100 Virality Score, animated captions with keyword highlighting and AI B-roll ([Opus Clip help](https://help.opus.pro/docs/article/virality-score), [datastudios](https://www.datastudios.org/post/opus-clip-clipanything-video-repurposing-virality-scoring-and-pricing)). An independent 2026 test found that 20 to 40 percent of generated clips get discarded, with three failure modes: contextually incomplete moments, caption drift and inappropriate reframing; no published data supports the Virality Score's predictive accuracy ([BIGVU](https://bigvu.tv/blog/opus-clip-tested-2026-where-ai-wins-40-percent-discard/)). Those three failure modes are also the three weakest areas of the open-source field.

## (a) The best ideas worth stealing

Selection (finding the clip):
1. **Two-pass windowed selection.** Score every ~90 s window 0 to 100 with a "2-second test", take the global top N, then detail clips inside the shortlist with STANDS ALONE and DIVERSITY rules; a floor-recovery call when too few clips survive. One call over the whole transcript clusters picks near the start (measured by the author). `mutonby/openshorts` `gemini_worker.py`, `clip_selection.py` (MIT).
2. **Quote, never timestamp.** The model returns `quoteStart`/`quoteEnd` copied verbatim; code reverse-matches them onto word timings. `xixihhhh/hotclip` `src/core/highlight/prompt.ts`, `match.ts` (AGPL, ideas only). Equivalent contracts: decisions reference transcript `word_ids` only (`cuixiangyu789-gif/SmartCut`); start/end must equal a word's `s`/`e` (`fralapo/clippyme`); text search in the recognised transcript (`modelscope/FunClip`).
3. **A hard gate before any score** ("merely pleasant, well-spoken or on-topic is NOT a clip"), then five 1-20 axes (hook, payoff, quotability, self-contained, density), plus title grounding: "Exaggerate the FRAMING, never invent the EVENT". `fralapo/clippyme` `gemini_request.py` (MIT).
4. **Relative ranking over absolute scores.** A listwise rerank of all finalists, justified in code because absolute 0-100 scores cluster. `ColinGPT9/clips-studio` `config/prompts/rerank.txt` (AGPL, ideas only).
5. **Deterministic opener/ending gate.** Dangling openers (`so|but|and|then|also|because|however|anyway|therefore`), endings on a comma and dense speaker switching demote a candidate to review. `hotclip` `gate.ts`. Paired with the fix rule "move the START earlier, never cut the ending short" (`openshorts`).
6. **Weighted rubric with spacing.** Hook 0.30, standalone coherence 0.25, emotion 0.20, value density 0.15, payoff 0.10, threshold 60, no two clips on one subtopic, 2 minutes apart in source, hook text must not repeat the first spoken words. `AgriciDaniel/claude-shorts` `references/scoring-rubric.md` (MIT).
7. **Genre triage first.** Decide whether the footage is content-in-the-words, reaction-driven or visual-driven before deciding which evidence to trust (`hotclip`); separate prompt sets per genre (`zhouxiaoka/autoclip`, 8,986 stars).
8. **Learning loops.** `HOT.md` of falsifiable rules rewritten from the top and bottom 20 percent of published clips, refusing to change much on thin evidence; a `reflect` pass that learns the creator's filter from approved versus rejected candidates. `Upload-Post/skill-autoshorts`.

Seeing the video (how an agent that cannot watch decides well):
9. **Read the video, do not watch it.** A packed phrase-level transcript (`[start-end] S0 text`, ~12 KB per session) is always in context; a PNG with a 10-frame filmstrip, RMS waveform, word labels and shaded silences is rendered only at decision points. `browser-use/video-use` `helpers/pack_transcripts.py`, `helpers/timeline_view.py` (MIT).
10. **An auditable EDL.** Every range carries `beat`, `quote` and `reason` (`video-use`); every beat is written in original-recording seconds and mapped through a guard that throws on removed material (`talking-head-reel` `E()`).

Cutting (inside the chosen clip):
11. **Repair Whisper word times against a VAD speech map before any cut.** Whisper `end` bleeds into the following pause (one word "lasted" 9.58 s; 23 of 297 words affected) and `start` can land in silence; after re-seating, "eight of nine boundaries landed on a real pause". Words stranded by a moved boundary are redistributed so captions keep every audible word. `a-prs/remotion-video-onboarding` `fix_word_times.py`, `snap_cuts.py` (1 star, no licence; ideas).
12. **Word snapping with a half-gap lead.** Snap to the nearest word start within 1.5 s, lead into half the preceding silence up to 0.35 s, tail up to 0.45 s. `openshorts` `snap_clip_to_words`. Cut at silences of at least 400 ms, pad 30 to 200 ms, never inside a word (`video-use`). Keep a word when at least 0.1 s of it lies inside the take (`talking-head-reel` `cut.py`).
13. **Retake and stumble detection as candidates, never as automatic cuts.** Prefix matching for restarts of different lengths (`a-prs` `find_repeat_candidates.py`), Jaccard similarity of 18-token signatures and false-start rules (`nateherkai/hyperframes-student-kit` `find-cut-candidates.mjs`), silence islands transcribed separately with a `takes.tsv` of every island kept or cut (`vincentventalon/claude-code-video-editing-skill`). Filler removal limited to pure sounds, keeping "like" and "so" when load-bearing (`clips-studio` `tighten.py`). Risk tiers where any cut that changes a number, negation or qualifier is high risk; doubt means keep (`natyang1234/auto-edit-video-skill`).

Reframing (16:9 to 9:16):
14. **Plan per shot: lock, pan or track.** If every face position fits in one crop, lock for the whole shot (snap to centre within 3.5 percent); if the face barely varies, lock at the median; a steady drift gets a linear pan; only real movement gets a One Euro filter with a 2 percent dead zone; hold 1.25 s through dropouts. `hotclip` `reframe/track.ts` (AGPL, reimplement). Same idea in Google AutoFlip's steady/track/sweep decision (`motion_stabilization_threshold_percent = .30`, `snap_center_max_distance_percent = .08`) and `AhmedHisham1/pyautoflip` STATIONARY/PANNING/TRACKING.
15. **Hold, then move deliberately.** A dead band, then an eased move with a velocity cap, then settle and lock again (`clippyme` `PanSmoother`, `clips-studio` `HoldMove`, AutoFlip `kinematic_path_solver.cc`). Big jumps must repeat for 3 detections before the camera follows; the camera cuts (never pans) to the first face of a new shot (`openshorts` `SmoothedCameraman`).
16. **Offline path solving** for a two-pass skill: an L2 path minimising deviation plus velocity plus acceleration with manual keyframe constraints, Kalman-RTS, Savitzky-Golay, AutoFlip-style `stationary_lock` (`clippyme` `reframe_ops.py`, MIT); a robust quartic fit with Cauchy loss (AutoFlip `polynomial_regression_path_solver.cc`); sparse 2 fps keyframes, median filter, cubic Hermite with clamped tangents compiled into one ffmpeg `crop` x-expression (`ft1148137/reframe-video-subject-skill`).
17. **Who is speaking.** TalkNet audio-visual active-speaker detection with boxes detected at 8 fps and interpolated to 25 fps (+15 percent cost), with the measured finding that mouth-pixel motion differed only 7 percent between speaker and listener (`clips-studio` `video/asd.py`, AGPL). Cheap fallback: per-speaker normalised mouth motion gated on audio RMS with a 3-window hold (`openshorts` `active_speaker.py`, MIT). Split-screen when two faces cannot fit one crop (`pyautoflip`), with captions on the seam (`openshorts` `\an5`).
18. **Prove the crop.** Report the least-visible face per sampled frame (`hotclip` `evaluateCropCoverage`); build face crops from the native-resolution source (student kit); filter false faces under 3 percent of frame area such as posters (`pyautoflip`).

Captions:
19. **Rail plus embed.** A verbatim lower-third rail carries the words; at most one earned peak word per thought is promoted and composited behind the speaker through a human matte (`u2net_human_seg`); a luminance probe on the caption region decides the scrim (under 60 bare, 60 to 180 glyph scrim, above 180 opaque plus scrim). `heygen-com/hyperframes` `skills/embedded-captions` (Apache-2.0).
20. **Grouping rules that fix caption lag.** Break on a pause of 500 ms, a sentence end, a comma plus 250 ms, a discourse reset ("but", "so"), or 6 words / 2.5 s; `in = w[0].start - 0.08`, `out = min(next.in - 0.05, last.end + 0.6)` (`hyperframes` `references/caption-grouping.md`). The `min(next.in ...)` clamp is exactly what `talking-head-reel`'s captions lack.
21. **A declarative word-state model.** Three states per word (`not-narrated-yet`, `being-narrated`, `already-narrated`) with tags as CSS classes and only two triggers (`narration-starts`, `narration-ends`). `francozanardi/pycaps` (MIT).
22. **Remotion primitives that fit this project.** `createTikTokStyleCaptions` pages, `@remotion/elevenlabs` (ElevenLabs word timings straight to `Caption[]`), `@remotion/layout-utils` `fitText`, `@remotion/rounded-text-box`; the thick-outline trick `WebkitTextStroke` with `paintOrder: "stroke"` (`remotion-dev/template-tiktok`). The student kit reports inconsistent `-webkit-text-stroke` in Chromium renders and prefers layered `text-shadow`; test both at phone size.

Motion, sound, overlays:
23. **Snap zoom grammar.** A step function alternating 1.0 / 1.1 at every cut and most sentence starts, multiplied by slow 1.10 to 1.15 pushes on four to six lines that matter; snaps replace crossfades between takes (`talking-head-reel`). Tuning lesson: loudness-driven punch-ins came out at "8.4 punches per minute ... a twitch" (`openshorts` `punch_in.py`).
24. **Beat table from speech act to overlay** (product name to logo chip on the word, number to a big callout, dismissed list to a stamp, quote to a quote card), one item per slot, nothing in the first 0.5 s of a sentence, gone 0.3 s after (`talking-head-reel`); "said X, X not shown = FAIL" (`jincheng2026/jc-remotion-skills` judge rubric).
25. **Sound design with restraint.** "~20 stock whooshes ... in 18s reads as generic; ~8 reads as designed", hit on the measured attack, duck music 12 to 15 dB (`video-use`); at most 3 SFX per clip (`hotclip`); a synthesized SFX kit with no licence question (`talking-head-reel` `make_sfx.py`); static gain plus limiter on quiet phone speech instead of one dynamic loudnorm pass (`a-prs` `clean_audio.py`); 30 ms audio fades at every cut (`video-use`).

Verification:
26. **Validators proven with negative controls.** Caption words 1:1 with retained transcript words within 5 ms, every word inside exactly one kept range, frame-aligned scenes, gaps over 2.2 s need a `holdReason`; each check must fail on a 0.3 s caption shift, a one-frame gap and a dropped word. `nateherkai/hyperframes-student-kit` `validate-plan.mjs`, `quality-gates.md`.
27. **Preview before render, then a fresh-eyes critic.** Composite preview frames in ~2 s each ("A full render costs minutes — never use it to discover layout problems"); a sub-agent that sees only the preview sheet and a checklist gives PASS/FIX per frame (`hyperframes`). A judge agent that cannot edit, four 0-10 dimensions, any below 7 goes back, every violation cites a frame and a fix (`jc-remotion-skills` `agents/mg-judge.md`). "Brief it to roast, not to praise" (`video-use`).
28. **Word-exact sampling and machine checks.** Frames at spoken-word timestamps, never round numbers (student kit); sync at cue start -6, 0, +3, +8 frames and a luminance-curve flicker test (`Vincentwei1021/anything2explainer`); `blackdetect`, `freezedetect=n=-50dB:d=0.3` with a presenter freeze as FAIL (`jc-remotion-skills` `qc-master.mjs`); `ebur128` per section, "You cannot listen: say so, and report the numbers" (`video-use`); `silencedetect` on the output where a silence over 0.8 s inside speech is a missed cut (`talking-head-reel`); re-transcribe the rendered audio (student kit, natyang); automatic repair kept only when the re-check strictly improves (`hotclip`).
29. **Operational hardening.** Detached renders with a log and a monitor loop, a chunked low-memory render path, font loading through `delayRender` with a fallback (`talking-head-reel`); never overwrite a render, move the previous one to `out/versions/` with its plan (`EdYuTo/yt-video-creator`); dense-keyframe re-encode (`-g fps -keyint_min fps`) before browser rendering so seeks never freeze (`hyperframes` `talking-head-recut`); iPhone HLG/PQ tone-mapping before any grade (`video-use` `render.py`); force the Whisper language (yt-video-creator).
30. **A human-editable exit.** FCP7 XML for Resolve or Premiere (`SmartCut`), or Studio-editable Remotion props, so one bad cut can be fixed by hand.

## (b) Recurring weaknesses a superior skill must fix

1. **Selection reads text only.** Laughter, delivery, faces and on-screen content are invisible to the scorer in nearly every default path. Only `skill-autoshorts` (Gemini on the file) and optional frame checks in `openshorts` and `hotclip` let a model see anything.
2. **Scores that mean little and rubrics that reward bait.** Absolute 0-100 "viral" scores cluster; the most copied rubrics score "Everything you know about X is wrong" at 80 to 100; hooks are generated clickbait ("POV: ...") rather than the speaker's own strongest line. No rubric protects qualifiers, a claim's exact numbers or the speaker's voice, which matters for a serious author whose house rules ban engagement bait.
3. **Timestamps that lie.** Invented by the model or snapped to Whisper segments (`Anil-matcha`, `clips-studio`, `viral-clips-crew`, FunClip); raw Whisper word times trusted as truth (everyone except `a-prs`); careful snapping silently undone by `-c copy` cuts that land on keyframes (`claude-shorts`, `clipify`, ECC). `Anil-matcha/AI-Youtube-Shorts-Generator` (5,153 stars) adds its chunk offset to timestamps that are already absolute, so on videos over 30 minutes every clip after the first chunk points at the wrong place (`shorts_generator/highlights.py` lines 176 and 297).
4. **Clippers do not edit and editors do not clip.** `claude-shorts`, `clipify` and the apps mine moments but leave stumbles, retakes and dead air inside the clip; `video-use`, the student kit and `talking-head-reel` tighten takes but cannot mine a 60-minute lecture.
5. **Reframing is the weakest link.** Centre crops (ECC, HyperFrames `media-use`), one static guess from 5 frames following the largest face (`claude-shorts`), Haar plus EMA with no dead zone (`Anil-matcha`), hand-drawn mouth boxes with hard-cut pans (`clipify`). Per-frame symmetric smoothing makes the frame breathe with every nod; there is rarely a "this shot should not move" plan, rarely a scene-cut reset and rarely a speaker model. Crops and zooms come from downscaled proxies, so every punch-in is an upscale (`talking-head-reel` zooms a 1080x1920 transcode by 1.1 to 1.15).
6. **Captions are either plain or generic.** libass colour swap plus at most a scale pop; centred TikTok pages with one highlight colour; fixed 3-word chunks that ignore phrases. Almost none places captions against the face or checks legibility against the background (HyperFrames is the exception). `talking-head-reel` shows the previous caption group for up to 300 ms into the next group's first word, because each group lingers 0.3 s and `groups.find()` returns the earlier group. Caption text diverges from audio when fillers are removed from captions only.
7. **Effects on timers and loudness.** Zooms and SFX fire on audio envelopes, "power word" lists or 10-second breathing cycles, which reads as twitching; stock SFX and imgflip memes carry rights and tone risks.
8. **Self-graded, low-resolution verification.** The generating agent looks at its own 320 px filmstrips at round-number timestamps; almost nothing checks phone-size legibility, re-transcribes the output, or proves its validators fail on a known-bad input.
9. **Fragile installs.** CUDA- and Windows-first defaults, Python version pins (pycaps 3.10 to 3.12), MoviePy 2 breaking MoviePy 1 code (`captacity` fails on a fresh install), hard-coded author paths (`/opt/anaconda3/bin/whisper` in `talking-head-reel`), cloud ASR as a hard dependency, Homebrew's default `ffmpeg` formula shipping without libass.
10. **Prose over scripts.** 300 to 1,200-line SKILL.md files with the rules in prose; the reliable parts (repair scripts, validators) are rare. Runs drift.
11. **Licence blind spots.** AGPL (`hotclip`, `clips-studio`, `pireel`), PolyForm Noncommercial (`anything2explainer`), InsightFace pretrained weights (noncommercial), Remotion's company licence above three employees; almost no skill mentions licensing.
12. **Single, overwritten outputs.** One 9:16 file, no clean (caption-free) version, no SRT/VTT sidecar, no 16:9 or 1:1 variant, no thumbnail frame, previous renders overwritten.

## (c) Rendering approach on macOS Apple Silicon

Recommendation: **Remotion for the final render of anything with designed captions, overlays or camera moves; ffmpeg with libass as the fast path for drafts and caption-only variants; ffmpeg alone for cutting, reframing to a high-resolution intermediate, probing and loudness.** HyperFrames is the credible alternative if Remotion's licence becomes a problem or if text-behind-the-speaker becomes a requirement. pycaps is a source of ideas; MoviePy should not be used for new work.

Reasons:
- **Look.** Remotion draws anything CSS, SVG or canvas can: springs, per-word transforms that reflow correctly, colour emoji, rounded plates, blurred shadows, masks, cards and logo chips, all in one frame-seeked pass. libass cannot do springs, colour emoji (libass issue #381 is open) or soft plates. A scaled active word also shifts its neighbours. pycaps renders CSS only for static word states (CSS animations are disabled at screenshot time), so motion is limited to fade, pop, zoom and slide primitives. MoviePy is PIL-quality text with slow per-frame Python compositing.
- **Fragility.** Remotion bundles its own ffmpeg (`@remotion/compositor-darwin-arm64`) and downloads Chrome Headless Shell, so it is immune to Homebrew's ffmpeg packaging. That packaging is a live risk: the current Homebrew `ffmpeg` formula (9.0.2 on 2026-09-27) has no libass dependency, while `ffmpeg-full` has `--enable-libass`. This Mac's 8.0_1 still has `ass`, `subtitles` and `drawtext`; a `brew upgrade` would remove them. The libass path must therefore pin `ffmpeg-full` or probe `ffmpeg -filters` at start-up and fail loudly. HyperFrames needs Node 22+, system ffmpeg and Puppeteer; on macOS it runs in screenshot mode because BeginFrame capture is Linux-only. It ships releases daily (v0.8.79 and v0.8.80 within one day) with some skills needing a built checkout. pycaps needs Python 3.10 to 3.12, Playwright Chromium and Numba. MoviePy 2 broke MoviePy 1 code and MoviePy 1 `TextClip` needs ImageMagick, which is not installed here.
- **Speed.** Remotion is the slow option: about 4 fps for 1080x1920 with one `OffthreadVideo` at concurrency 8, memory-hungry enough that the reference skill needed a chunked render for swap-induced `ENOSPC`. Concurrency 4 to 6 is a sensible starting point on this M3 Pro with 36 GB (not yet measured). The cure is structural: render stills and preview composites to find layout problems, render the final once in the background, cap concurrency, split long renders. libass is a single ffmpeg pass faster than real time with `h264_videotoolbox`.
- **Agent ergonomics and continuity.** The project already has the `remotion-best-practices` skill installed and already produces ElevenLabs word timings, which `@remotion/elevenlabs` and `@remotion/captions` consume directly; the reference skill's overlay grammar is Remotion. Remotion's API is stable across 4.x (the official skills are versioned 4.0.529 and direct agents to `<Video>` from `@remotion/media`; the reference skill pins 4.0.245 and uses `OffthreadVideo`).
- **Licence.** Remotion is free for individuals and for-profit organisations with up to three employees; a pipeline run inside a larger company needs a Company License. personal use is fine; running it inside Acme should be checked against Acme's headcount before relying on it there.

Suggested division of labour: Python and ffmpeg compute the word-level cut list and a per-shot camera path (lock / pan / track, dead band, velocity cap, scene-cut snaps), then ffmpeg renders a reframed vertical intermediate at 1440x2560 or higher from the native-resolution source with dense keyframes, so punch-ins stay sharp and Chrome decodes a smaller file than 4K; Remotion applies the snap and push zoom grammar, captions, overlays and SFX in one render; ffmpeg does loudness (static gain plus limiter, or two-pass loudnorm to -14 LUFS for platforms), `blackdetect`, `freezedetect` and `silencedetect`. The draft and caption-only variants go through a pinned libass build.

## Top five repositories by usefulness

1. **browser-use/video-use** (27,380 stars, MIT, active): the architecture for an agent that cannot watch video (packed transcript plus on-demand filmstrip and waveform PNGs), an EDL with quote and reason per cut, twelve hard production rules, a self-eval pass at every cut plus a "roast, not praise" critic. Weak on captions, reframing and clip mining.
2. **mutonby/openshorts** (5,726 stars, MIT, active): two-pass windowed selection with the 2-second test, word snapping, the "heavy tripod" camera with jump confirmation and scene snaps, audio-gated active-speaker switching, stacked two-speaker layout with seam captions. Its comments record measured tuning. MIT, so code can be borrowed.
3. **heygen-com/hyperframes** skills `embedded-captions` and `talking-head-recut` (53,574 stars, Apache-2.0, active): the best caption craft (rail plus embed, human matte, luminance scrim, grouping rules) and the best gates (timing drift at 0.08 s, occlusion, overflow, font fitting, preview-before-render, fresh-eyes critic).
4. **xixihhhh/hotclip** (257 stars, AGPL-3.0, active; ideas only): quote-don't-timestamp selection, stitching rules, the deterministic opener gate, the per-shot lock/pan/track reframing planner, crop-coverage checks and render QA with repair kept only on strict improvement.
5. **nateherkai/hyperframes-student-kit** (1,047 stars, custom licence, active): validators calibrated with negative controls, the first-three-seconds gate with an open-loop ledger, mechanical retake candidates that stay review-gated, word-exact frame verification.

Next in line: `fralapo/clippyme` (MIT library of camera smoothers and the gated rubric), `mariagorskikh/talking-head-reel` (overlay grammar, zoom grammar, original-time guard), `a-prs/remotion-video-onboarding` (Whisper word-time repair), `ColinGPT9/clips-studio` (TalkNet speaker detection, listwise rerank), `remotion-dev/skills` with `@remotion/captions`.

## Where the verbatim material is

- Clip-selection prompts and rubrics: Part 2 "Best clip-selection prompts, verbatim" (OpenShorts two-pass, ClippyMe gate and rubric, HotClip quote rules, clips-studio rerank, skill-autoshorts learning prompt, OpenShorts word snapping) and Part 3 sections 1, 3 and 5 (video-use editor brief, student-kit first-three-seconds gate, claude-shorts weighted rubric).
- Camera smoothing: Part 2 "Best reframing / smoothing code, verbatim" (HotClip per-shot planner, ClippyMe `PanSmoother`, ClippyMe L2 path solver and stationary lock, OpenShorts jump confirmation) and Part 4 section 8 (AutoFlip steady/track decision, robust polynomial path, kinematic solver; pyautoflip camera modes and split-screen rule; FrameShift) plus the Hermite crop expression in Part 4 section 11.

---


## Part 1. The reference skill: mariagorskikh/talking-head-reel

- Repo: https://github.com/mariagorskikh/talking-head-reel (MIT, 56 stars, 5 forks, single commit pushed 2026-09-22; local clone at `scratchpad/ref/talking-head-reel`, HEAD c8472f3).
- Stack: ffmpeg (VideoToolbox h264 for the transcode), openai-whisper CLI (`turbo`, word timestamps, CPU with `--fp16 False`), Python 3 stdlib scripts, Remotion 4.0.245 + React 18, Geist fonts, a synthesized SFX kit (`remotion/scripts/make_sfx.py`, pure stdlib: pop, tap, tick, thud, whoosh, click, ding), simple-icons SVGs.
- Scope: ONE portrait phone recording of ONE person reading a script with retakes, turned into a 60 to 90 s 1080x1920 reel. It is a take-picker plus a motion-graphics layer. It is explicitly not a long-form-to-shorts clipper and not a reframer ("Not for landscape walkthroughs with a screen recording").

### Pipeline (as the SKILL.md instructs)

```
prep.sh       -> public/talk/ig1080.mp4           (portrait 1080x1920, 30 fps, cheap to seek)
transcribe.py -> words.whisper.json + segment table   (the WHOLE recording, all takes)
choose takes  -> reel-segments.json                 (original seconds, best take per sentence)
cut.py        -> reel-words.json + edit timeline    (captions in edit time, frames per take)
plan          -> beats: original second -> overlay
Reel.tsx      -> Remotion composition (copy assets/reel-overlays.tsx)
stills.sh     -> tiled portrait grids at the key seconds, fix layout
render.sh     -> detached render (~10 min for 80 s)
QA            -> probe, contact sheet, audio check, copy to Desktop, hand over
```

### What it does well (ideas worth keeping)

1. **Original-time addressing with a guard.** Every beat, snap and push is written in ORIGINAL recording seconds; `E(t)` maps to an edit frame through the chosen takes and throws if `t` was cut (`throw new Error(\`E(${t}): not inside any take in reel-segments.json\`)`). `stills.sh` uses the same mapping, so a still or a beat can never point at removed material. This is the single best engineering idea in the repo.
2. **Word-overlap keep rule at cuts** (`scripts/cut.py`): "keep a word when at least 0.1 s of it (or half of a short word) falls inside the take; whisper stretches a word over the pause before it". Plus: capitalise a take's first word only when the previous kept word ended a sentence; frame-snap the edit offset so seconds and frames agree; fail loudly when a segment contains no words.
3. **Cut padding from word times**: start 0.10 to 0.15 s before the first word, end 0.20 to 0.30 s after the last, and when whisper produces a suspiciously long word, run `silencedetect=noise=-32dB:d=0.25` on that window to find the real onset.
4. **Take-selection rubric** (`references/take-selection.md`): match the script's meaning, fluent, later over earlier ("people warm up"), keep a run of consecutive sentences as one segment ("one cut instead of four"), splice one-liners from other runs only when framing matches, pauses under 0.5 s stay ("the speaker's rhythm"), pauses over ~1 s get a cut plus a snap. "Lines never said do not appear, not as captions, not as cards."
5. **Zoom grammar**: two multiplied layers. `SNAPS` is a step function alternating 1.0 / 1.1 (1.12 on a punchline) at every cut and most sentence starts, "about one every three to four seconds", each with a soft tap SFX; `PUSHES` are slow push-ins (1.10 to 1.15 over 8 to 16 frames) on the line that matters, 4 to 6 per reel. "Snap zooms replace crossfades. A crossfade between two takes of the same sentence reads as a mistake; a framing change reads as an edit."
6. **Audio de-click at every cut**: `volume={(f) => interpolate(f, [0, 2, s.frames - 3, s.frames - 1], [0, 1, 1, 0])}` on each `OffthreadVideo`.
7. **Beat table** mapping speech acts to overlays (product name -> logo chip on the word; number -> `Big`; dismissed list -> `StampList`; quote -> `QuoteCard`; "not about X" -> `StrikeBig`; typed prompt -> `PromptCard` at ~44 cps with key ticks; feeling -> `BigEmoji` plus a push-in; punchline -> `Meme`; close -> `EndCard` over a `Freeze` of the last frame). And the density rules: one thing in the card band and one in the reaction slot at a time, nothing in the first half second of a sentence, everything gone 0.3 s after, "silence in the band is what makes the next overlay land", memes land on the punchline word, never before it.
8. **Measured safe zones** for Instagram Reels at 1080x1920 (top 250 px, bottom 450 px, right 130 px from y ~1000 to 1500; important content in x 60 to 930, y 250 to 1470) and a recipe to measure a new recording (`drawgrid=width=108:height=192`).
9. **Verification loop**: tiled stills at every beat's landing moment and every cut before the full render; after the render: ffprobe, `ebur128` loudness (lift phone speech from ~-27 to ~-16 LUFS with `volume` + `alimiter`, video stream copied), a 4 s contact sheet, and a `silencedetect` pass where "a silence longer than 0.8 s inside the speech means a pause that should have been cut".
10. **Operational hardening for Remotion on a Mac**: detached `nohup` render with a log and a Monitor loop (the Bash tool dies at 10 min); refuses to start if a render is already running; a chunked render path (`render-chunked.sh`: muted 420-frame chunks, concurrency 2, `--jpeg-quality 65`, audio rendered separately, ffmpeg concat) for the ENOSPC-from-swap failure; font loading through `delayRender` with a fallback so a font failure never hangs a render.
11. **A synthesized SFX kit** (no licensing question) and a rule of fixed volumes per event type (pop 0.28 to 0.42, thud 0.4 to 0.55, whoosh 0.3, tick 0.22, tap 0.22).
12. **Rules that came from getting it wrong** as a section, which is the right format for an agent skill.

### How the captions are implemented (`ReelCaptions` in `assets/reel-overlays.tsx`)

- Words grouped greedily into chunks of 3, or earlier at `.?!,`.
- A group is visible for `t` in `[first.start - 0.05, last.end + 0.3)`; it fades and rises in over 0.1 s (`translateY((1-a)*14px) scale(0.96+0.04a)`).
- Rendering: one dark pill (`rgba(12,12,14,0.88)`, radius 22, padding 16x32, maxWidth 900, flex-wrap), Geist 66 px weight 800, letter-spacing -0.5. Spoken words white, the current word in accent `#FFD166` at `scale(1.06)`, unspoken words at 42 percent white. Bottom edge at y 1470.
- Look: clean, legible, "tech explainer" rather than "creator" style. No stroke, no per-word pop, no emphasis colouring of key words, no emoji, no two-line layout control.

**Bug found:** `groups.find(...)` returns the FIRST group whose window contains `t`. Because each group lingers 0.3 s after its last word, whenever the next group starts less than 0.3 s after the previous one ends (normal fluent speech) the previous group stays on screen and its last word stays highlighted while the next group's first word is already being spoken. Captions lag by up to 300 ms at every group boundary in fluent speech. Fix: end the linger at `min(last.end + 0.3, next.start - 0.05)`, or pick the LAST matching group.

### How the overlays are implemented

- All overlays are absolutely positioned React components driven by `useCurrentFrame()`, `spring()` (damping 8 to 15, stiffness 150 to 240, mass 0.5 to 0.8) and `interpolate()` with clamp and cubic easing. A shared `Card` (dark, radius 26, big shadow, `backdropFilter: blur(10px)`) gives enter (spring translateY 40 px + scale 0.92 to 1) and exit (8-frame fade).
- Each overlay is wrapped in `<At from={origSec} to={origSec}>`, a `Sequence` placed via `E()`; inner timings use `rel(t, from)`.
- SFX are `<Sequence from={at}><Audio src="sfx/pop.wav" volume={...}/></Sequence>` embedded inside components.
- Components: `ReelCaptions`, `StampList`, `QuoteCard`, `StrikeBig`, `TreeCard`, `PromptCard`, `RecBadge`, `Takes` (polaroids), `GitHubCard`, `EndCard`, `BigLogo`, `BigEmoji`, `Meme`, `HeroChips`, plus in `overlays.tsx`: `Card`, `Big`, `LogoRow`, `RepoCard` (stars count up), `ScreenClip`, `Still`, landscape `Captions`, `usePush`.
- Quality: tasteful and consistent (one font, one accent, one red, one shadow). The motion vocabulary is spring pop-ins; there is no kinetic typography, no masked reveals, no motion blur, no B-roll, no screen-shake, no light leaks, no transitions beyond snaps.

### What it lacks (concrete weaknesses)

1. **No clip discovery.** It chooses takes of a known script; it cannot find the best 45 s inside a 60-minute lecture. No hook/payoff rubric, no scoring, no multiple candidates.
2. **No reframing at all.** It assumes a portrait source with the face centred; the zoom origin is a hard-coded `50% 29%` and `CARD_Y` 990 comes from one person's measured chin. A landscape lecture, a two-person podcast, a speaker who walks: all out of scope. No face detection, no smoothing, no speaker switching.
3. **Zoom softness.** `prep.sh` downscales to 1080x1920 and the zoom is a CSS `scale()` of that 1080p video, so every 1.1 to 1.15 punch-in is an upscale. Keeping a 4K (or at least 1.25x) intermediate for zoom headroom would keep the punch-ins sharp.
4. **Transcription is slow and loose.** openai-whisper `turbo` on CPU with fp16 off, a hard-coded `WHISPER = "/opt/anaconda3/bin/whisper"`, no forced alignment (WhisperX/stable-ts) and no MLX/whisper.cpp Metal path. Word boundaries come from raw whisper word timestamps, which the skill itself has to patch with silencedetect.
5. **Everything creative is hand-typed seconds.** Beats, snaps and pushes are literal arrays in `Reel.tsx`; there is no beat-plan JSON, no auto-generated first draft of snaps at cuts and sentence starts, and no linter for the density rules the SKILL.md states (one item per slot, nothing in the first 0.5 s, gone 0.3 s after the sentence, safe zones).
6. **Caption lag bug** described above; captions have no outline/shadow option for bright backgrounds, no keyword emphasis, fixed 3-word grouping without measuring rendered width.
7. **Audio is minimal.** No denoise, no EQ/compression, loudness fixed after the render with a second encode pass, no music bed or ducking, no room-tone fill at cuts.
8. **Memes from imgflip** are a rights risk for anything commercial and a tonal risk for a serious speaker.
9. **Render cost.** ~4 fps for a 1080x1920 composition with one OffthreadVideo; `backdropFilter: blur` on every card adds cost; Remotion's full Chromium stack is heavy on a 16 GB Mac (their own chunked path exists because of swap). Remotion's company licence applies to teams above three people.
10. **Single-output.** One 9:16 file; no 16:9/1:1 variants, no burned-in versus clean versions, no SRT/VTT sidecar for platform captions, no title/hook text or thumbnail frame.
11. **No automated QA of the final frames** beyond a contact sheet the agent eyeballs: no check that the face stays inside the frame, that captions do not cover the mouth, that overlays do not collide.

---

## Part 2. End-to-end "long video to shorts" apps (Opus Clip alternatives)

Surveyed 2026-09-27 by reading the cloned code under `scratchpad/ref/<owner>_<repo>`. Stars and dates from `gh api repos/...` on that day.

### Summary table

| Repo | Stars | License | Last push | Selection | Reframe | Captions | Verdict |
|---|---|---|---|---|---|---|---|
| mutonby/openshorts | 5726 | MIT (self-host) + separate cloud/ license | 2026-09-27 | 2-pass LLM (score windows, detail shortlist), word-snap | MediaPipe BlazeFace + YOLOv8, "heavy tripod" dead zone + jump confirmation, scene reset, TRACK/GENERAL/SPLIT/SCREENCAST/INSET layouts, mouth+audio ASD | ASS karaoke via libass (effects pop/glow/box); Remotion path for preview | The most engineered open app; measured, commented decisions |
| fralapo/clippyme | 45 | MIT | 2026-09-17 | Gemini, 5-axis rubric + hard gate + grounding rules | YOLOv8 + FaceMesh MAR, SmoothedCameraman with EMA/1-euro/spring options, global Savitzky-Golay / Kalman-RTS / L2 path, AutoFlip stationary lock | ASS `\k` presets | Fork of OpenShorts; best library of smoothing math; best rubric |
| xixihhhh/hotclip | 257 | AGPL-3.0 | 2026-09-23 | LLM quotes text (never timestamps), reverse-matched; "parts" stitching; rule quality gate | YuNet faces, per-shot locked / linear pan / 1-euro track with dead zone, crop-coverage QA | ASS (karaoke/keyword/pop/hormozi/minimal) + offscreen-Chromium HTML template | Best doctrine and QA loop; Electron/TS |
| ColinGPT9/clips-studio | 65 | AGPL-3.0 | 2026-09-27 | Signal fusion (audio excitement, PANNs, visual) + LLM score + listwise rerank | YOLOv8 pose + TalkNet ASD, HoldMove hysteresis controller | ASS word groups | Best active-speaker approach (TalkNet); rerank idea |
| Anil-matcha/AI-Youtube-Shorts-Generator (ex SamurAIGPT) | 5153 | MIT | 2026-09-17 | One LLM call per 20-min chunk, 8-signal virality list | API mode: paid MuAPI autocrop; local: Haar + EMA 0.15 | none | Stars far exceed substance; now a MuAPI funnel |
| modelscope/FunClip | 6351 | MIT | 2026-09-16 | User picks text/speaker; LLM picks SRT ranges | none | MoviePy + PIL TextClip | Transcript-as-editor idea; no vertical |
| zhouxiaoka/autoclip | 8986 | MIT | 2026-09-27 | Outline, timeline, 4-axis score, titles, topic clustering (per-genre prompt sets) | none (horizontal topic clips, 3-8 min) | n/a | Long-form "chaptered highlight" tool, not shorts |
| ClipsAI/clipsai | 543 | MIT | 2024-01-17 (dead) | TextTiling on sentence embeddings (topic boundaries, no virality) | MTCNN + FaceMesh MAR, pyannote speaker turns x scene cuts, one static crop per segment | none | Library, unmaintained; per-segment static crop is the useful idea |
| Shaarav4795/ClippedAI | 210 | none asserted | 2026-09-04 | clipsai TextTiling + heuristic "engagement" score | clipsai resizer | ASS, numbers in yellow, top-center | Thin wrapper; heuristic scoring is weak |
| Upload-Post/skill-autoshorts | 146 | none | 2026-05-02 | Gemini multimodal on the video file + word-snap rule; HOT.md learning loop from metrics and approvals | none (expects 9:16 input) | PIL hook overlay only | Best feedback-loop design; an agent skill |
| alexfazio/viral-clips-crew | 768 | MIT | 2026-02-16 | One GPT call returns clip TEXT; CrewAI agents match text back to SRT | none | ffmpeg `subtitles=` default style | Obsolete; contradictory prompt |
| atherion005-byte/agent-opus | 12 | MIT | 2026-04-29 | Ollama prompt, fallback keyword heuristic | YOLOv8 person + moving average | PIL frames in MoviePy (karaoke, pill) | Toy; one commit |
| faris-sait/openshorts | 103 | MIT | 2026-04-17 | copy of an April 2026 OpenShorts snapshot | same | same | Ignore; use mutonby/openshorts |
| yukitorido/short-video-generator-AI | 722 | MIT | 2026-09-23 | fake | fake | fake | **MALWARE. Do not install.** See below |
| ghost1412/shorts-generator | 6 | MIT | 2026-09-11 | mostly faceless AI content | "EMA face tracking" switch | Remotion | Kitchen-sink; not relevant |

Also seen on the `opus-clip-alternative` topic page: NovaTaleRise/clip-studio-ex-nexus (226 stars) and Trianglezichopper/submagic-core (215 stars), both created 2026-08-06 with 0 forks. Same star-farm pattern as yukitorido; not opened, treat as hostile.

---

### 1. mutonby/openshorts (5726 stars, MIT, very active)

What it does: self-hostable Docker app plus hosted SaaS (openshorts.app) that turns a YouTube link or upload into 9:16 clips with face tracking, burned captions, a hook overlay, dubbing, thumbnails and publishing. Has an MCP server, a CLI and a Claude-style `skills/openshorts/SKILL.md` that drives the hosted API.

Pipeline: yt-dlp download, faster-whisper (`small`, `vad_filter`, `condition_on_previous_text=False`, word timestamps) or other backends, scene detection (PySceneDetect), clip selection (2-pass Gemini or any OpenAI-compatible local LLM), word snapping, per-scene layout decision, reframe (v2: analyse at 640 px, render natively in ffmpeg with `sendcmd` crop commands per scene, concat with stream copy), hook overlay (PIL image), captions (ASS burn), optional punch-in zooms, hook grounding from frames.

Clip selection (`main.py:get_viral_clips`, `gemini_worker.py`, `clip_selection.py`):
- Windows of about 90 s (scaled to 1.5x the max clip length) built on Whisper segment boundaries with 30 s overlap.
- Pass 1 `SCORE_PROMPT_TEMPLATE`: score EVERY window 0-100 against "the 2-second test", in near-equal batches; shortlist is the global top N (`shortlist_target = clamp(duration//90 + 2, 3, 10)`).
- Pass 2 `DETAIL_PROMPT_TEMPLATE`: choose clips inside the shortlisted windows with rules for the 2-second rule, STANDS ALONE, HOW MANY (a floor and ceiling), DIVERSITY, a hook playbook and "about this moment, not the video".
- A floor-recovery call asks unused windows for missing clips; `trim_to_best` keeps by score (not position); `snap_clip_to_words` moves boundaries onto real word starts/ends plus half the adjacent silence (max lead 0.35 s, tail 0.45 s); `dedupe_overlapping` by ratio of the shorter clip.
- Comments cite production measurements (for example "95% of jobs delivered 3 clips or fewer" and boundary error p90 0.4-0.5 s before snapping). This is the only repo whose selection logic is tuned against measured outcomes.
- `_run_stage_split` bisects a batch when Gemini's content filter blocks it.

Reframing:
- Detection: MediaPipe BlazeFace (`model_selection=1`, conf 0.5) every `DETECT_STRIDE=4` frames and at scene starts; YOLOv8n as fallback.
- `SmoothedCameraman` "heavy tripod": dead zone of 25% of crop width; inside it the camera does not move; outside it moves linearly at 3 px/frame (15 px/frame if the error exceeds half the crop width) with overshoot clamp. `update_target` requires a big jump to repeat `JUMP_CONFIRM_FRAMES=3` times before following (measured: in-scene reversals -69%, travel -34%). `begin_scene` snaps to the first face of a new shot instead of panning.
- `analyze_scenes_strategy`: 5 sampled frames per scene; average faces 0.5 to 1.2 is TRACK, else GENERAL (blurred-background letterbox); hysteresis flips short scenes whose neighbours agree.
- `split_layout` stacks two speakers top/bottom; `active_speaker.py` attributes 0.4 s windows by per-speaker normalised mouth motion gated on audio RMS (`AUDIO_FLOOR=0.18`, `MIN_MARGIN=0.15`) and a `hold()` that needs 3 consecutive windows to change speaker; `SPEAKER_CUT=1` cuts to whoever holds the floor.
- `layout_picker.py` asks Gemini for a categorical layout decision from 12 frames at 1024 px (measured 92-96% agreement with hand labels), explicitly because continuous "measure X" prompts were unstable.
- `camera_inset.py` and `screencast_layout.py` handle a webcam inset over a screen recording.

Captions (`subtitles.py`): one ASS Dialogue event per word, each event the whole block with the active word wrapped in override tags. Effects: `pop` (`\fscx90\fscy90\t(0,110,\fscx108\fscy108)`), `glow` (`\bord` + `\blur4`), `box` (thick outline). Default `AUTO_CAPTION_STYLE`: Anton 44 at PlayResY 288, uppercase, highlight #FFE500, 16 chars/block, max 1.4 s per block. On SPLIT scenes each event gets `\an5` so the caption sits on the seam between stacked faces. Looks competent and standard; libass limits it to per-word colour and scale.

Other effects: `punch_in.py` 1.12x zoom pushes (rise 0.25 s, hold 1.3 s, fall 0.55 s) on audio-envelope beats, off by default, with a comment documenting that the first tuning produced "8.4 punches per minute... not a push on the beat, it is a twitch". Hook overlay styles (pill, classic, dark, yellow, red, outline) rendered with PIL. `hook_grounding.py` rewrites the hook from 3 frames when the clip is a screencast so the hook names what is on screen. Remotion compositions (Subtitles, HookOverlay, VideoEffects zoom/colour) exist for preview and a render service.

Weaknesses:
- Selection is text-only except the optional layout and hook-grounding calls; the model never sees delivery, laughter or face.
- Default model `gemini-3.1-flash-lite`; quality of judgment is traded for price per job.
- Hook text is generated copy ("POV: ...") rather than the speaker's own line; the hook playbook pushes clickbait-flavoured overlays.
- Punch-ins keyed to audio loudness rather than meaning (the file says so).
- `main.py` is 2500 lines and `app.py` 6897 lines; many behaviours hidden behind env flags that default off (SPEAKER_SIGNAL, SPEAKER_CUT, PUNCH_IN).
- Dead zone of 25% crop width is large for a 9:16 crop of a single speaker: the face can sit well off-centre for a whole scene.

### 2. fralapo/clippyme (45 stars, MIT, active)

What it does: an OpenShorts fork "hardened and extended": Deepgram/ElevenLabs/Whisper transcription (ElevenLabs Scribe audio-event tags such as `(laughter)` feed the prompt), Gemini selection, active-speaker reframing, compose-on-download editing, scheduling via Zernio. Huge test suite. Its `docs/` holds comparative analyses of about fifteen other reframe and caption repos (smart-reframe, auto-vertical-reframe, montage-ai, clipsai, autocrop-vertical, FrameShift, flycut-caption, videolingo), which is itself a map of the field.

Clip selection (`src/clippyme/pipeline/gemini_request.py`): single Gemini call over transcript plus WORDS. The prompt has a gate ("a clip must hit at least ONE of these HARD"), a 5-axis 1-20 rubric (HOOK_STRENGTH, EMOTIONAL_PAYOFF, QUOTABILITY, SELF_CONTAINED, DENSITY), diarization and audio-cue rules, a hard constraint that `start`/`end` must be copied from a word's `s`/`e`, a speaker-attribution rule (never name a speaker unless the name is spoken in the clip) and a long title-copy section with grounding rules. A 5-level robust JSON parser handles malformed output. Excerpts below.

Reframing (`reframe_track.py`, `reframe_ops.py`, `reframe.py`): YOLOv8 person + MediaPipe FaceMesh mouth-aspect-ratio variance picks the speaker. `SmoothedCameraman` has dead zones 5% x / 8% y, adaptive EMA (0.08 slow, 0.30 fast), optional 1-euro (`min_cutoff=0.014, beta=0.0008`) or damped spring (response 0.18, damping 0.82, velocity cap), lost-subject hold 90 frames then drift to centre, continuous zoom to keep face occupancy near 40% with asymmetric zoom rates (in 0.05, out 0.12). Optional two-pass global smoothing: Savitzky-Golay (default), Kalman + RTS backward pass, or an L2 path optimiser penalising velocity and acceleration, then an AutoFlip-style `stationary_lock` that pins a scene to its median when the target spans under 15% of the frame. Research doc concluded dead-band 0.20 to 0.05 cut centring error about 30% with lower jerk.

Captions: ASS with `\k` karaoke tags and named presets; letterbox-aware placement.

Weaknesses: single call over the whole transcript (the clustering-near-the-start problem OpenShorts measured); Italian-streamer-specific copy rules baked into the default prompt; the prompt is long enough to dilute its own priorities; still text-only selection; lots of opt-in smoothing modes with no clear default winner beyond savgol.

### 3. xixihhhh/hotclip (257 stars, AGPL-3.0, very active)

What it does: Electron desktop app plus headless CLI and MCP server, fully local (sherpa/SenseVoice/Paraformer/Qwen ASR, any OpenAI-compatible LLM), aimed at Chinese livestream VODs but bilingual. Ships `skills/hotclip/SKILL.md` for agents.

Clip selection (`src/core/highlight/*`):
- The LLM never emits timestamps. It returns `quoteStart`/`quoteEnd` (verbatim, at least 6 words) plus sentence ids; `match.ts` reverse-matches the quotes onto the token stream (ladder: exact, anchored, segment fallback).
- "parts": 2-3 far-apart stretches may be stitched in source order (for "self-contradiction" clips), with an explicit rule that stitching must not manufacture meaning.
- Content-type triage first (content-in-the-words, reaction-driven, visual-driven) decides which evidence to trust (transcript vs vocal-emotion peaks vs chat density vs visual energy).
- `gate.ts` deterministic quality gate: dangling openers ("so", "but", "and", "then", "also", "because", "however", "anyway", "therefore"), endings on a comma, dense speaker switching; can only downgrade publish to review, never drop (fail-open).
- Optional vision review of candidates, a reference-clip mode that measures pacing of a viral example, review memory (past accept/reject) and performance memory fed back into the prompt.
- Its research doc (`docs/RESEARCH-2026-08-CLIP-QUALITY.md`) cites HIVE (EMNLP 2025): split editing into highlight detection plus separate opening and ending selection plus irrelevance removal.

Reframing (`reframe/track.ts`): YuNet face detector; per shot: coverage below 40% gives a centred crop; if every face position fits in one crop the camera locks for the shot (snapped to exact centre within 3.5%); std below 4% of width locks to the median; steady drift gives a 12-keyframe linear pan; otherwise 1-euro (`minCutoff 0.3, beta 0.007`) with a 2% dead zone; 1.25 s hold through detector dropouts; keyframes compiled to an ffmpeg `sendcmd` / crop expression; `evaluateCropCoverage` re-uses detections to prove how much of every face the crop keeps.

Captions (`subtitle.ts`): ASS presets karaoke, keyword (LLM-picked keywords tinted and enlarged), pop (damped bounce 0.8 to 1.04 to 1.0 over 165 ms, current word coloured 80 ms early), hormozi, minimal (2-4 word chunks, soft shadow, at most one highlighted word per chunk). Baseline at about 71% of frame height for platform UI clearance. A web-caption path renders an HTML template (`resources/caption-templates/bubble.html`) in an offscreen Electron BrowserWindow and composites it: in effect a local Remotion.

Effects: autozoom "breathing" 1.0 to 1.06 over a 10 s cycle plus 1.1 pushes 0.4 s before emphasis moments; sound design (whoosh on splice cuts, pop on hook appearance, ding on payoff, at most 3 per clip, synthesised locally with ffmpeg); BGM ducking 15-20 dB; filler and silence removal with a speech detector that refuses to cut gaps still containing speech; flash-forward cold open; render QA (black frames, long silences, loudness, mid-word cuts, platform-risk words) with automatic repair kept only when the re-check strictly improves.

Weaknesses: AGPL (cannot vendor code into a closed skill); Electron/pnpm heavy; Chinese-market tuning (Douyin, live selling) dominates defaults; English prompt is a translation of the Chinese one; autozoom breathing on a timer is the "random push-in" its own research warns against when no emphasis is supplied.

### 4. ColinGPT9/clips-studio (65 stars, AGPL-3.0, very active; many clones exist under other accounts)

What it does: Windows-first local app (bundled Ollama, Whisper, YOLO, PANNs, TalkNet) for streamers; gaming layouts, chat-moment detection, multilingual dubbing, publishing.

Selection (`analysis/fusion.py`, `config/prompts/*.txt`): two candidate pools, transcript picks from the LLM and signal windows where audio+visual excitement exceeds a percentile (their text scored by the LLM in one extra call); weighted fusion `w_text*text + w_visual*visual + w_reaction*reaction + w_audio*audio + w_engagement*engagement`; then a RERANK prompt that orders all finalists relative to each other, justified in code as "far more reliable for small local models than absolute 0-100 scoring, which clusters". Prompt adds a TRENDING & DRAMA axis (creator beef, public figures) weighted heavily.

Reframe: YOLOv8 pose; TalkNet-ASD (vendored, MIT) for who is speaking, with the documented finding that mouth-pixel motion differed by only 7% between speaker and listener on a real clip while TalkNet answers the question properly; boxes detected at 8 fps are interpolated to 25 fps for TalkNet (+15% cost vs +452% for re-detecting). `HoldMove` hysteretic controller: HOLD until drift exceeds 5.5% of width, then MOVE with smoothing 0.45 and pan-speed clamp 0.30 width/s until error falls under 1.2%; `stable_target` median of last 5 samples; `snap` at cuts.

Tighten (`analysis/tighten.py`): proposes (never applies) cuts for silences from `silencedetect` (not transcript gaps, because a gap may contain laughter) with MIN_GAP 0.55 s and KEEP_BREATH 0.15 s, and filler words limited to pure sounds ("um", "uh", "hmm"), keeping "like"/"so"/"you know" because they are often load-bearing.

Captions: ASS, 3 words per group, Arial 84 uppercase default, optional word highlight; an edit-chat prompt maps natural-language requests to render controls. Plain look.

Weaknesses: AGPL; Windows/CUDA orientation (RTX timings); caption styling basic; selection prompt permits the model to invent timestamps from segment times.

### 5. Anil-matcha/AI-Youtube-Shorts-Generator (5153 stars, MIT; SamurAIGPT redirects here)

What it does now: a thin client for MuAPI (download, Whisper, gpt-5-mini highlight ranking, `autocrop`), with a `--mode local` fallback (yt-dlp, faster-whisper, OpenAI/Gemini, OpenCV). Ships `.claude/skills/youtube-shorts-generator/SKILL.md`. README is largely an ad for the paid API.

Selection (`shorts_generator/highlights.py`, ported from "ViralVadoo"): content-type/density classification from the first 25 segments, then one call per 20-minute chunk (60 s overlap) with an 8-signal VIRALITY_CRITERIA list, score 0-100, `hook_sentence`, `virality_reason`; dedupe by >50% overlap.

Reframe (local mode): OpenCV Haar frontal-face cascade, largest face, EMA with `smoothing = 0.15` on the centre, no dead zone, no scene-cut reset; writes `mp4v` via OpenCV then muxes audio.

Captions: none. Effects: none.

Weaknesses (concrete):
- **Double-offset bug for videos over 30 minutes**: `build_transcript_text(chunk)` prints each segment's absolute `s['start']`, so the model returns absolute times, and `get_highlights` then adds the chunk `_offset` again (`h["start_time"] = float(h["start_time"]) + offset`). Every clip from chunk 2 onward points at the wrong place.
- Timestamps come from segment starts; no word snapping; clips can start or end mid-word.
- Haar misses profile and small faces; EMA without dead zone jitters on every detection; no hold on dropouts.
- `mp4v` intermediate plus re-encode loses quality.

### 6. modelscope/FunClip (6351 stars, MIT, active)

What it does: Gradio tool built on FunASR Paraformer (Chinese-first, hotword biasing via SeACo-Paraformer, CAM++ speaker diarization). You clip by selecting transcript text, by speaker id, or by letting an LLM choose.

Selection: default system prompt (translated): "You are a video SRT subtitle analysis clipper... analyse the exciting and as-continuous-as-possible segments and clip them, output at most four segments, merge temporally continuous sentences and their timestamps into one... output strictly as `1. [start-end] text`". Clips are located by exact text search in the recognised text (`trans_utils.proc`), mapping token indices to timestamps.

Reframe: none. Captions: MoviePy composite with a PIL-rendered TextClip (STHeiti font); plain.

Weaknesses: no vertical output; no virality judgment beyond "exciting"; regex-parsed LLM output; English support secondary.
Worth stealing: selecting a clip by quoting its text, and "clip everything speaker 2 said".

### 7. zhouxiaoka/autoclip (8986 stars, MIT, active; Tauri desktop, macOS Apple Silicon build)

What it does: Bilibili-style 2nd-creation tool. Steps: `step1_outline` (8-15 topics of 3-8 minutes from the transcript), `step2_timeline`, `step3_scoring`, `step4_title`, `step5_clustering` (group clips into collections), `step6_video`. Separate prompt sets per genre (business, knowledge, opinion, entertainment, experience, content_review, speech).
Scoring prompt: four principles (information value, emotional resonance, spread potential incl. quotable lines and memes, structural completeness), `final_score` 0.0-1.0 plus a 15-30 character recommendation.
Not a shorts tool: horizontal, multi-minute topic clips, no reframing, no captions styling of note. Relevant only for the genre-specific prompt idea and topic clustering into series.

### 8. ClipsAI/clipsai (543 stars, MIT, last push 2024-01-17)

What it does: Python library. `ClipFinder` runs TextTiling over sentence embeddings to find topic boundaries (clips 15-900 s); no notion of hooks or virality. `resize()` splits the video by pyannote speaker turns crossed with scene changes, detects faces with MTCNN (facenet-pytorch), clusters boxes with k-means (k = max faces in a frame), picks the face whose mouth aspect ratio (FaceMesh inner-lip landmarks) changes the most, and emits ONE static crop per segment; adjacent segments within 4% position difference merge.

Weaknesses: unmaintained, pinned old torch/pyannote, needs a HuggingFace token for pyannote; `_calc_crop` clamps x and y at 0 but not at the right/bottom edge; static per-segment crops cannot follow a moving subject; selection is topical, not engaging.
Worth stealing: speaker-turn x shot segmentation with one locked crop per segment is the right default for seated talking heads.

### 9. Shaarav4795/ClippedAI (210 stars)

Thin wrapper on clipsai. Selection: TextTiling clips filtered to a duration band, then `calculate_engagement_score = 0.45*min(words_per_sec/3,1) + 0.30*(share of words containing digits, "$" or "!") + 0.25*min(duration/75,1)`. Title from Groq. Captions: ASS at PlayResX/Y 1080x1920, Montserrat Extra Bold 80, outline 15, top-centre, words with digits or currency in a Yellow style, 25-character cues. Weakness: the "engagement" heuristic rewards long, fast, number-heavy clips regardless of content; interactive `input()` prompts; no word-level highlighting.

### 10. Upload-Post/skill-autoshorts (146 stars; author mutonby, same as OpenShorts)

What it does: a Claude Code / openclaw skill (`SKILL.md` 308 lines + `autoshorts.py`) that runs a daily loop: pick one video from a folder, Whisper, Gemini multimodal (uploads the video file and the word-timed transcript), cut with ffmpeg, overlay a PIL hook, present candidates for approval over a messaging bridge, publish approved clips via Upload-Post.

Selection: `ANALYZE_PROMPT` asks for all viable 20-60 s moments with `start` equal to an existing word start and `end` to an existing word end, multimodal cues (laughter, gestures, energy), `hook_text` max 8 words, `viral_score` 1-10.

Learning loops (the part worth stealing):
- `learn`: pulls platform metrics for published clips, splits top/bottom 20% by `0.6*views + 0.4*engagement_rate`, and asks Gemini to rewrite a `HOT.md` of falsifiable rules with evidence counts, capped at 80 lines, refusing to change much when evidence is thin (fewer than 5 winners or losers). HOT.md is injected as priors in the next analyze call.
- `reflect`: before metrics exist, learns the creator's own filter from approved vs rejected candidates.

Weaknesses: no reframing or captions (input must already be 9:16 with burned captions); Spanish defaults; publish step is the product.

### 11. alexfazio/viral-clips-crew (768 stars, MIT, last push 2026-02)

One GPT call returns clip TEXT (the prompt says "identify four 1-minute long clips" and later "Always return EXACTLY THREE clips"); on a count mismatch it inserts filler text. Three CrewAI agents on Gemini 1.5 then try to match each extract back to the SRT to recover timings. Cut and `subtitles=` burn with default style; no reframe. `__pycache__` committed. Obsolete; listed only because of its star count.

### 12. atherion005-byte/agent-opus (12 stars, MIT, one commit)

Ollama prompt with a keyword/punctuation heuristic fallback (power-word list, "?", "!", numbers, ASR confidence). Reframe: YOLOv8 person boxes at 5 fps, largest box centre, `uniform_filter1d` moving average over 2 s, linear interpolation. Zoom track: energy bumps around "power words" smoothed and mapped to 1.0-1.15. Captions: PIL-drawn karaoke and per-word pill styles composited in MoviePy. Weaknesses: person-box centre is not the head; moving average lags symmetric around cuts and bleeds across scene changes; Windows CUDA setup only.

### 13. yukitorido/short-video-generator-AI (722 stars, created 2026-09-23): MALWARE

The single commit (author "Minister", weappawq179@outlook.com) is a patchwork of unrelated code (a Telegram crypto "GoblinMine" tapper bot in `src/launcher.py`, OnlyFans-scraper filters in `src/base/flags.py` and `src/other.py`, an Anthropic tool base class, a `Detector.score` that returns `random.uniform(20, 90)`). `main.py` imports `src.fs` and calls `fs.run_sync()`; `src/fs.py` decodes XOR-obfuscated names for `hashlib`, `zlib`, `hmac` and `builtins`, decrypts a large byte blob with an HMAC keystream, zlib-decompresses it and passes it to `builtins.exec(..., globals())` at import time. This is a loader. 722 stars in four days is purchased. Do not run `pip install` or `python main.py`. The README text is copied from Anil-matcha.

### 14. ghost1412/shorts-generator (6 stars)

Mostly a faceless AI content generator (TTS, ComfyUI backgrounds, trend scripts, Stripe/Supabase SaaS) with a "Smart Crop & EMA Face Tracking" switch and a Remotion `ShortFlow` composition. Not a serious clipper.

---

### Best clip-selection prompts, verbatim

#### (1) OpenShorts two-pass: score every window, then detail the shortlist
Source: mutonby/openshorts `gemini_worker.py` (MIT). Pass 1 excerpt:

```
RANK these candidate windows by how well each would work as a standalone short.
- Score EVERY window in this batch: exactly one entry per input window, with
  the id you were given. Do not drop the weak ones — say they are weak.
- `score` must be an integer from 0 to 100, and the ranking is what matters:
  use the whole range instead of clustering. Most windows of a normal video
  are not clippable, so reserve 70+ for the ones that pass the test below,
  and put weak filler, housekeeping, outros, rambling transitions and
  low-signal padding under 30 even when the topic is interesting.
- THE 2-SECOND TEST is the main criterion: would the first 2 seconds of this
  moment force a cold viewer (no context) to keep watching? Windows that only
  work with prior context score low.
```

Pass 2 excerpt:

```
- THE 2-SECOND RULE: the clip MUST open on its strongest moment. If the first
  2 seconds would not stop a cold viewer from scrolling, move the start or skip the clip.
- STANDS ALONE: the clip must make sense to someone who has seen nothing else.
  If it opens on a pronoun, a "that", a "so anyway", or an answer whose question
  was asked earlier, move the start back to where the idea begins or skip it.
  A brilliant moment that needs the previous five minutes is not a clip.
  Fix this by moving the START earlier, never by cutting the ending short: a
  clip that loses its payoff to gain context has traded down.
- DIVERSITY: never return two clips that make the same point, tell the same
  story, or land the same joke — even across different windows.
- ABOUT THIS MOMENT, NOT THE VIDEO: the hook and the title name the concrete
  thing that happens inside this clip — the tool being set up, the action,
  the number, the claim, the name. [...] If nothing concrete can be
  named, quote the clip's strongest sentence instead of summarising the topic.
- `why`: one sentence, max 20 words, naming what makes THIS moment worth a
  clip — the specific hook, claim, number or payoff, not the topic.
```

And the code-level contract around it (clip_selection.py): windows on segment boundaries, global top-N shortlist, clip-count floor with a recovery call, keep-by-score, `snap_clip_to_words` (quoted in the word-snapping section below).

#### (2) ClippyMe gate + 5-axis rubric + timestamp anchoring
Source: fralapo/clippyme `src/clippyme/pipeline/gemini_request.py` (MIT).

```
## IS THIS MOMENT EVEN WORTH CUTTING? (gate — apply BEFORE scoring)
A clip must hit at least ONE of these HARD. A moment that is merely pleasant,
well-spoken or on-topic is NOT a clip, however clean the audio is.
1. UNEXPECTED TURN — plot twist, pattern interrupt, someone contradicting what
   they just said, a reveal nobody saw coming. The surprise is the product.
2. STRONG EMOTION OR POLARIZATION — [...] The test: would a
   viewer send this to a friend or drop it in a group chat?
3. RELATABILITY — "this is literally me". Specific and everyday, not abstract.
4. NEW OR USEFUL INFO — a fact, number, trick or broken misconception a viewer
   would SAVE for later.
Emit FEWER, harder clips rather than padding the list with competent-but-flat
moments: a weak clip costs the account more than a missing one.
The reaction beat is PART of the clip — the laugh, the silence after the reveal,
the "cosa?!". End after it lands, never before.

## VIRAL_SCORE RUBRIC (1–100)
Score each axis from 1 to 20 and sum (cap at 100):
- HOOK_STRENGTH: do the first 1–3s grab attention? [...] a moment whose best beat is buried at 0:20 scores low here even if that beat is great.
- EMOTIONAL_PAYOFF: is there an actual turn or reaction [...] Score the surprise and the reaction, not the subject matter.
- QUOTABILITY: is there a line viewers would screenshot, repeat, or argue with?
- SELF_CONTAINED: makes sense without context from the rest of the video?
- DENSITY: no dead air, no rambling, every second earns its place.

- ANCHOR TO REAL TIMESTAMPS: `start` MUST equal the `s` (start) of the FIRST
  word of the opening sentence in the WORDS section, and `end` MUST equal the
  `e` (end) of the LAST word of the closing sentence. Do NOT invent times between
  words and do NOT round to whole seconds [...]
```
Plus its grounding rule for titles: "every element of a title must be traceable to something that actually happens or is actually said in THAT clip [...] Exaggerate the FRAMING, never invent the EVENT."

#### (3) HotClip: quote, don't timestamp; stitch only if meaning survives
Source: xixihhhh/hotclip `src/core/highlight/prompt.ts` (AGPL-3.0; ideas only, do not copy code).

```
【Viral material is RARE】
In a two-hour stream, under five minutes is usually worth clipping. Most of it is filler. Returning two or three genuine hits beats padding the list [...]

【First work out what this footage IS, then decide which evidence to trust】
- Content-in-the-words (selling / lecture / interview / commentary / review): the highlight is what was said — judge from the transcript
- Reaction-driven (gaming / chat / outdoor / sports): [...] Lean on vocal-emotion peaks and live-chat spikes
- Visual-driven (dance / singing / scenery): the transcript is essentially empty [...]

5. Jokes: only as a complete setup→punchline unit. A clip where the audience laughs but the punchline itself is missing is NEVER acceptable

【Hard rules】
1. Select ONLY from the transcript verbatim: quoteStart/quoteEnd must be copied character-for-character (punctuation included) — never paraphrase, never invent
4. Do not output clock timestamps (hh:mm:ss) — the system reverse-matches the text you quoted
6. Never quote-mine: the clipped meaning must match what was actually said. A "hook" manufactured by cutting a sentence in half will backfire on the account
- Stitching must never manufacture a meaning that was not there. If the gap contains a "but/however" that reverses it, or the second part is actually about something else, don't stitch — drop the candidate.
```
Paired with the deterministic gate (`gate.ts`): `DANGLING_OPENER_EN = /^(?:so|but|and|then|also|because|however|anyway|therefore)\b/i`, endings on a comma, and dense speaker switching downgrade a candidate to "review".

#### Honourable mentions
- clips-studio `config/prompts/rerank.txt`: "Order ALL {count} clips from MOST likely to go viral to LEAST. Judge them against each other [...]" with the code comment that relative ordering is more reliable than absolute scores, which cluster.
- skill-autoshorts `LEARN_META_PROMPT`: "Each bullet is a single, actionable, falsifiable rule. Avoid platitudes ('be engaging'). Cite sample sizes when meaningful: '(seen in 4/5 winners, 0/5 losers)'. [...] If the evidence is weak (fewer than 5 winners or 5 losers), output the existing HOT.md with at most a single appended bullet".
- Anil-matcha VIRALITY_CRITERIA (8 ranked signals: hook, emotional peak, opinion bomb, revelation, conflict, quotable one-liner, story peak, practical value) is the most copied list in the ecosystem (clips-studio and yukitorido reuse it).

### Word snapping (the most useful non-prompt selection code)
Source: mutonby/openshorts `clip_selection.py` (MIT), abridged:

```python
# START: snap to the nearest word start, then lead into the silence before it.
candidates = [s for s in starts if abs(s - new_start) <= search_window]   # 1.5 s
if candidates:
    word_start = min(candidates, key=lambda s: abs(s - new_start))
    prev_ends = [e for e in ends if e <= word_start]
    gap = max(0.0, word_start - max(prev_ends)) if prev_ends else None
    lead = min(max_lead, gap / 2) if prev_ends else max_lead               # max_lead 0.35
    new_start = max(0.0, word_start - lead)
# END: same with max_tail 0.45 into the following silence,
# then repair min/max duration while staying on word boundaries.
```

---

### Best reframing / smoothing code, verbatim

#### (1) HotClip per-shot planner: lock if you can, pan if drifting, 1-euro only when you must
Source: xixihhhh/hotclip `src/core/reframe/track.ts` (AGPL; reimplement, do not copy).

```ts
// Comfort-first composition: if every observed face position fits in one
// crop, lock the virtual camera for the entire shot.
if (!hasRecovery && envelopeWidth <= cropFrac) {
  let center = (envelopeLeft + envelopeRight) / 2;
  if (Math.abs(center - 0.5) <= CENTER_SNAP_DISTANCE) center = 0.5;   // 0.035
  keyframes.push({ t: filled[0].t, x: clampX(center), hold: true });
  continue;
}
if (std < STATIC_STD) {                                              // 0.04 of width
  keyframes.push({ t: filled[0].t, x: clampX(median), hold: true });
} else {
  const drift = xs[xs.length - 1] - xs[0];
  if (!hasRecovery && Math.abs(drift) > 2 * std) {                   // steady drift: linear pan
    /* 12 evenly spaced keyframes from xs[0] to xs[0]+drift */
  } else {
    const euro = new OneEuro();                                      // minCutoff 0.3, beta 0.007
    for (const f of filled) {
      const smoothed = euro.filter(f.cx, f.t);
      if (lastX === null || Math.abs(smoothed - lastX) > DEAD_ZONE)  // 0.02 of width
        keyframes.push({ t: f.t, x: clampX(smoothed) });
    }
  }
}
```
Supporting pieces: shots split at scene cuts, `LOST_HOLD_SEC = 1.25` hold through dropouts, a crop-coverage check that reports the least-visible face per sampled frame.

#### (2) Hysteresis controller: hold still, move deliberately, settle
Source: ColinGPT9/clips-studio `video/framing.py` (AGPL) with the same design in fralapo/clippyme `PanSmoother` (MIT, quoted here):

```python
class PanSmoother:
    def __init__(self, deadband_frac=0.04, settle_frac=0.005, alpha=0.2): ...
    def smooth(self, target_x, frame_width):
        if target_x is None:
            return self.center                      # bridge single-frame dropouts
        if self.center is None or frame_width <= 0:
            self.center = float(target_x); self.moving = False
            return self.center
        err = float(target_x) - self.center
        if not self.moving:
            if abs(err) <= self.deadband_frac * frame_width:
                return self.center                  # HOLD: noise never reaches the crop
            self.moving = True
        self.center += self.alpha * err             # MOVE: exponential ease
        if abs(float(target_x) - self.center) <= self.settle_frac * frame_width:
            self.moving = False                     # settle and lock again
        return self.center
```
clips-studio's `HoldMove` adds a pan-speed clamp (`max_pan_speed=0.30` width/s), feeds it a 5-sample median (`stable_target`) and `snap()`s at cuts.

#### (3) Offline global path smoothing (for a two-pass, analyse-then-render skill)
Source: fralapo/clippyme `reframe_ops.py` (MIT; ported from mfahsold/montage-ai).

```python
def solve_camera_path_l2(values, lambda_smooth=100.0, lambda_trend=10.0, constraints=None):
    """Minimises Σ(xₜ−cₜ)² + λ_smooth·Σ(xₜ−xₜ₋₁)² + λ_trend·Σ(xₜ−2xₜ₋₁+xₜ₋₂)²"""
    c = np.asarray(values, dtype=float); n = len(c)
    d1 = np.eye(n - 1, n, k=1) - np.eye(n - 1, n, k=0)
    d2 = (np.eye(n - 2, n, k=0) - 2.0 * np.eye(n - 2, n, k=1) + np.eye(n - 2, n, k=2))
    a = np.eye(n) + lambda_smooth * (d1.T @ d1) + lambda_trend * (d2.T @ d2)
    b = c.copy()
    for idx, target in (constraints or {}).items():   # manual keyframes, strong pull
        a[idx, idx] += 1e4; b[idx] += 1e4 * float(target)
    return np.linalg.solve(a, b)

def stationary_lock(xs, ys, frame_w, frame_h, threshold=0.15, snap_center_dist=0.10):
    # AutoFlip-style: if the target spans < threshold of the frame on both axes,
    # pin the whole scene to its median; snap to exact centre if close.
```
Also in the same file: a Kalman + RTS backward smoother that extrapolates through detection gaps, Savitzky-Golay, 1-euro, a damped spring with a velocity cap, and `asymmetric_zoom_step` (fast pull-back, slow push-in) with `zoom_for_face_height` targeting 40% face occupancy.

#### (4) OpenShorts jump confirmation and scene snap (online)
Source: mutonby/openshorts `main.py` (MIT):

```python
if abs(new_center - self.target_center_x) > self.safe_zone_radius:
    # Same big move as last time? Count it. Otherwise start counting
    # afresh — two contradictory outliers must not confirm each other.
    if (self._pending_target is not None
            and abs(new_center - self._pending_target) <= self.safe_zone_radius):
        self._pending_count += 1
    else:
        self._pending_target = new_center
        self._pending_count = 1
    if self._pending_count < self.jump_confirm_frames:   # 3
        return  # not convinced yet — hold the frame
```
`begin_scene()` drops the pending jump and cuts (not pans) to the first face of the new shot; the comment records the bug it fixed ("a headless torso for 1.5s after every cut while the frame slid over to the speaker").

#### Active-speaker choice
- Best: TalkNet-ASD (clips-studio `video/asd.py`), audio-visual sync model, with the measured observation that mouth-pixel motion differs by only about 7% between speaker and listener.
- Good and cheap: OpenShorts `active_speaker.py` per-speaker percentile normalisation of mouth motion, audio RMS gate, 3-window hold.
- Acceptable for one-off offline work: clipsai MAR variance per k-means face cluster per speaker turn.

---

### Recurring weaknesses across these apps

1. Selection is text-only. Only skill-autoshorts (Gemini on the file) and hotclip/OpenShorts (optional frame checks) let a model see or hear delivery; laughter, pauses, facial reaction and on-screen content are invisible to the scorer in every default path.
2. Absolute 0-100 "viral scores" from one call; hotclip's research and clips-studio's code both note they cluster and mean little. Few use pairwise or listwise reranking.
3. Timestamps invented by the LLM or snapped to segments instead of words (Anil-matcha, clips-studio, viral-clips-crew, FunClip). Only OpenShorts (snap), ClippyMe (copy word `s`/`e`), hotclip (quote and reverse-match) and autoshorts (word rule) handle it.
4. One call over the whole transcript clusters picks near the start (OpenShorts measured it); chunking implementations have bugs (Anil-matcha double offset).
5. Hook overlays are generated clickbait ("POV: ...", "Stop doing this!") rather than the speaker's own strongest line; titles drift from what the clip delivers unless a grounding rule exists.
6. Reframing defaults to a single-face tracker with per-frame EMA; jitter, lag, head cut-offs after scene cuts, and no concept of "this shot should not move". Only hotclip and ClippyMe (opt-in) plan per shot.
7. Captions are libass karaoke with a colour swap and at best a scale pop; no layout awareness of the speaker's face, no per-word physics, no emphasis logic tied to meaning. Remotion-quality typography exists only in OpenShorts' preview path and hotclip's HTML template.
8. Zooms, SFX and B-roll are either absent or triggered by loudness, "power word" lists or timers, which reads as twitching (OpenShorts documents its own 8.4 pushes per minute).
9. No verification of the output: apart from hotclip's render QA (mid-word cuts, silences, loudness, black frames) and OpenShorts' measurement comments, nothing checks the rendered file against the plan.
10. Heavy, fragile installs: Docker + CUDA + YOLO + MediaPipe + pyannote HF tokens + Gemini keys; several are Windows/CUDA first. Star counts are unreliable and the category now attracts malware (yukitorido, and two more star-farmed repos on the same topic page).

### Which repos matter most

1. mutonby/openshorts: two-pass windowed selection, word snapping, jump confirmation, scene snap, split layout with seam captions, audio-gated ASD. MIT, so code can be borrowed.
2. xixihhhh/hotclip: quote-don't-timestamp, stitch rules, rule gate, per-shot lock/pan/track planner, crop-coverage QA, render QA with repair, sound-design and caption research. AGPL, so ideas only.
3. fralapo/clippyme: the rubric and grounding rules, plus the most complete MIT library of camera-path smoothers (1-euro, spring, Savitzky-Golay, Kalman-RTS, L2 path, stationary lock, asymmetric zoom) and a docs folder analysing a dozen other reframe repos.
4. ColinGPT9/clips-studio: TalkNet active-speaker detection with the interpolation trick, HoldMove, signal fusion plus listwise rerank, conservative filler/silence tightening. AGPL, ideas only.
5. Upload-Post/skill-autoshorts: multimodal Gemini on the file and the HOT.md / reflect learning loops, packaged as an agent skill.

---

## Part 3. Agent skills and agent-first editors for video editing, clipping, reels and captions

Survey date: 2026-09-27. Scope: Claude Code / Codex / generic agent skills (SKILL.md packages) and agent-first editors that cut talking-head footage, clip long videos into shorts, or caption and dress footage. Every repo below was cloned (depth 1) into `scratchpad/ref/` or `scratchpad/ref/skillsC/` and read; star counts come from `gh api repos/...` on the survey date.

### At a glance

| Project | Stars | License | Last push | What it is | Usefulness for a talking-head reel skill |
|---|---|---|---|---|---|
| browser-use/video-use | 27,380 | MIT | 2026-09-24 | General "edit by conversation" skill: Scribe transcript, packed transcript, EDL, ffmpeg render, self-eval | Very high (architecture, hard rules, self-eval loop) |
| heygen-com/hyperframes (skills: talking-head-recut, embedded-captions, media-use) | 53,574 | Apache-2.0 | 2026-09-27 | HTML+GSAP renderer with agent skills; captions with subject matte occlusion | High (caption craft, preview-before-render, gates) |
| nateherkai/hyperframes-student-kit | 1,047 | custom (NOASSERTION) | 2026-09-25 | 15 skills; short-form-edit, cut-silences, cut-mistakes, validators | Very high (editorial gates, plan validator with negative controls) |
| remotion-dev/skills (official) | 4,741 | none stated | 2026-09-25 | Remotion best-practice skills incl. captions, silence detection, sfx | Medium (API correctness, captions primitives) |
| AgriciDaniel/claude-shorts | 217 | MIT | 2026-07-11 | Long-to-short clipper: faster-whisper, Claude scoring rubric, MediaPipe reframe, Remotion captions | High (clip-selection rubric, boundary snapping) |
| louisedesadeleer/clipify | 580 | MIT | 2026-08-24 | Clip funny moments, active-speaker pan via ROI motion, ASS captions | Medium (cheap speaker detection, verify-in-frame rule) |
| mariagorskikh/talking-head-reel (reference, see Part 1) | 56 | MIT | 2026-09-22 | Multi-take phone recording to reel, Remotion overlays | Baseline |
| a-prs/remotion-video-onboarding | 1 | none | 2026-09-02 | Russian-language onboarding + talking-head pipeline: Silero VAD map, retake finder, snap cuts | High for cut accuracy (word-time repair) |
| jincheng2026/jc-remotion-skills | 14 | NOASSERTION | 2026-08-22 | Chinese "koubo" MG packaging on Remotion; three QC gates, adversarial judge agent | High for QC design |
| haidrrrry/claude-remotion-skill | 207 | MIT | 2026-08-12 | Motion-graphics craft rules for Remotion | Low-medium (motion rules only) |
| EdYuTo/yt-video-creator | 0 (created 2026-09-26) | none | 2026-09-27 | Folder of footage to YouTube long-form or Short with Remotion; plan.json, contact sheets, YuNet faces | Medium-high (render versioning, mlx-whisper, ffmpeg gotchas) |
| Vincentwei1021/anything2explainer | 2,108 | PolyForm Noncommercial | 2026-09-18 | Topic to narrated explainer; quantitative frame QC | Medium (QC metrics, sync-frame sampling) |
| cuixiangyu789-gif/SmartCut | 1 | none | 2026-09-20 | Chinese single-speaker rough cut: keep/delete/review JSON on word_ids, FCP7 XML export | Medium (decision contract, NLE export) |
| natyang1234/auto-edit-video-skill | 1 | MIT | 2026-08-15 | Agent-first conservative auto-edit with risk tiers, re-transcription after cut | Medium |
| vincentventalon/claude-code-video-editing-skill | 2 | MIT | 2026-09-25 | One-command rough cut: silence islands, keep last take | Medium (island method) |
| agenticluke/claude-skill-video-editing-plus (fork of affaan-m/ECC video-editing, ECC 268k stars) | 0 / 268,259 | MIT | 2026-08-05 / 2026-09-24 | Generic ffmpeg + Remotion editing advice | Low |
| Jaycheng1103/chatgpt-video-editing-skills | 571 | MIT | 2026-07-26 | Wrapper over video-use, eight steps, trigger evals | Low-medium (evals file) |
| assafkip/claude-video-editor | 19 | NOASSERTION | 2026-06-12 | Plugin bundling video-use + student-kit skills + generated footage | Low (derivative) |
| Kappaemme-git/codex-video-short-maker-skill | 35 | MIT | 2026-05-01 | Silence-only shortener, blurred-bg vertical, PIL captions | Low |
| vizance/codex-talking-head-video-editor | 45 | none | 2026-07-18 | Chinese tutorial: letterboxed horizontal talk into 9:16 template | Low |
| 6missedcalls/video-editing-skill | 37 | MIT | 2026-02-27 | Bash + ffmpeg + whisper: trim, jumpcut, "hormozi" captions | Low |
| kwindla/skill-caption-clip | 2 | none | 2026-01-27 | yt-dlp + Deepgram + SRT burn | Low |
| Vossy/claude-video-editing-skill | 0 | MIT | 2026-09-27 | Drives the closed "Shorz" desktop app over MCP (160+ tools) | Low (closed engine) |
| pireel/pireel | 1,234 | AGPL-3.0 | 2026-09-18 | Open-source timeline editor drivable by agents | Low-medium (human-editable output idea) |
| nexu-io/html-video | 4,622 | Apache-2.0 | 2026-06-21 | Meta-layer over HyperFrames templates | Low |
| digitalsamba/claude-code-video-toolkit | 2,136 | MIT | 2026-09-21 | Generative explainer toolkit (TTS, FLUX, LTX-2, Remotion) | Low (no footage editing) |
| coreyhaines31/marketingskills `video` | 51,668 (repo) | MIT | 2026-09-05 | Tool-chooser prose for marketing video | Low |

Out of scope here but found: `mutonby/openshorts` (the original OpenShorts, MIT, MCP server; see Part 2), wonda.sh clipping CLI (commercial).

---

### 1. browser-use/video-use (27,380 stars, MIT, pushed 2026-09-24)

The most influential skill in the space; several others (Jaycheng1103, assafkip) wrap it outright.

**What it does.** "Edit any video by conversation." Drop footage in a folder, run Claude Code there, get `<videos_dir>/edit/final.mp4`. Talking heads, montages, tutorials, interviews. No reframing to vertical in the tool itself (portrait sources are just scaled by height).

**How the agent sees video (the core idea).** Two layers (`README.md`):
- Layer 1, always loaded: one ElevenLabs Scribe call per source (`model_id: scribe_v1`, `diarize: true`, `tag_audio_events: true`, word-level) packed by `helpers/pack_transcripts.py` into `takes_packed.md`, phrase lines broken on silence >= 0.5 s or speaker change, each prefixed `[start-end]` with a speaker tag. "~12KB" for a session, "1/10 the tokens of raw JSON".
  ```
  ## C0103  (duration: 43.0s, 8 phrases)
    [002.52-005.36] S0 Ninety percent of what a web agent does is completely wasted.
  ```
- Layer 2, on demand: `helpers/timeline_view.py <video> <start> <end>` renders a PNG with a 10-frame filmstrip, an RMS waveform envelope, word labels above it and shaded silences >= 400 ms. "Not a scan tool — use it at decision points." README framing: "Naive approach: 30,000 frames × 1,500 tokens = 45M tokens of noise. Video Use: 12KB text + a handful of PNGs."

**Pipeline.** Inventory (ffprobe, batch transcription with 4 workers, pack) → pre-scan for verbal slips → converse (questions shaped by the material) → propose a 4 to 8 sentence strategy and wait → execute (editor sub-agent writes `edl.json`; animations built by parallel sub-agents, one per slot) → `render.py --preview` → self-eval → iterate → append to `project.md` (session memory).

**Cut selection.** LLM from the packed transcript; explicitly anti-heuristic ("Hand-tuned moment-scoring functions. The LLM picks better than any heuristic you'll write."). The editor sub-agent brief (verbatim excerpt, `SKILL.md`):
```
You are editing a <type> video. Pick the best take of each beat and
assemble them chronologically by beat, not by source clip order.
...
RULES:
  - Start/end times must fall on word boundaries from the transcript.
  - Pad cut boundaries (working window 30–200ms).
  - Prefer silences ≥ 400ms as cut targets.
  - Unavoidable slips are kept if no better take exists. Note them in "reason".
  - If over budget, revise: drop a beat or trim tails. Report total and self-correct.
OUTPUT (JSON array, no prose):
  [{"source": "C0103", "start": 2.42, "end": 6.85, "beat": "HOOK",
    "quote": "...", "reason": "..."}, ...]
```
Structural archetypes offered: "Tech launch / demo: HOOK → PROBLEM → SOLUTION → BENEFIT → EXAMPLE → CTA", tutorial, interview, documentary, etc. Cut craft: "Silences ≥400ms are usually the cleanest. 150–400ms phrase boundaries are usable with a visual check. <150ms is unsafe"; "Extend past punchlines to include reactions — the laugh IS the beat."

**EDL format.** JSON: `sources` map, `ranges[]` with `source,start,end,beat,quote,reason`, `grade`, `overlays[]` (`file,start_in_output,duration`), `subtitles`, `total_duration_s`. The `reason` and `quote` fields make every cut auditable.

**The 12 hard rules** (the part worth copying almost verbatim): subtitles applied LAST in the filter chain; per-segment extract then lossless `-c copy` concat; 30 ms audio fades at every boundary; overlays shifted with `setpts=PTS-STARTPTS+T/TB`; master SRT on output-timeline offsets; never cut inside a word; pad every edge 30 to 200 ms ("Scribe timestamps drift 50–100ms"); word-level verbatim ASR only, never normalized fillers; cache transcripts; parallel sub-agents for animations; strategy confirmation before execution; all outputs in `<videos_dir>/edit/`.

**Rendering path (`helpers/render.py`).** Per segment: `-ss` before `-i`, HDR detection with a zscale+tonemap chain for iPhone HLG/PQ sources (a real bug others ignore), scale, optional grade (`grade.py` auto mode samples frames and caps corrections at ±8 %), `afade` 30 ms both ends, libx264, one frame rate resolved for the whole render. Then concat demuxer `-c copy`, then one filter graph with PTS-shifted overlays and `subtitles=...:force_style=...` last, then two-pass loudnorm (-14 LUFS, TP ≤ -1). Quality ladder: draft 720p ultrafast CRF 28, preview CRF 22, final CRF 20.

**Captions.** libass via SRT + `force_style`: Helvetica 18 Bold white, black outline 2, `MarginV=90` (commented as a platform safe-zone rule for 9:16). Chunker `chunk_words`: 2 words target, grows to 3 if the cue would flash under 0.35 s, breaks on punctuation or a 0.3 s pause. No active-word highlight, no animation. Functional, not attractive.

**Effects.** Grades (auto, `neutral_punch`, `warm_cinematic`), overlay animations built by sub-agents in HyperFrames, Remotion, Manim or PIL; music and SFX guidance ("~20 stock whooshes ... in 18s reads as generic; ~8 reads as designed"; "Hit on the frame": measure a sound's attack and start the file that many seconds early; duck music -12 to -15 dB under speech). No zooms, no reframing, no face tracking.

**Verification loop.** Step 7 "Self-eval (before showing the user)": run `timeline_view` on the rendered output at every cut boundary ±1.5 s; check discontinuity, waveform spike (pop), subtitle hidden by overlay, misaligned overlay; sample first 2 s, last 2 s and 2 to 3 midpoints; ffprobe duration vs EDL; measure loudness with `ebur128` and per-section RMS ("You cannot listen: say so, and report the numbers"). For anything published: spawn a critic sub-agent "Brief it to roast, not to praise: a verdict, ranked problems with timecodes and evidence ... and the 5 fixes to do first." Cap at 3 self-eval passes.

**Weaknesses.** Captions are plain SRT (no karaoke, no design); no vertical reframing, no face tracking, no zoom grammar; depends on a paid cloud ASR (ElevenLabs Scribe) and explicitly discourages local Whisper ("Running Whisper locally on CPU. Slow and it normalizes fillers."), which ignores Apple Silicon mlx-whisper; no clip-finding mode for long sources (it assembles takes; it does not score viral moments); the "verify" images are 320 px filmstrips, too small to judge caption legibility at phone size; `--edl` full-project view is "not implemented yet".

---

### 2. HyperFrames' own skills (heygen-com/hyperframes, 53,574 stars, Apache-2.0, pushed 2026-09-27)

Relevant skills in `skills/`: `talking-head-recut` (1,218 lines), `embedded-captions` (260 lines plus a large `references/` and `scripts/` tree), `media-use`. Each asks the agent to run `npx hyperframes skills update <name>` first (self-updating skills).

**talking-head-recut.** Packages an existing talking-head clip with designed cards; "the clip plays untouched underneath" (no cutting). Local Whisper via `npx hyperframes transcribe ... --model small.en`, agent corrects ASR in place keeping timestamps, writes `storyboard.json` of cards with `intent`, `startSec/endSec`, `zone` (`fullscreen`, `lower-third`, `side-panel`, `video-overlay`, `whiteboard-area`). Card count formula: base pace by duration (< 60 s reel: 6 to 8 s per card) × density multiplier (0.7 / 1.0 / 1.5), floor 5 cards. Useful production tip, verbatim: "RE-ENCODE with dense keyframes. Sources with a sparse GOP (keyframe interval > ~1s) freeze on seek in the renderer (a frozen frame under the overlays); -g / -keyint_min set to your composition fps make every frame seekable." Reframing: none beyond layout zones; `media-use/references/operations.md` reframes 16:9 to 9:16 with a centered `crop=ih*9/16:ih`. Verification: `npx hyperframes snapshot public --at 5` single frames, lint.

**embedded-captions** (the most sophisticated caption system surveyed).
- Caption model, verbatim: "Every spoken phrase is one of three things: drop (filler) / rail (the default — ordinary spoken content, verbatim, clean lower-third subtitle, in front) / embed (a promoted peak — one big word composited behind the subject)". "The rail carries most of the text; embed is the scarce, earned peak." "≤1 hero per block ... never two co-visible."
- Subject occlusion: `scripts/matte.cjs` runs `hyperframes remove-background` (u2net_human_seg, ~9 fps on CoreML, 168 MB model) to produce per-frame RGBA foreground PNGs, so text can sit behind the head.
- Scene analysis: `safe-zones.cjs` computes hug-left/hug-right strips next to the silhouette, a hero band, luminance, palette sampled from footage, light direction.
- Decision gate before anything: refuse multiple speakers or hard cuts, burned-in captions (checked on a 1 fps contact sheet: `ffmpeg -i in.mp4 -vf "fps=1,scale=160:-1,tile=10x5" sheet.png`), garbage transcript, near-silent audio ("Whisper hallucinates words like 'Thank you.' over silence").
- Luminance probe for caption region: "under 60 → light text reads as-is, 60-180 → add the glyph scrim, 180+ → opaque text + scrim (never bare light text)".
- Rail rules (`references/rail.md`): lower third, portrait "~600–700px from the bottom (clear of platform UI)", ≤ 2 lines, 32 to 42 chars/line, one group on screen, ≥ 0.5 s per group, word timings within 80 ms of transcript, size `calc(0.045 * var(--h))`, active-word pop ≤ 1.1×, motion 150 to 250 ms fades only.
- Grouping (`references/caption-grouping.md`): break on pause ≥ 500 ms, sentence end, comma + pause ≥ 250 ms, discourse reset ("but", "so"), or 6 words / 2.5 s; min 2 words, min 0.5 s; `in = w[0].start - 0.08`, `out = min(next.in - 0.05, last.end + 0.6)`.
- Verification: `preview-frames.cjs` composites "faithful preview frames in ~2s each" without a render ("A full render costs minutes — never use it to discover layout problems"); five failure checks (washout, text-on-text, reading order, hero presence, balance) plus five positive checks; gates in `render-and-composite.sh` (`check-timing.cjs` drift tolerance 0.08 s, `check-occlusion.cjs`, `check-overflow.cjs`); and "Fresh-eyes review ... give it ONLY the preview sheet + this checklist and ask for PASS/FIX verdicts per frame."
- Ten "DNA" visual languages (cream, ink for bright scenes, editorial, keynote, documentary, loud, neon, glitch, chrome, velocity) and 35 catalog identities.

**Weaknesses.** Does not cut footage; talking-head-recut is 1,200 lines of prose the agent must hold; reframing is a centered crop; u2net matting flickers on busy handheld footage (the skill says so); requires Node 22 + headless Chrome; matting a 60 s clip at ~9 fps is minutes of compute.

---

### 3. nateherkai/hyperframes-student-kit (1,047 stars, custom license, pushed 2026-09-25)

Fifteen skills mirrored for Claude Code and Codex. Relevant: `short-form-edit` (328 lines + 5 references + 2 validators), `cut-silences`, `cut-mistakes`, `short-form-video` (legacy), `edit-video`, `video-storytelling`.

**Pipeline (short-form-edit).** Probe → transcribe (ElevenLabs Scribe default) → optional reference-reel analysis saved as `REFERENCE-ANALYSIS.md` → asset shortlist with exact usable intervals before concept lock → silence and mistake tools plus a full manual transcript read ("a zero-candidate report can miss an obvious retake") → cut locked after rough animatic → `DESIGN.md`, beat plan, `OPEN-LOOPS.json` → three different rough openings compared → low-res moving animatic → graphics bound to spoken words → music bed and SFX from a visual-event map → gates → `VERIFY.md` with output hash.

**Selection rubric: the first-three-seconds gate**, verbatim: "The first creative gate is: 'In the first 3 seconds is someone convinced they need to watch until the end?' Establish a specific reason to stay and earn its payoff inside the video." And: "Build three materially different rough openings using the same truthful source speech. Compare the first three seconds for topic clarity, curiosity, muted comprehension, and follow-through." Open-loop ledger schema: `{id, question, object, setup, updates[{time,state}], closure, resolution, supportingSpeech}` with an `opening {benefit, evidenceBy3, payoffTime}`. Honesty rules: "Never manufacture retention scores or call internal hook comparisons an audience A/B test"; "Do not invent a product result simply to make a more satisfying payoff."

**cut-mistakes** (`scripts/find-cut-candidates.mjs`): mechanical candidates only, review-gated. Stutters (same token, gap < 0.5 s), retakes via Jaccard similarity of stop-word-filtered 18-token signatures of segments (≥ 0.34, or ≥ 0.24 with the same opening), false starts (same opening, first take < 6 s, restart within 12 s). Default removes the earlier take. Output JSON + Markdown with context, confidence and recommendation. Skill text: "Deciding what counts as a mistake is judgment, not a formula — emphatic repetition ('never, never') and rhetorical doubling ... look identical to a stutter mechanically."

**cut-silences.** Gap threshold 0.55 s; trimmed pauses keep a scaled breath (0.24 s after long pauses, 0.20 s after sentence end, 0.14 s otherwise).

**Captions.** Legacy karaoke in HTML: per-word `<span data-word-start>` with GSAP 0.08 to 0.12 s pops, Montserrat 900 46 to 58 px, active word scale 1.08 + accent color, "Stroke via layered text-shadow, NEVER -webkit-text-stroke (renders inconsistently in Chromium render)", no pill. Retiming through a `shift(originalTime)` function.

**Validators** (the best in the survey). `validate-plan.mjs` checks: caption word count equals retained word count; each caption word within 5 ms of the transcript; every word maps into exactly one kept source range; scenes contiguous and frame-aligned; each scene has an anchor phrase within -0.15/+0.2 s of its cut; B-roll files exist; any visual-event gap > 2.2 s needs a `holdReason`; caption groups do not truncate words or overlap. `validate-footage.mjs` hashes B-roll and rejects reused scenes. `validate-beat-sync.mjs` enforces `-0.2s <= (wordStart - beatStart) <= 1.8s`. `build-edl-review.mjs` builds an HTML page with kept/cut regions on a timeline and both videos side by side. Quality-gates doc, verbatim: "Calibrate new validators with negative controls. A caption shifted by 0.3 seconds, a one-frame scene gap, and an omitted spoken word should fail the relevant checks. Do not make the validator accept the current output merely to reach green."

**Verification loop** (legacy short-form-video): render draft, extract 8 to 15 frames at word-exact timestamps ("Not round numbers. Not mid-scene. The exact word."), "Call Read on every PNG ... Do NOT just list filenames", fix, re-verify, then spot-check the final encode. Also "Build final face crops from the native-resolution source rather than a downscaled editing proxy."

**Weaknesses.** Enormous prose load (short-form-edit + references + MOTION_PHILOSOPHY + hyperframes skills) invites skipped steps; no face tracking or automatic reframing; relies on Kie.ai generated B-roll for a lot of its look; verification evidence is Windows-only; many gates are editorial self-assessment the same agent performs.

---

### 4. remotion-dev/skills (official; 4,741 stars; pushed 2026-09-25; skills versioned 4.0.529)

`remotion-captions` defines the `Caption` JSON type (`text, startMs, endMs, timestampMs, confidence, pageBreakAfter`), transcription via `@remotion/install-whisper-cpp`, and display via `createTikTokStyleCaptions({captions, combineTokensWithinMilliseconds: 1200})` with active-token highlight (`token.fromMs <= t < token.toMs`). `remotion-markup` has current API guidance: `@remotion/media` `<Video trimBefore>`, `crop*` props, `TransitionSeries` ripple editing, `Interactive.Div` for Studio-editable keyframes, `output: 'perceptual-scale'` for scale interpolation, `@remotion/sfx` (hosted whoosh, vine-boom, etc.), `@remotion/rough-notation` highlights, light leaks, motion blur. `silence-detection.md` is adaptive: measure `loudnorm` `input_thresh`, then `silencedetect=noise=${THRESH}dB:d=0.5`.

**Weaknesses.** Primitives only: no editorial workflow, no reframing, no clip selection, no verification loop. Caption example is a centered green-highlight default. Note the reference skill pins `remotion 4.0.245` with `OffthreadVideo`; the current API is several hundred patch versions ahead. html-video's README notes Remotion is "Source-available, paid above 4 devs" (Remotion's company license); worth checking for Acme.

---

### 5. AgriciDaniel/claude-shorts (217 stars, MIT, pushed 2026-07-11)

**Pipeline (10 steps).** Preflight → faster-whisper large-v3 (GPU) producing both WhisperX-style segments and Remotion `captions[]` → content-type detection (talking-head, screen, podcast) → Claude reads transcript + rubric, scores 8 to 12 candidates of 15 to 55 s → table presented, user picks via AskUserQuestion, style and platform chosen → timecode adjustment loop → `snap_boundaries.py` → stream-copy extraction + `compute_reframe.py` → Remotion render → per-platform export → `validate.sh`.

**Clip-selection rubric** (`references/scoring-rubric.md`), verbatim core:
```
| Hook strength        | 0.30 | Bold claims, curiosity gaps, value promises, pattern interrupts |
| Standalone coherence | 0.25 | Makes complete sense without any context from the rest of the video |
| Emotional intensity  | 0.20 | Strong opinions, surprise reveals, humor, passion |
| Value density        | 0.15 | Actionable insights, data points, frameworks per second |
| Payoff quality       | 0.10 | Satisfying conclusion — punchline, reveal, call-to-action |
```
Hook archetypes with score bands ("Bold/Contrarian 80-100 ... Weak/Generic 'So today I want to talk about...' 10-40"), boosters (+5 to 10 for a specific number, a named entity, personal experience), coherence red flags ("As I mentioned earlier...", "Pronouns without clear referents"), selection guidelines ("Minimum score threshold: 60", "Diversity: Don't select 5 segments about the same subtopic", "Spacing: Prefer segments at least 2 minutes apart in source"), hook overlay text "should NOT duplicate the first spoken words".

**Boundary snapping.** Start to nearest word boundary preferring sentence starts; end extended to next `.?!` if within 3 s; +300 ms tail; silencedetect near cut points; clamp 5 to 60 s.

**Reframe.** MediaPipe FaceDetection (model_selection=1) on only 5 sampled frames per clip, largest face chosen; screen recordings get cursor tracking by frame differencing with a 5-point moving average. Static crop for talking heads.

**Captions.** Remotion components: Bold (Montserrat 800 uppercase, 72 px, 800 ms pages, spring pop `{mass:1, damping:12, stiffness:200}`, yellow active word, 4-way text-shadow outline), Bounce (Bangers), Clean (Inter). Plus a hook overlay and progress bar. Transcript cleanup removes fillers from caption text while keeping timestamps.

**Weaknesses.** Extraction with `-c copy` lands on keyframes, so the snapped boundaries are not what gets cut; face tracking on 5 frames is a static guess and picks the biggest face, not the speaker; rubric is generic marketing virality (rewards "Everything you know about X is wrong", which is engagement bait for a serious author); caption cleanup can make captions disagree with audio; no post-render visual inspection, only `validate.sh` technical checks.

---

### 6. louisedesadeleer/clipify (580 stars, MIT, pushed 2026-08-24)

**What it does.** Finds funny dialogue moments or repeated impact actions, cuts them, reframes 16:9 to 9:16 (pan between faces or split screen), speed-ramps reveals, burns "opus-style" ASS captions.

**Selection.** Whisper `tiny.en` word timestamps; agent scans for punchlines ("what", "wait", "no way", laughter), reversals, awkward pauses, quotable one-liners; proposes `[start, end, why-it's-funny, title]`, 10 to 25 s clips, user confirms. Action mode uses spectral flux in 1 to 6 kHz to find strikes. Useful rule, verbatim: "Audio detection ≠ visible event. Always run Step 1.5 (verify each candidate frame) before rendering."

**Reframing (cheap active-speaker detection).** The agent eyeballs two mouth+chin ROIs from one probe frame (drawn back with `drawbox` for verification, "Iterate at most twice"), ffmpeg measures per-frame motion energy in each ROI (`tblend=all_mode=difference,signalstats` YAVG), `analyze.py` normalizes, smooths with a 15-frame moving average, switches speaker only when the other side exceeds by a 1.15 margin (hysteresis), merges segments < 1.0 s, and `build_pan.py` emits a nested `if(lt(t,...))` crop-x expression with hard cuts. Split-screen variant stacks two 1080×960 tiles with the active speaker on top.

**Captions.** `build_ass.py`: PlayRes 1080×1920, Arial Black 100, outline 8, shadow 3, MarginV 280, fixed 3-word chunks, one Dialogue event per word with the active word colored `&H0000FFFF&` (yellow). Karaoke preset 4 words green; minimal Helvetica.

**Weaknesses.** Fixed-count chunking ignores phrase boundaries; ROI boxes are hand-estimated and static (breaks on camera cuts, which the skill warns about); motion energy mistakes gestures and nodding for speech; no smoothing of camera position (hard cuts only); `-c copy` trims; Arial Black is not guaranteed on macOS (libass falls back silently).

---

### 7. a-prs/remotion-video-onboarding (1 star, no license, pushed 2026-09-02; Russian)

Onboarding plus a real talking-head pipeline, validated on "9:43 → 1:12, 26 segments". The low star count hides the most careful cut engineering in the survey.

- **Unified speech map via Silero VAD** (`scripts/vad.py`, `vad_model.py`), used for both pause cuts and retake cuts.
- **Word-time repair before anything else** (`fix_word_times.py`), translated from the docstring: Whisper timestamps "systematically diverge from the sound": `end` is set to the start of the next word, so a word before a pause "occupies" silence (one word lasted 9.58 s, 23 of 297 words were affected), and a `start` can land entirely in silence (1.84 s early). After re-seating words on the VAD map, "eight of nine boundaries landed on a real pause by themselves."
- **Retake finder** (`find_repeat_candidates.py`): exact repeated phrase chunks and prefix matches ("a shorter chunk's words == a prefix of a later chunk's words (the stutter/false-start case)"), because a speaker restarting with different lengths never produces identical n-grams. Candidates only; the agent applies semantic rules ("when in doubt, do not cut", never cut punchlines).
- **snap_cuts.py**: moves boundaries onto the speech map only when safe, redistributes words stranded inside a cut onto the surviving speech so captions do not lose audible words, and handles takes Whisper merged into one phrase via explicit `spans` and `wordMoves`.
- **clean_audio.py**: diagnose first, repair only what is broken; "a single loudnorm pass is dynamic (acts like a compressor) and pulls up the noise floor along with quiet speech; static gain + limiter (computed here) leaves the floor where it was." No neural denoiser because DeepFilterNet-class models are GPL-3.0 and heavy.
- Regression tests for each script.

**Weaknesses.** Russian-only docs; onboarding-heavy SKILL.md; graphics mode is a primitive bank; no reframing.

---

### 8. jincheng2026/jc-remotion-skills (14 stars, NOASSERTION, pushed 2026-08-22; Chinese)

Six skills for "koubo" (talking-head) MG packaging from a rough cut + SRT, with a 45-file component substrate (BigNumber, Stamp, QuoteDoc, CompareCard, TimelineCard, PersonCard, ...) and pipeline scripts.

**QC design (the reason to read it).** "Three QC gates: geometric assertion scripts → independent QC agent reads frames and scores → user final review." The judge is a separate agent (`agents/mg-judge.md`, tools Read/Bash/Grep/Glob, cannot edit), translated: "The generator will confidently praise its own mediocre output, so you must be harsh — 'probably fine' is a fail." Rubric (`references/rubric.md`): four dimensions scored 0 to 10 (layout, beat alignment, craft, anti-AI-look/originality), "any dimension < 7 or any FAIL-level violation = send back", every violation must cite a frame number and a concrete fix. The key check, translated: pick 3 to 5 key entities from the SRT (names, numbers, verdict words) and verify that at the moment each is spoken the frame shows it legibly; "said X, X not shown = FAIL" (added after a segment scored 8/8/8/8 and the user still rejected it because a named person never appeared). The judge must state that motion feel is a still-frame blind spot and leave it to the user.

**Automated probe** (`scripts/qc-master.mjs`, cross-platform Node): faststart box order, `blackdetect=d=0.1:pix_th=0.10`, `freezedetect=n=-50dB:d=0.3` (noise-tolerant; md5/mpdecimate were fooled by compression noise) with freeze = FAIL when the presenter is on screen, loudness, expected duration. `check-subs.mjs` checks line width, dangling single characters, orphaned Latin letters, overlaps. Incremental rendering (a segment in ~2 min, a SFX change in ~5 min). A "mistakes book" of 34 documented failures.

**Weaknesses.** Chinese-only; tuned to one house style copied from a benchmark creator; very long rule corpus; takes a pre-cut video and SRT as input (no cutting, no reframing).

---

### 9. haidrrrry/claude-remotion-skill (207 stars, MIT, pushed 2026-08-12)

Motion-graphics craft for Remotion. Ten "non-negotiable" rules: no linear interpolation, entrances animate 2 to 3 properties, stagger 3 to 6 frames, exits faster than entrances, a five-layer stack (bg mesh → assets → type → grade → grain + vignette), Ken Burns on stills, idle breathing, timing from fps, one theme object, and "Render, extract frames, LOOK at them, fix, re-render." Verification via `npx remotion still ... --frame N` at chosen frames. Failure list includes "Emoji as icons ... silently break the one-hero-color rule" and "`gap`/`margin` in `em` resolves against the PARENT font-size". Synthesizes its own SFX kit in Node when none exists.

**Weaknesses.** Aimed at generated motion graphics, not footage; its "every scene needs grain and gradient mesh" rule would wreck a talking-head reel; captions are a 10-line pointer to `createTikTokStyleCaptions`.

---

### 10. EdYuTo/yt-video-creator (0 stars, created 2026-09-26, no license)

Folder of footage → Remotion long-form or Short. The agent "can't watch video or hear audio, so the workflow runs on proxies for both: contact sheets ... transcripts". Edit written as `plan.json` in source time; `build_edit.py` generates `src/edit-data.ts` and `edit-map.json` ("the ground truth for 'what's at 3:34'"). Speech: mlx-whisper or faster-whisper in a private venv, a small model to skim and large-v3-turbo for chosen windows. Verified in practice and written down as gotchas:
- "Homebrew ffmpeg is often broken (`Library not loaded: libx265.215.dylib`) ... The scripts use Remotion's bundled binary."
- "Force the language. Whisper auto-detects from the first 30 s; one waiter speaking Japanese turned 40 min of Portuguese into repeated nonsense Japanese."
- "Energy-based silence detection doesn't work in noisy rooms."
- Render versioning: `render.mjs` renders to a temp file and moves the previous output to `out/versions/<name>-vN` with the plan snapshot; "Never overwrite or delete an existing render".
- Privacy scan with OpenCV YuNet (`faces.py scan --edges`) to find bystanders for blurring.
- 9:16 crops: agent reads subject x-position per shot from contact sheets ("Only ~32% of a 16:9 frame's width survives").
- Verification: fine contact sheet of the render every 2 s, `audio_levels.py` (talk ≈ -20 dBFS, music-only 6 to 8 dB below, peak < -1 dBFS).

**Weaknesses.** Static per-shot crop x chosen by eye; captions are simple subtitles; brand new and untested by others.

---

### 11. Vincentwei1021/anything2explainer (2,108 stars, PolyForm Noncommercial, pushed 2026-09-18)

Topic to narrated explainer (not footage editing), but its QC protocol (`reference/agent-qc-rules.md`, Chinese) is the most quantitative. Translated highlights: to check sync, "look at the frames at subtitle-block start −6, 0, +3, +8"; element appears more than 3 frames late or 6 frames early = medium; a whole sentence with no visual change = high. Flicker check: "for each element entrance frame compute the luminance curve over f0…f0+12; a 0/0.5/1 jump = flicker." `frame_metrics.py` measures subject scale, empty-frame runs, glow area, longest static stretch per shot; `motion_check.py` flags stills > 3 s. QC agents append findings to a file as a table `severity | shot | frame | symptom | criterion | fix`.

**Weaknesses.** Noncommercial license; hours of wall clock per video; black-canvas house style only.

---

### 12. cuixiangyu789-gif/SmartCut (1 star, no license, pushed 2026-09-20; Chinese)

Three separated stages: content decision (LLM) → frame-exact virtual timeline → FCP7 XML export for DaVinci Resolve / Premiere. The decision prompt (`剪辑决策提示词_v0.1.md`, translated excerpts): "Content not marked delete is kept by default. When unsure output review; risky deletion is forbidden." "For a slip and restart, prefer deleting the wrong or abandoned version and keep the last correct, complete, natural version." "Pauses cannot be judged by duration alone. Pauses with emphasis, emotion, transition or thinking function must be kept." "You must identify content ranges with word_ids that really exist in the input. Do not invent word_ids, timecodes, frame numbers." Pace profiles (`editing_pace_profiles.json`): natural / compact / energetic with join handles 0.30 / 0.20 / 0.12 s, tail handles, waveform search windows, speech protection, quiet thresholds; sentence gaps compressed to 15 frames. Boundary "mistakes book" as structured feedback.

**Weaknesses.** Prototype; Doubao ASR (Chinese cloud); no rendering, no captions.

---

### 13. natyang1234/auto-edit-video-skill (1 star, MIT, pushed 2026-08-15)

Agent-first conservative auto-edit with an optional loopback Studio GUI. `references/EDITING_RULES.md`: candidate classes (silence, filler, stutter, repetition, false_start) analyzed independently; risk tiers (low: clear silence, isolated hesitation, literal stutter contained in the kept phrase; high: full-sentence deletion, "two similar sentences with different nouns, figures, negation, or qualifiers", technical-term retries) with "When uncertain, default to keep." "After the cut, re-extract audio and transcribe the rendered cut" and keep a `cut_map.json`. Glossary-based subtitle calibration rules `canonical=alias|alias`.

**Weaknesses.** Large, Traditional-Chinese-first, local-Ollama context pass; the five "director profiles" are heuristics.

---

### 14. vincentventalon/claude-code-video-editing-skill (2 stars, MIT, pushed 2026-09-25)

One command rough cut. Method: split audio into "islands" between silences, transcribe each island separately with whisper.cpp large-v3-turbo, drop empty and filler-only islands, drop earlier takes when a later island "starts like" it (keep the last take), write `edited.takes.tsv` listing every island kept or not. Then the agent reads the kept lines "like an editor" for rephrased retakes the script cannot see and reruns with `--cut A:B` or `--protect A:B` without re-transcribing. "In doubt, keep: a repeat left costs a second pass, a sentence lost costs the video."

**Weaknesses.** Retake detection limited to shared openings; no captions styling, no reframing.

---

### 15. affaan-m/ECC video-editing skill and agenticluke/claude-skill-video-editing-plus

ECC (268k stars) ships a generic `video-editing` skill: pipeline "Screen Studio → Claude → FFmpeg → Remotion → ElevenLabs/fal.ai → Descript/CapCut", batch cuts with `-c copy` (keyframe-inaccurate), centered crop for 9:16. The fork adds VFR normalization, a CSV EDL (`source,start,end,label,notes`), timestamp-uncertainty caveats and a padded-letterbox option. **Weakness:** advice, not a pipeline; no captions design, no tracking, no verification beyond "preview".

### 16. Jaycheng1103/chatgpt-video-editing-skills (571 stars, MIT)

Eight fixed steps wrapped around video-use (Traditional Chinese). Two useful additions: explicit consent before the first upload to ElevenLabs, and an `evals/evals.json` of trigger and behavior cases (positive, negative, dirty repo, missing key, cloud-upload consent) plus a recorded baseline of generic behavior. **Weakness:** no new editing capability.

### 17. Smaller skills (brief)

- **Kappaemme-git/codex-video-short-maker-skill (35):** silencedetect-only shortening "not content-aware yet", keeps earliest non-silent segments until target length; vertical = blurred background fill; PIL-burned captions; hard-coded author paths.
- **vizance/codex-talking-head-video-editor (45):** one Markdown file that installs a Codex skill: horizontal talking head letterboxed into a 1080×1920 template with title, Traditional Chinese captions and CTA.
- **6missedcalls/video-editing-skill (37):** Bash + ffmpeg + Whisper; jumpcut via silencedetect; "hormozi" SRT style.
- **kwindla/skill-caption-clip (2):** yt-dlp section download, Deepgram nova-2, SRT burn.
- **assafkip/claude-video-editor (19):** plugin bundling video-use + student-kit skills + keyframe-animated generated footage.
- **Vossy/claude-video-editing-skill (0):** instructions for driving the closed Shorz desktop app over MCP; clip selection happens inside the app.
- **pireel/pireel (1,234, AGPL):** open timeline editor with an agent plugin; the idea worth noting is that agent output lands in a human-editable timeline.
- **nexu-io/html-video (4,622):** meta-layer over HyperFrames templates; Remotion adapter planned.
- **digitalsamba/claude-code-video-toolkit (2,136):** generative (TTS, FLUX.2, LTX-2, ACE-Step) explainers; no footage clipping.
- **coreyhaines31/marketingskills `video`:** tool-chooser prose; claims HyperFrames is "Basic (CSS transitions)" versus Remotion, which is outdated given HyperFrames' GSAP pipeline.

---

### Best ideas worth stealing (with attribution)

1. **Read the video, do not watch it**: packed phrase-level transcript as the primary view plus on-demand filmstrip+waveform+word-label PNGs at decision points (video-use `pack_transcripts.py`, `timeline_view.py`).
2. **Hard production rules separated from taste**: subtitles last, per-segment extract then `-c copy` concat, 30 ms afades, PTS-shifted overlays, output-timeline caption offsets, never cut inside a word, 30 to 200 ms padding (video-use).
3. **Repair Whisper word times against a VAD speech map before any cut decision**; whisper `end` values bleed into pauses and `start` values land in silence (a-prs `fix_word_times.py`, `snap_cuts.py`). Redistribute words stranded by a moved boundary so captions keep audible words.
4. **Prefix-match retake detection** for restarts of different lengths, alongside exact repeats and Jaccard similarity (a-prs `find_repeat_candidates.py`; student kit `find-cut-candidates.mjs`); keep candidates review-gated because emphasis looks like stutter.
5. **Silence islands transcribed separately** so takes are not merged by Whisper; `takes.tsv` of every island kept or cut; `--cut/--protect` reruns without re-transcribing (vincentventalon).
6. **Decisions reference transcript word ids only; the model never invents timecodes**; keep/delete/review with review never auto-deleted (SmartCut); risk tiers where anything changing a claim, number, negation or qualifier is high risk (natyang).
7. **Weighted clip rubric**: hook 0.30, standalone coherence 0.25, emotion 0.20, value density 0.15, payoff 0.10, threshold 60, diversity and 2-minute spacing, hook text must not duplicate the first spoken words (claude-shorts).
8. **First-three-seconds gate and open-loop ledger**, three distinct openings compared on a cheap animatic, "never manufacture retention scores" (student kit `short-form-edit`).
9. **Rail + embed caption model**: verbatim readable rail carries the transcript; one earned peak word per block is promoted and composited behind the subject using a human matte; luminance probe decides scrim; grouping on pauses ≥ 500 ms / comma+250 ms / 6 words / 2.5 s (HyperFrames `embedded-captions`).
10. **Preview composites before rendering** (~2 s per frame) and a fresh-eyes sub-agent that sees only the preview sheet and a checklist (HyperFrames `preview-frames.cjs`).
11. **Adversarial judge agent that cannot edit**, four scored dimensions, send back if any < 7, violations cite frame numbers and fixes, and the "said X, show X" entity check (jc-remotion-skills `mg-judge`, `rubric.md`); critic brief "roast, not praise" (video-use).
12. **Validators with negative controls**: caption words 1:1 with retained transcript words within 5 ms, every word inside one kept range, frame-aligned scenes, anchor within -0.15/+0.2 s of cut, event gaps > 2.2 s need a reason, and each check proven to fail on a 0.3 s caption shift, a one-frame gap and a dropped word (student kit `validate-plan.mjs`, `quality-gates.md`).
13. **Word-exact frame sampling** for verification: frames at spoken-word timestamps, not round numbers, and Read every PNG (student kit); sync check at cue start −6, 0, +3, +8 frames; luminance-curve flicker test (anything2explainer).
14. **Automated technical QC**: `blackdetect`, `freezedetect=n=-50dB:d=0.3` with presenter-on-screen freeze = FAIL, faststart, LUFS, duration (jc `qc-master.mjs`); `ebur128` per section and "you cannot listen: say so, and report the numbers" (video-use).
15. **Audio**: static gain + limiter instead of one-pass dynamic loudnorm on quiet phone speech (a-prs `clean_audio.py`); SFX aligned on measured attack, fewer effects tied to visible events, music ducked 12 to 15 dB (video-use).
16. **Cheap active-speaker detection** from mouth-ROI motion energy with hysteresis (1.15 margin) and a minimum dwell (clipify `analyze.py`); "verify each candidate frame is actually in shot" (clipify).
17. **HDR-to-SDR tonemap for iPhone HLG sources** before any grade (video-use `render.py`); dense-keyframe re-encode (`-g fps -keyint_min fps`) before browser rendering to avoid frozen seeks (HyperFrames `talking-head-recut`).
18. **Render versioning**: never overwrite a render; move the previous one to `out/versions/` with its plan snapshot (yt-video-creator `render.mjs`).
19. **Apple Silicon practicalities**: mlx-whisper, force `--language`, Remotion's bundled ffmpeg when Homebrew ffmpeg is broken (yt-video-creator).
20. **Session memory and explicit consent**: `project.md` appended per session (video-use); consent before first cloud upload of footage, plus trigger/behavior evals (Jaycheng1103).
21. **Human-editable exit**: FCP7 XML for Resolve/Premiere (SmartCut) or Studio-editable Remotion keyframes via `Interactive.*` (remotion-dev/skills), so the user can fix one cut by hand.

### Recurring weaknesses a superior skill must fix

- **Reframing is the weakest link among the skills** (the apps in Part 2 do better). Center crop (ECC, HyperFrames media-use), a static crop from 5 sampled frames choosing the largest face (claude-shorts), hand-drawn static ROIs with hard-cut pans (clipify), per-shot x read by eye (yt-video-creator), blurred-background fill (Kappaemme). No skill does per-frame face tracking with smoothing, dead-zone and speaker awareness, and none reframes from native resolution with a zoom grammar tied to cuts.
- **Stream-copy cuts after careful boundary snapping** (claude-shorts, clipify, ECC): `-c copy` lands on keyframes and silently undoes the snapping.
- **Trusting raw Whisper word times.** Only a-prs repairs them; others pad blindly or cut on `end` values that bleed into pauses. Several do not force the language.
- **Captions either plain or generic.** SRT with force_style (video-use), fixed 3-word chunks (clipify), centered TikTok pages with one highlight color (remotion-dev, claude-shorts). Few are phrase-aware, few check readability against the background, and only HyperFrames avoids covering the face with a computed safe zone.
- **Caption text diverging from audio**: filler removal on caption text only (claude-shorts), editorial "condensing" (HyperFrames grouping) without a check that every retained word appears once.
- **Selection rubrics reward engagement bait** ("Everything you know about X is wrong" scores 80 to 100) and generic virality; none has a notion of the speaker's own voice, of claims that must keep their qualifiers, or of a lane/brand.
- **Self-grading by the same agent.** Most "verify" steps ask the generating agent to look at its own frames; only jc-remotion-skills, HyperFrames and video-use (for publishable work) use a separate critic, and only the student kit calibrates validators with negative controls.
- **Verification at the wrong scale and time**: tiny filmstrips, round-number timestamps, no phone-size check, no word-exact sampling, no fresh ASR on the final audio (only the student kit and natyang re-transcribe the render).
- **Heavy prose, few scripts.** 300 to 1,200-line SKILL.md files with the rules in prose; the reliable parts (validators, repair scripts) are rare and short. Skills that are mostly prose drift between runs.
- **Environment fragility**: GPU-only faster-whisper defaults (claude-shorts), hard-coded author paths (Kappaemme), Homebrew ffmpeg breakage, Node 22 + Chrome requirements, cloud ASR as a hard dependency (video-use, student kit).
- **No long-source clipping in the editors, no editing in the clippers.** video-use and the student kit assemble takes but do not mine a 60-minute lecture for moments; claude-shorts and clipify mine moments but do not remove stumbles, retakes or pauses inside the chosen clip.
- **Overwrites and lost versions**: only yt-video-creator protects prior renders.
- **Licensing blind spots**: Remotion's company license, PolyForm Noncommercial (anything2explainer), AGPL (pireel), GPL denoisers; only a-prs and html-video mention license at all.

---

## Part 4. Renderers, caption engines, reframing and cut engines

Scope: the layers underneath a clipping skill. How captions and motion graphics get drawn onto footage, how a landscape frame gets reframed to 9:16 with a smooth virtual camera, how dead air gets cut. Everything here was read from source (shallow clones under `scratchpad/ref/`, or `gh api repos/.../contents/...`) on 2026-09-27. Stars and push dates come from the GitHub API on that day.

### Summary table

| Project | Role | Render path | Stars | License | Last push | Verdict |
|---|---|---|---|---|---|---|
| remotion-dev/remotion (+ `@remotion/captions`) | React video engine | Chrome Headless Shell screenshots per frame, bundled ffmpeg | 60,736 | Remotion License (free for individuals and companies up to 3 employees) | 2026-09-27 (v4.0.529) | Best motion graphics per unit of effort; slow renders; licence caveat |
| remotion-dev/template-tiktok | Official TikTok caption template | Remotion | 282 | template, UNLICENSED package.json | 2026-09-05 | Minimal reference, one highlight colour, one enter spring |
| heygen-com/hyperframes | HTML-to-video engine plus 21 agent skills | Puppeteer + chrome-headless-shell; BeginFrame on Linux, screenshot mode on macOS; system ffmpeg | 53,574 | Apache-2.0 | 2026-09-27 (v0.8.80, releases daily) | Strongest caption craft and QA gates in the survey; high churn |
| francozanardi/pycaps | CSS-styled captions for video | Playwright Chromium screenshots of each word state, composited by `movielite` (Numba) | 217 | MIT | 2026-06 | Pretty static styles, limited animation vocabulary, alpha |
| unconv/captacity | Whisper + MoviePy captions | MoviePy 1.x `TextClip` (ImageMagick), PIL blur | 139 | MIT | 2024-06 | Broken on a fresh install (imports `moviepy.editor`, moviepy unpinned) |
| gyoridavid/short-video-maker | Faceless TTS + Pexels + captions, MCP server | Remotion | 1,379 | MIT | 2025-06 | Not a talking-head tool; caption code is basic |
| muneebkhan08/Capite (and its sibling nicolaigaina/ai-video-captions) | Whisper + ASS animated captions, 27 presets | pysubs2 ASS, ffmpeg/libass burn | 6 / 63 | MIT | 2026-09-21 / 2026-03 | Best ASS tag recipes found |
| nik-devs/ffmpeg-caption-burn-ass | words.json to ASS, one ffmpeg pass | libass | 0 | MIT | 2026-09-26 | Small, clean, production-used |
| jianfch/stable-ts | Whisper timestamp stabilisation, ASS/SRT export | writes ASS with `\1c` highlight or `\kf` karaoke | 2,281 | MIT | 2026-05 | Timing quality layer, not a renderer |
| midrender/revideo | Motion Canvas fork with headless render API | Puppeteer | 4,066 | MIT | 2026-07 | Viable, generator-function scenes, smaller ecosystem |
| motion-canvas/motion-canvas | Editor-first animation tool | in-browser editor export | 19,187 | MIT | 2026-07 (last release v3.18.0-alpha.0, Feb 2025) | Wrong fit for footage overlays |
| Google MediaPipe AutoFlip | Saliency-aware reframing | C++ graph (Bazel) | 37,093 (mediapipe) | Apache-2.0 | autoflip unmaintained | Best camera-path ideas; not practical to build |
| AhmedHisham1/pyautoflip | Python AutoFlip reimplementation | OpenCV, InsightFace, MediaPipe, UNISAL ONNX | 23 | MIT | 2026-09-19 | Useful camera-mode logic and split-screen rule; heavy deps |
| fralapo/FrameShift | Per-scene stationary crop | YOLOv11n-face + MediaPipe fallback, OpenCV | 14 | MIT | 2026-06-18 | Simple, honest, no tracking inside a shot |
| WyattBlue/auto-editor | Silence/motion cutting, now in Nim, with skills | own libav pipeline | 5,371 | Unlicense | 2026-09-19 | Best silence-cut semantics; ships Claude skills |

### 1. Remotion, `@remotion/captions`, template-tiktok

**What it is.** React components render each frame in Chrome Headless Shell; Remotion screenshots each frame and encodes with its own bundled ffmpeg (`@remotion/compositor-darwin-arm64`), so it does not depend on Homebrew's ffmpeg build. Video footage is decoded by a Rust compositor behind `<OffthreadVideo>`, which gives frame-exact seeking.

**Captions package** (`packages/captions/src`, read via gh api): `Caption = {text, startMs, endMs, timestampMs, confidence, pageBreakAfter?}`; `createTikTokStyleCaptions({captions, combineTokensWithinMilliseconds, breakOnSilenceAfterMilliseconds?})` returns pages of tokens; `ensureMaxCharactersPerLine`, `parseSrt`, `serializeSrt`. A page breaks when the accumulated span exceeds `combineTokensWithinMilliseconds`, when a pause exceeds `breakOnSilenceAfterMilliseconds`, or at an explicit `pageBreakAfter`. Tokens keep leading spaces so the renderer can use `whiteSpace: "pre"`. Adjacent packages worth knowing: `@remotion/elevenlabs` (ElevenLabs transcript to `Caption[]`, relevant because this project already uses ElevenLabs speech-to-text), `@remotion/openai-whisper`, `@remotion/install-whisper-cpp`, `@remotion/whisper-web`, `@remotion/rounded-text-box` ("TikTok-like multiline text box SVG path with rounded corners"), `@remotion/sfx`, `@remotion/layout-utils` (`fitText`, `measureText`), `@remotion/animation-utils`, `@remotion/light-leaks`, `@remotion/motion-blur`, `@remotion/transitions`.

**template-tiktok** (`src/CaptionedVideo/*`): whisper.cpp 1.6.0 `medium.en` via `@remotion/install-whisper-cpp` with `tokenLevelTimestamps: true, splitOnWord: true`; pages every 1200 ms; each page enters with `spring({damping: 200, durationInFrames: 5})` scaling 0.8 to 1 and sliding 50 px; `fitText` caps the font at 120 px within 90 percent width; text is uppercase TheBoldFont, `WebkitTextStroke: "20px black"` with `paintOrder: "stroke"` (the trick that gives a thick outline without eating the glyph), active token turns `#39E508`. That is the whole style. It is a teaching template: no safe zones, no per-word pop, no emphasis tagging, no emoji.

**Looks.** Anything CSS/SVG/canvas/WebGL can draw: springs, per-word transforms that reflow correctly, colour emoji, gradients, blurred shadows, masks, Lottie, rounded plates. The reference skill `talking-head-reel` (Part 1) shows what a careful Remotion overlay grammar looks like at 1080x1920.

**Speed and fragility on Apple Silicon.** The reference skill measured roughly 4 fps for 2,500 portrait frames with one `OffthreadVideo`, about 10 minutes for 80 s, at concurrency 8. It also documents a real failure: `ENOSPC` inside `/var/folders/.../react-motion-render*` caused by swap pressure from eight headless Chromes, with a chunked two-tab fallback. Hardware encoding exists on macOS (`--hardware-acceleration if-possible`; ProRes from v4.0.228, H.264/H.265 from v4.0.236, per remotion.dev/docs/hardware-acceleration) but the bottleneck is the browser screenshot, not the encoder. `--gl=angle` is the desktop recommendation for GPU-heavy content, with the documented caveat "Memory leaks are a known problem with `angle`". Chrome Headless Shell is downloaded automatically.

**Licence.** Free for individuals and for-profit organisations with up to 3 employees; otherwise a Company License is required (`LICENSE.md`). personal use is fine; a company-wide pipeline might not be.

**Weaknesses.** Render speed; memory; the 3-employee licence line; a bundler step; React is more verbose for an agent than plain HTML. None of these affect output quality.

### 2. HyperFrames (HeyGen)

**What it is.** Compositions are plain HTML with `data-start`, `data-duration`, `data-track-index` on `.clip` elements; animation comes from any seekable runtime (GSAP, CSS, WAAPI, Lottie, Three.js, Anime.js) registered on `window.__timelines`. `@hyperframes/engine` drives chrome-headless-shell through Puppeteer and pipes frames to ffmpeg. Native `<video>` elements are replaced during capture by pre-extracted frames (`videoFrameInjector.ts`: "replaces native <video> elements with pre-extracted frame images during rendering"). The encoder detects VideoToolbox (`chunkEncoder.ts`).

**macOS specifics.** `browserManager.ts` only requests `HeadlessExperimental.beginFrame` capture when `process.platform === "linux"` with `--enable-begin-frame-control`; on macOS it runs in screenshot mode. Output is still deterministic because timelines are seeked, not played, but the strongest determinism guarantee is Linux-only. Requirements: Node 22+, system FFmpeg.

**Caption craft (skills/embedded-captions).** The most sophisticated caption system in the survey:
- A caption model with three classes per phrase: `drop` (filler, stutters, self-corrections), `rail` (verbatim lower-third, in front), `embed` (a single peak word composited behind the speaker). Rule: "embed is the scarce, earned peak", at most one hero per thought, never two co-visible, a warning under 0.6 s of air between hero windows.
- Subject matting with `u2net_human_seg.onnx` through the CLI's `remove-background` (CoreML on Mac, ~168 MB first download), so text can sit behind the head.
- `safe-zones.cjs` computes free regions per time window from the per-pixel alpha matte ("a bbox would wrongly claim" the pocket beside the head).
- Gates before and after render: `check-timing.cjs` (plan word times against transcript, `DRIFT_TOL = 0.08` s), `check-occlusion.cjs` (real Chromium DOM rects against matte alpha, per word), `check-overflow.cjs` (seeks the timeline and flags any text box leaving the canvas), `fit-fonts.cjs` (shrinks before render using per-family advance widths), `preview-frames.cjs` (composite previews at about 2 s per frame without a render).
- A decision gate that refuses clips with multiple speakers or hard cuts, burned-in captions (checked with a 1 fps contact sheet), near-silent audio where Whisper hallucinates ("Thank you."), or garbage transcripts.
- A luminance probe on the caption region: under 60 light text as is, 60 to 180 add a glyph scrim, above 180 opaque text plus scrim.
- 35 caption "identities" in `CATALOG.md` plus 17 `caption-*` registry blocks (`caption-pill-karaoke`, `caption-kinetic-slam`, `caption-emoji-pop`, `caption-camera-follow`, `caption-highlight`, ...).

**talking-head-recut skill.** Designed graphic cards (lower-thirds, callouts, quotes, side panels, PiP) authored as one HTML fragment per card from `transcript.json` word arrays, assembled and rendered; the clip plays untouched underneath.

**Weaknesses.** Release churn (v0.8.79 and v0.8.80 within a day; the skill text says "Standard mode retired 2026-06-12"). Several embedded-captions scripts need a built checkout (`HYPERFRAMES_ROOT` with `packages/cli/dist/cli.js`, falling back to `~/Downloads/hyperframes`), so the skill is not self-contained. Frame extraction of the whole source to images is disk-heavy for long footage. It does not select clips or reframe; "split multi-shot footage before applying it".

### 3. pycaps (+ tscaps, movielite)

**Model.** `Document -> Segment -> Line -> Word -> WordClip`. Each word has three visual states (`word-not-narrated-yet`, `word-being-narrated`, `word-already-narrated`), each a CSS class. Structure tags are automatic (`first-word-in-line`, `last-word-in-segment`, ...); semantic tags come from wordlists, regex or an LLM prompt ("words related to finance") and become CSS classes too.

**Rendering.** `CssSubtitleRenderer` opens a Playwright Chromium page, lays out the line, screenshots each word in each state with `page.screenshot(omit_background=True, animations="disabled", clip=...)`, caches the PNG by (word, CSS classes), then `movielite` (same author, "Alternative to MoviePy, powered by Numba") composites the PNG clips over the video with Python-side position/scale/opacity functions. A lighter `PictexSubtitleRenderer` skips the browser but supports a CSS subset and renders shadows differently.

**Template format** (`template/preset/hype/pycaps.template.json` + `styles.css`):

```json
"layout": {"max_width_ratio": 0.85, "max_number_of_lines": 2, "vertical_align": {"align": "bottom", "offset": -0.1}},
"splitters": [{"type": "split_into_sentences"}, {"type": "limit_by_chars", "min_chars": 10, "max_chars": 15}],
"effects": [{"type": "emoji_in_segment", "chance_to_apply": 0.85}, {"type": "animate_segment_emojis"}],
"animations": [
  {"type": "zoom_in_primitive", "when": "narration-starts", "what": "word", "duration": 0.12, "init_scale": 0.8,
   "overshoot": {"amount": 0.05, "peak_at": 0.7}},
  {"type": "fade_in", "when": "narration-starts", "what": "segment", "duration": 0.15}]
```

```css
.word { font-family: 'Komika Axis'; font-size: 24px; color: #DDDDDD; font-weight: 800;
  text-shadow: -2px -2px 0 #000, 2px -2px 0 #000, -2px 2px 0 #000, 2px 2px 0 #000, 3px 3px 5px rgba(0,0,0,0.5); }
.word-being-narrated { color: #FFFF00; }
.word-already-narrated { color: #FFFFFF; }
```

Animation vocabulary: `fade_in/out`, `zoom_in/out`, `pop_in/out`, `pop_in_bounce`, `slide_in/out`, plus primitives with `init_scale`, `overshoot`, `transformer` (`linear`, `ease_in`, `ease_out`, `inverse`), triggered on `narration-starts` or `narration-ends` for `word`, `line` or `segment`, filterable by `tag_condition`. Sound effects use the same trigger model (17 bundled SFX). Twelve built-in templates.

**Weaknesses.** CSS is only used for static appearance: CSS animations are disabled at screenshot time, so motion is limited to the Python primitives above. Alpha, not on PyPI, tested on Python 3.10 to 3.12 only, needs `playwright install chromium`, default transcription is `openai-whisper` on CPU. Captions only; no cards, logos or camera. The editor sibling `tscaps` (72 stars) is browser-native and AGPL for the app.

**Idea worth stealing.** The three-state word model with tags as CSS classes, and `narration-starts`/`narration-ends` as the only two animation triggers. It is a clean declarative vocabulary an agent can write without mistakes.

### 4. ASS/libass generators (whisper word timings to `.ass`, burned by ffmpeg)

**Capite / ai-video-captions** (`backend/subtitles.py`, pysubs2): one Dialogue event per spoken word, each carrying the whole line with only the current word styled, pinned with `\pos(x,y)` "to disable collision stacking", end time minus 10 ms "to prevent overlap at word boundaries". Per-style tags, verbatim:

```python
# box (active word inside a solid plate with a spring-like pop)
f"{{\\3a&H00&\\3c{box_color}\\1c{style_config.primary_color}"
f"\\t(0,40,\\fscx{pop_pct}\\fscy{pop_pct})"
f"\\t(40,90,\\fscx100\\fscy100)"
# karaoke (progressive fill)
f"{{\\kf{duration_cs}\\c{word_color}{active_weight_tag}}}{w_upper}{{\\r}}"
# bounce
f"{{\\t(0,50,\\fscx{bounce_pct}\\fscy{bounce_pct})"
f"\\t(50,100,\\fscx100\\fscy100)"
# glow
f"{{\\blur4{active_weight_tag}\\c{word_color}}}{w_upper}{{\\r}}"
```

RTL languages fall back from `\kf` to a colour change. Word spacing via `{\fscx N} {\fscx100}` around the space.

**nik-devs/ffmpeg-caption-burn-ass** (`ass_captions.py`): stdlib-only, `PlayResX/PlayResY` set to the 1080x1920 canvas, modes `karaoke-highlight` (3 to 5 words, active word `{\c}{\fscx110}`, described as "more reliable than `\k` karaoke timing"), `word-carousel` (`{\fscx80\fscy80\t(0,80,\fscx100\fscy100)}` pop), and `phrases` on a rounded plate measured with Pillow plus `fc-match`. Explicit `marginV` above the Reels UI.

**stable-ts** (`stable_whisper/text_output.py`): `result_to_ass(..., highlight_color='00ff00', karaoke=False)`; word-level tags `{\1c&H..&}` per word, or `\kf` progressive fill when `karaoke=True`. Its main value is timing: it stabilises Whisper word timestamps and can force-align a known script, which matters more for caption feel than the renderer does.

**Looks.** Good for the TikTok/Hormozi family: thick outline (`\bord`), shadow (`\shad`), blur glow (`\blur`), per-word colour, scale pops via `\t` with an optional acceleration exponent, karaoke fill. Limits: no springs (only `\t` curves), no colour emoji (libass renders grayscale glyphs only; libass issue #381 "support color emoji" is open), no soft drop shadows beyond `\blur`/`\be`, square `BorderStyle=3` boxes unless you draw `\p` vector shapes, and a scaled active word re-lays out the line so neighbours can shift during a pop. Cards, logos and charts are out of reach.

**Speed and fragility.** One ffmpeg pass, faster than real time with `h264_videotoolbox`, fully deterministic. The big Mac trap: Homebrew's default `ffmpeg` became a "lite" build without libass, freetype and harfbuzz (reported for 8.1.1 in VideoLingo issue #561, May 2026; the formula on 2026-09-27, ffmpeg 9.0.2, has no libass dependency while `ffmpeg-full` builds with `--enable-libass`), so `subtitles=`/`ass=`/`drawtext` vanish after a `brew upgrade`; `brew install ffmpeg-full` (keg-only) restores them. This machine currently has Homebrew ffmpeg 8.0_1 with `ass`, `subtitles` and `drawtext` present, so it works today and would break on upgrade. Fonts should be passed with `fontsdir=` to avoid fontconfig/CoreText surprises.

### 5. captacity (MoviePy)

`captacity/__init__.py` builds one `TextClip` per line per highlighted-word state, plus PIL-blurred shadow clips, all in a MoviePy `CompositeVideoClip`, written with `libx264`. Captions are vertically centred (`position` is a TODO). Word highlight is a colour change on the current word. Dependencies: `moviepy`, `pillow`, `openai` unpinned, but the code imports `moviepy.editor` and `TextClip`, which MoviePy 2.0 removed or changed ("the moviepy.editor namespace simply no longer exists"; `.set_` renamed to `.with_`). A fresh `pip install captacity` therefore fails without pinning `moviepy<2`, and MoviePy 1.x `TextClip` needs ImageMagick. Slow (Python per-frame compositing). Last push 2024-06. Useful only as a cautionary example.

### 6. short-video-maker (gyoridavid)

Kokoro TTS, whisper.cpp captions, Pexels b-roll, music, Remotion render, exposed as MCP and REST. Caption rendering (`src/components/videos/PortraitVideo.tsx`): pages of 20 characters, one line, `maxDistanceMs: 1000`, Barlow Condensed at `6em`, `WebkitTextStroke: "2px black"`, `textShadow: "0px 0px 10px black"`, active word gets a coloured rounded background. Faceless only; English only; last push 2025-06. Relevant only as proof that an MCP-driven Remotion pipeline works.

### 7. Revideo and Motion Canvas

**Revideo** (midrender/revideo, MIT, 4,066 stars): Motion Canvas fork with `renderVideo()` headless rendering through a browser, parallel workers, a React `<Player/>`, `<Video/>` and `<Audio/>` with frame-accurate sync. Scenes are generator functions (`yield* waitFor(0.5)`), which reads well for sequenced motion graphics but is awkward for hundreds of word-timed events. Smaller ecosystem than Remotion; no caption package. No GitHub release tags recently; last push 2026-07.

**Motion Canvas** (19,187 stars): editor-first, exports from its browser editor; last release v3.18.0-alpha.0 in February 2025. Not a fit for automated overlays on footage.

### 8. Reframing engines and camera smoothing

#### Google MediaPipe AutoFlip (the reference design)

Pipeline: shot boundaries, face/object/saliency signals fused into weighted focus regions, per-scene key-frame crop summaries, a per-scene camera motion decision, then a path solver. Code under `mediapipe/examples/desktop/autoflip/`.

**Per-scene camera decision** (`quality/scene_camera_motion_analyzer.cc`, options in `quality/cropping.proto`): steady if motion is small, sweep if detection keeps failing, otherwise track.

```cpp
// If scene motion is small, then look at a steady point in the scene.
if ((scene_summary->horizontal_motion_amount() <
         options_.motion_stabilization_threshold_percent() &&
     scene_summary->vertical_motion_amount() <
         options_.motion_stabilization_threshold_percent()) ||
    total_scene_frames_ == 1) {
  return DecideSteadyLookAtRegion(key_frame_crop_options, scene_summary,
                                  scene_camera_motion);
}
// Otherwise, tracks the focus regions.
scene_camera_motion->mutable_tracking_motion();
```

```proto
// If there is small motion within the scene keep the camera steady at the center.
optional float motion_stabilization_threshold_percent = 1 [default = .30];
// Snap to center if there is small motion and already focused closed to the center.
optional float snap_center_max_distance_percent = 2 [default = .08];
// If success rate in a scene is less than this, then use camera sweeping.
optional float minimum_success_rate_for_sweeping = 7 [default = 0.4];
```

In steady mode with required regions, the look-at point is the centre of the union of required focus regions and the crop grows to cover that union (`DecideSteadyLookAtRegion`).

**Offline path: robust polynomial fit** (`quality/polynomial_regression_path_solver.cc`): fits a quartic `out = a*t + b*t^2 + c*t^3 + d*t^4 + k` to focus-point centres over the scene with a Cauchy robust loss, then clamps so the window never leaves the frame.

```cpp
residual[0] = out_ - a[0] * in_ - b[0] * in_ * in_ -
              c[0] * in_ * in_ * in_ - d[0] * in_ * in_ * in_ * in_ - k[0];
...
problem->AddResidualBlock(cost_function, new CauchyLoss(0.5), a, b, c, d, k);
```

`prior_frame_buffer_size` (default 30) carries the previous chunk's points into the fit so forced flushes stay continuous.

**Online path: kinematic solver** (`quality/kinematic_path_solver.cc`, options in `kinematic_path_solver.proto`, used per axis for pan, tilt and zoom by `content_zooming_calculator`). A median filter over a time window, a dead band (`min_motion_to_reframe`, in degrees), a hysteresis window (`reframe_window`), a velocity estimate blended toward observations, and a velocity cap.

```cpp
int filtered_position = Median(raw_positions_at_time_);
...
// If the motion is smaller than the min_motion_to_reframe and camera is
// stationary, don't use the update.
if (IsMotionTooSmall(delta_degs) && !motion_state_) {
  delta_degs = 0;
  motion_state_ = false;
} else if (abs(delta_degs) < options_.reframe_window() && motion_state_) {
  delta_degs = 0;
  motion_state_ = false;
}
...
double observed_velocity = delta_degs / delta_t_sec;
double update_rate = std::min(mean_delta_t_ / options_.update_rate_seconds(),
                              options_.max_update_rate());
double updated_velocity = current_velocity_deg_per_s_ * (1 - update_rate) +
                          observed_velocity * update_rate;
current_velocity_deg_per_s_ = updated_velocity > 0
                                  ? fmin(updated_velocity, max_velocity)
                                  : fmax(updated_velocity, -max_velocity);
```

```proto
optional double update_rate_seconds = 5 [default = 0.20];
optional double max_update_rate = 6 [default = 0.8];
optional int64 filtering_time_window_us = 7 [default = 0];   // median filter history
optional float mean_period_update_rate = 8 [default = 0.25];
optional float max_velocity_scale = 11;  // max velocity grows with distance from target
optional float max_velocity_shift = 12;
```

`ContentZoomingCalculatorOptions` adds `scale_factor` (default 0.9: the subject fills 90 percent of the frame), `detection_shift_vertical` (shift the face box to leave headroom), `us_before_zoomout` (default 1 s before zooming out when the subject is lost), `max_zoom_value_deg` (default 35).

Status: the README of pyautoflip states AutoFlip "is no longer actively supported". Building it needs Bazel plus the MediaPipe C++ tree; nobody should do that on a Mac for a skill. The value is the design.

#### pyautoflip (`pyautoflip/cropping/camera_motion.py`)

Scene detection with PySceneDetect, key frames per scene, then one of three camera modes per scene. Talking-head detection by a crude proxy (70 percent of key windows centred), with a looser threshold for talking heads.

```python
motion_threshold_multiplier = 25 if is_talking_head else 15
if max_movement < self.motion_threshold * motion_threshold_multiplier:
    return CameraMotionMode.STATIONARY
elif consistent_direction and avg_movement < max_movement * 0.7:
    return CameraMotionMode.PANNING
else:
    return CameraMotionMode.TRACKING
```

STATIONARY averages key positions into one fixed window; PANNING is `np.linspace` from first to last key position; TRACKING linearly interpolates key positions and then smooths:

```python
sigma = self.smoothing_window / 6.0  # Heuristic for sigma value
smoothed_xs = gaussian_filter1d(xs, sigma=sigma)
smoothed_ys = gaussian_filter1d(ys, sigma=sigma)
```

Also worth stealing from `saliency_cropper.py`: false faces (posters, photos on the wall) filtered by `min_face_fraction = 0.03` of frame area; per-scene narrow (exact 9:16) or wide (`WIDE_CROP_FACTOR = 1.30`, blurred padding) crop when saliency is spread; split-screen when two faces cannot fit one crop:

```python
crop_w = int(frame_h * target_aspect[0] / target_aspect[1])
crop_w_norm = crop_w / frame_w
...
if right[0] - left[0] > crop_w_norm:
    return [left, right]
```

Weaknesses: heavy dependency set (torch, torchvision, insightface, mediapipe, onnxruntime, tensorboard, scikit-image, matplotlib); InsightFace model licensing is non-commercial for its pretrained weights; no active-speaker detection, so in a two-person shot it follows saliency rather than who is talking; smoothing is uniform Gaussian, so a fast subject gets a laggy window and a still one gets needless drift.

#### FrameShift (`frameshift/utils/crop.py`)

One stationary crop per scene: sample up to 150 frames, weighted centroid of detections where `effective_weight = weight * (1 + np.sqrt(area / max(1, frame_w * frame_h)) * 10)`, union of boxes for size, expand to the target ratio, clamp. The README is candid: "No tracking or panning inside a shot. A subject that walks across a long take can leave the frame." Output codec `mp4v`. Models verified by pinned SHA-256 before loading (a good practice for `.pt` pickles). The leftover `smooth_box` is a plain exponential moving average, `prev_box * (1 - factor) + curr_box * factor` with `factor = 0.2`.

#### What the smoothing survey implies

Every open-source reframer either holds one crop per shot (FrameShift, AutoFlip steady mode) or smooths a tracked path with a symmetric filter (pyautoflip Gaussian, FrameShift EMA). Only AutoFlip has the two properties a talking-head clip needs: a dead band so the frame does not breathe with every head nod (`min_motion_to_reframe`, `snap_center_max_distance_percent`), and bounded velocity so reframes look like an operator panning. For offline clip rendering the best composite is: decide per shot between steady and tracking with AutoFlip's 0.30 threshold; in steady shots, lock to the median face centre and snap to centre within 8 percent; in tracking shots, fit a robust (Cauchy or Huber) smooth curve or run a dead-band plus velocity-capped follower forward and backward; add headroom with a vertical detection shift. None of the reframing engines in this part uses active-speaker detection to choose between two faces; two apps in Part 2 do (TalkNet in clips-studio, audio-gated mouth motion in OpenShorts).

### 9. auto-editor (`src/analyze/audio.nim`, `src/lib/editutil.nim`, `src/conductor.nim`)

**Method.** Audio is split into chunks of one timebase unit (one video frame). Loudness per chunk is the max absolute sample, normalised to 0 to 1 (`toUnorm16(float32(maxAbs) / 32767.0)`, with NEON-vectorised paths on ARM). Default edit `audio:threshold=0.04,stream=all`; thresholds also accept dB (`audio:-19dB`). Other methods: `motion:threshold=0.02`, `blackdetect`, `subtitle`/`word`/`regex` (cut or keep by what was said, from an existing subtitle stream or its own transcription), combinable with `(or ...)`, `(and ...)`, `(not ...)`.

**Margin and smoothing** act on the boolean keep mask. Defaults: `--margin 0.2s` (can be asymmetric, `0.3s,1.5sec`), `--smooth 0.2s,0.1s` meaning `mincut` 0.2 s (silences shorter than this are kept) and `minclip` 0.1 s (sounds shorter than this are cut). Verbatim:

```nim
# Margin and smoothing act on the binary keep/cut boundary (active = any
# non-silent label). ...
mutMargin(active, startMargin, endMargin)
smoothing(active, mincut, minclip)
```

```nim
proc smoothing*(val: var seq[bool], mincut, minclip: int) =
  # A lone run shorter than both minclip and mincut flips forever (all-true
  # -> all-false -> all-true); checking two states back exits that 2-cycle.
  ...
      elif active:
        if j - startP < minclip:
          for i in startP ..< j:
            next[i] = false
```

**Beyond cutting.** Labels 0 to 255 with per-label actions (`-w:0 speed:8` to fast-forward silence with pitch preserved, `volume`, `zoom`, `deesser`, overlays via `add`), exports to Premiere, Resolve, Final Cut, Shotcut, Kdenlive. Transcription backends: whisper.cpp, NVIDIA Parakeet (`ggml-parakeet-tdt-0.6b-v3`, "Faster than Whisper at comparable English accuracy"), and Apple's on-device SpeechAnalyzer via the magic model name `apple` on macOS 26+ (`src/ae_speech.swift`). It ships four Claude skills (`skills/auto-editor*`), and `--preview` prints what would be cut without rendering.

**Weaknesses for our use.** Loudness is a proxy for speech: breaths and room noise pass, quiet trailing words get clipped unless the margin covers them. It cuts silence, not retakes or filler. Word-level cutting from a transcript (what the reference skill does) is strictly better for talking heads; auto-editor's margin and mincut/minclip semantics are the part to copy.

### 10. Rendering approach comparison for a macOS Apple Silicon skill

Criteria: how good captions and motion graphics can look, how much can break on the author's machine, speed.

| | Remotion | ffmpeg + libass (ASS) | pycaps | HyperFrames | MoviePy |
|---|---|---|---|---|---|
| Caption looks | Full CSS: springs, per-word transforms with correct reflow, colour emoji, gradients, blurred shadows, rounded plates | Strong for outline/karaoke/pop; no springs, no colour emoji, square boxes unless drawn, neighbours jitter on scale pops | Full CSS for static states; motion limited to fade/pop/zoom/slide primitives | Full CSS plus GSAP; matte-based text behind the speaker; 35 identities | PIL-quality text, few effects |
| Motion graphics (cards, logos, lists, charts, zooms) | Yes, React components | No | No | Yes, HTML/GSAP | Crude |
| Camera path (sub-pixel crop/zoom) | Trivial: per-frame `transform` from a JSON path | Only via per-segment crop or pre-rendered frames | No | Trivial: per-frame CSS | Per-frame numpy |
| Dependencies on Mac | Node, npm; bundles its own ffmpeg and downloads Chrome Headless Shell | Homebrew ffmpeg must include libass: default formula dropped it (use `ffmpeg-full`) | Python 3.10 to 3.12, Playwright Chromium, movielite/Numba, ffmpeg | Node 22+, system ffmpeg, Puppeteer chrome-headless-shell; some skills need a built repo checkout | Python, moviepy version pinning, ImageMagick for 1.x |
| Determinism | Frame-seeked, deterministic | Deterministic | Deterministic | Deterministic; BeginFrame only on Linux, screenshot mode on macOS | Deterministic |
| Speed (1080x1920) | Slow: about 4 fps with one video layer at concurrency 8 (measured by talking-head-reel); memory/swap sensitive | Fastest: a single pass, faster than real time with VideoToolbox (estimate) | Medium: browser only for unique word states, then Numba compositing | Slow, similar class to Remotion; frame extraction to disk | Slowest |
| Churn risk | Low (stable 4.x, daily patch releases, stable API) | Low (ASS spec frozen); packaging risk from Homebrew | Medium-high (alpha) | High (daily releases, retired modes) | Medium (v2 broke v1) |
| Licence | Free up to 3 employees, company licence above | LGPL/GPL ffmpeg, libass ISC | MIT | Apache-2.0 | MIT |

**Ranking for this skill.**

1. **Remotion** for the final render of anything with overlays, cards, logo chips, camera moves and premium captions. Reasons: best achievable look; bundled ffmpeg removes the Homebrew libass trap; stable API; the reference skill and the installed `remotion-best-practices` skill already encode working patterns; `@remotion/captions` and `@remotion/elevenlabs` plug straight into the ElevenLabs word timings this project already produces. Costs to manage: render time (render stills first, render detached, cap concurrency at 4 to 6 on a laptop, split long renders, check `df -h` and swap), and the licence line if the skill ever runs inside a company above three people.
2. **ffmpeg + libass** as the fast path: draft previews, caption-only clips, the 16:9 companion versions the existing `/clip` skill produces, and any batch where speed beats polish. Pin the binary (`brew install ffmpeg-full`, call `/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg`, or probe `ffmpeg -filters | grep subtitles` at startup and fail loudly). Keep emoji out of ASS captions.
3. **HyperFrames** when the Remotion licence matters or when "text behind the speaker" is wanted. Its QA gates (timing drift, occlusion, overflow, font fitting, contact-sheet decision gate) are worth porting regardless of which engine renders. Pin a version; do not track `main`.
4. **pycaps** only if a Python-only caption pass with CSS looks is required. Its template and tag model is the idea to take, not the runtime.
5. **MoviePy** never, for new work.

Hybrid that uses each where it is strongest: cut and reframe decisions as data (word-level cut list plus a per-frame camera path JSON computed in Python with AutoFlip-style steady/track logic), then one Remotion render that applies the crop as a transform on `OffthreadVideo`, draws captions and overlays, and mixes SFX; ffmpeg only for probing, audio loudness normalisation (`ebur128`, `alimiter`) and fast previews.

### 11. ft1148137/reframe-video-subject-skill (Codex skill, 4 stars, no licence, 2026-06)

- What: a single-skill reframer. `scripts/reframe_subject.py` (390 lines): ffprobe, sample frames at 2 fps, YOLO person detection per sample, pick the target by torso HSV colour ratio plus continuity plus a `--prefer left|right` hint, centre the crop on the bbox centre, smooth, render with one ffmpeg `crop` whose `x` is a time expression. Debug contact sheets with the chosen box drawn (`--debug-dir`). The SKILL.md makes the agent ASK which subject and which ratio before rendering, and says to prefer a fixed crop when the subject stays in a small region ("Fixed crop is simpler and avoids YOLO jumping between similar people").
- Smoothing worth stealing (sparse keyframes, median filter, cubic Hermite spline with clamped tangents, compiled into an ffmpeg expression so there is no per-frame Python loop and no re-encode through OpenCV):

```python
# ft1148137/reframe-video-subject-skill, reframe-video-subject/scripts/reframe_subject.py
def hermite_expr(xs, dt, max_velocity):
    velocities = []
    for i, x in enumerate(xs):
        if i == 0:
            v = (xs[1] - xs[0]) / dt if len(xs) > 1 else 0.0
        elif i == len(xs) - 1:
            v = (xs[-1] - xs[-2]) / dt
        else:
            v = (xs[i + 1] - xs[i - 1]) / (2 * dt)
        velocities.append(float(max(-max_velocity, min(max_velocity, v))))
    def segment(i):
        ...
        h00 = f"(2*{u3}-3*{u2}+1)"; h10 = f"({u3}-2*{u2}+{u})"
        h01 = f"(-2*{u3}+3*{u2})";  h11 = f"({u3}-{u2})"
        return f"({h00}*{x0:.2f}+{h10}*{dt*m0:.2f}+{h01}*{x1:.2f}+{h11}*{dt*m1:.2f})"
    expr = f"{xs[-1]:.2f}"
    for i in range(len(xs) - 2, -1, -1):
        expr = f"if(lt(t,{(i + 1) * dt:.3f}),{segment(i)},{expr})"
```
  rendered as `crop=w={crop_w}:h={height}:x='{expr}':y=0:exact=1,scale=1080:1920:flags=lanczos`.
- Weaknesses: horizontal pan only (y fixed at 0, no zoom); the nested `if()` expression grows linearly with duration (a 60 s clip at 2 fps is 120 nested ifs, evaluated per frame, fine for shorts, slow for long inputs); no shot-boundary handling (the spline will pan across a hard cut instead of jumping); the camera follows the subject continuously, so a speaker who sways produces a constantly drifting frame (no dead zone, no "hold still" state); YOLO person boxes rather than faces, so the crop centres the torso, not the eyes; person identity by shirt colour.

### 12. obi19999/smart-video-reframe (10 stars, "MIT"): do not use

- The README's "Download Now" and every link point to `src/utils/reframe-smart-video-1.7.zip` in the repo and tell the user to run a downloaded `.exe` or `.dmg`. Two zip archives sit in `src/utils/`. This is the common GitHub malware-lure pattern (a plausible Python skeleton plus a binary payload). Not opened, not evaluated further. Worth a line in any skill that tells an agent to "search GitHub for a reframer": never download release zips or binaries from low-star repos.
