# 01. Long-to-short clipping apps and professional short-form editing craft (state of the art, September 2026)

Purpose: inform a Claude Code skill that turns long recordings (lectures, talks, podcasts, interviews) into short clips and must beat Opus Clip out of the box.

Reading guide. Every claim carries an inline URL. Source quality varies a lot in this space, so each source is graded where it matters:

- **A**: first-party docs, help centers, API references, official platform help pages, peer-reviewed or arXiv papers.
- **B**: independent hands-on tests with stated methodology (ScaleReach, HeyGen's 42-minute test, BIGVU, The Podcast Host, Newsshooter).
- **C**: vendor marketing, SEO blogs, "2026 guide" listicles. Many of these are written by competitors or by AI. Their numbers are often unsourced. They are used only for direction and are flagged.

A vendor-authored benchmark (Reap) and vendor-authored "data studies" (OpusClip research hub) are useful but biased toward the author.

---

## Contents

1. Opus Clip in depth
2. The rest of the field (Submagic, Captions/Mirage, Vizard, Klap, Munch, Descript, Riverside, CapCut, VEED, quso, Choppity, Spikes, 2short, Reap, Eklipse, Clipchamp, YouTube Studio, 2026 newcomers, open source)
3. What professional short-form editors do that the tools do not
4. Platform specifics in 2026
5. What research and credible creator data say about retention and clip completeness
6. Design implications for a tool that beats Opus Clip
7. Appendix A: every named caption preset found
8. Appendix B: source index

---

## 1. Opus Clip in depth

### 1.1 Product surface as of September 2026

| Surface | What it is | Source |
|---|---|---|
| ClipBasic | Keyword-driven curation model for talking-head content. Keywords filter to moments where the words are spoken. | https://help.opus.pro/docs/article/select-keywords (A) |
| ClipAnything | Multimodal curation that reads "visual, audio and sentiment cues, objects, scenes, actions, sounds, emotions and on-screen text" per frame. Accepts natural-language prompts. Hands-Free mode auto-detects genre and applies default prompts. | https://www.opus.pro/clipanything (A), https://clipme.com/blog/how-opusclip-works (C) |
| ReframeAnything / AI Reframe | Tracks moving speakers and objects, outputs 9:16, 1:1, 16:9. Automated, prompt-based ("track the ball") or manual. | https://www.opus.pro/ai-reframe (A) |
| Agent Opus | Prompt/script/URL/audio to finished video with sub-agents for research, script, storyboard, motion graphics, voiceover, avatars. | https://mer.vin/2026/07/agent-opus-explained-opusclip-end-to-end-ai-video-agent/ (C) |
| AI Producer | Chat-driven editor: "captions, b-roll, charts, motion design, music, and SFX" in one pass. | https://producer.opus.pro/ (A), https://www.opus.pro/ai-video-editor (A) |
| Motion Studio (Sept 18, 2026) | Generates custom animations and brand assets from up to 30 images, 10 videos, 10 audio references. | https://opusclip.canny.io/changelog (A) |
| Claude connector (Sept 11, 2026) | Official Claude connector, no API key setup. | https://opusclip.canny.io/changelog (A) |
| MCP server | 27 tools prefixed `opusclip_`: submit_project, list_clips (with virality scores), get_transcript (per-word timing), get/apply_editing_script, censor, export (HD/4K/Adobe XML), social copy, schedule_publish. Claims ~90 s to generate 10 clips. | https://www.opus.pro/mcp (A) |
| opus-skills (Claude Code plugin, v3.6.0) | Bash CLI over the REST API with named edit ops. Requires Pro/Max/Enterprise API key. | https://github.com/opus-pro/opus-skills (A) |
| Mobile apps | iOS/Android, 8 UI languages (Aug 21, 2026). | https://opusclip.canny.io/changelog (A) |

Implication: Opus is already agent-accessible from Claude, so a Claude skill wins only through better clip choice, better craft and better control.

### 1.2 Internal model of a clip (from the public API and editing-script docs)

The opus-skills repo documents the `EditingScript`, which reveals how Opus represents an edit (https://github.com/opus-pro/opus-skills, `references/editing-script.md`, A):

- A tree of tracks, then sections, then segments, then elements. Time is in milliseconds.
- Two coordinate systems: `duration.{sO,eO}` are source-media offsets; `timeline.{in,out}` are clip-output offsets. Optional `sOAdj/eOAdj` override values after edits.
- Typical tracks: `KeyFrameTrack` (video frames plus crop/layout keyframes), `CaptionTrack` (one `TextElement` per spoken word with its own timing, which drives the karaoke highlight), `EmojiTrack`. Curated projects may add `BRoll`, `ScreenOverlay`, `TextOverlay`/`TextOverlayTrack`.
- Caption colour is not in the script. It lives in style settings: `captionColor`, `highlightColor` (default bright green `#04f827`), `captionPosition` (`top` | `middle` | `bottom`), `uppercase`.
- Named edit ops (v3.6.0): `trim_section`, `split_section`, `drop_section`, `reorder_sections`, `delete_phrase` (cuts the phrase from video and captions), `replace_phrase` (same word count only, timing preserved), `set_style`, `add_text_overlay` / `set_text_overlay` / `remove_text_overlay`, `remove_emoji`, `move_emoji`. Keyword-highlight toggle, `set_captions`, `set_emoji`, `remove_filler_words`, `remove_pauses` are MCP-only for now.
- `add_text_overlay` "renders as the same card the auto-hook uses: bold black text on a white rounded box", default 5 s, position `top` (default), `middle`, `bottom`.
- Clip preview page sorts by score and shows "detailed AI scores (hook, coherence, connection, trend)".
- Re-render of a 30 s clip takes ~30-45 s and is charged.

API create-project parameters (`references/api-reference.md`, A): `curationPref.model` (`ClipBasic` | `ClipAnything`), `clipDurations` as `[[min,max],...]` seconds (required in practice), `genre`, `topicKeywords` (ClipBasic), `customPrompt` (ClipAnything), `range {startSec,endSec}`, `skipCurate`; `renderPref.layoutAspectRatio` (`portrait` | `landscape` | `square`), `enableRemoveFillerWords`; `brandTemplateId`; CLI flags `--enable-auto-hook`, `--enable-caption`, `--target-lang` (translated captions), `--dubbing-language`, `--skip-slicing`, `--remove-filler`. Limits: 30 req/min, 10 h or 30 GB per video, 50 concurrent projects. Thumbnail generation endpoint is experimental (7 credits per call).

### 1.3 Clip selection, prompts and lengths

- Length options in the UI: **Auto (0m-3m)** default, **<30s**, **30s-60s**, **60s-90s** (help center and tutorials: https://help.opus.pro/docs/article/select-clip-length A; https://www.opus.pro/blog/how-to-edit-podcast-shorts-like-a-pro-using-opus-clip-pc-mac A). OpusClip 3.0 added mid-form **3-5 min, 5-10 min, 10-15 min** clips (no AI B-roll beyond 3 min at launch) (https://www.opus.pro/blog/opusclip-clip-different A).
- Genre-specific curation (Q&A, vlogs, listicles, webinars and others) since 3.0 (same source).
- ClipAnything prompt manual (https://help.opus.pro/docs/article/clip-anything-prompt-manual, A): prompt types are Moments/Scenes, Action, Emotion, Characters, plus compilations ("Compile all Man City's scoring"). Examples: "Find the moments most likely to go viral on social media", "Clip my exciting reactions to tasting shawarma". Prompts must not try to edit ("Remove the flickering"), control length or add effects. English prompts only. Reprompting on the results page is unlimited.
- Credits are charged per source minute, not per output clip (https://clipme.com/blog/how-opusclip-works C; https://www.scalereach.ai/blog/opus-clip-review B).

### 1.4 Virality score

- Help center definition (https://help.opus.pro/docs/article/virality-score, A): 0-99 scale on four dimensions. **Hook**: "whether the opening effectively captures attention and connects to the video's core subject". **Flow**: "logical progression of content and quality of the conclusion". **Value**: useful, emotionally resonant or personally meaningful. **Trend**: alignment with current social trends. Paid plans only.
- OpusClip 3.0 blog names the dimensions Hook, Flow, **Engagement**, Trend (https://www.opus.pro/blog/opusclip-clip-different A). The API preview labels them hook, **coherence**, **connection**, trend (opus-skills SKILL.md, A). The naming has drifted; the underlying idea is a rubric score from an LLM judge.
- Reliability, independent test (https://www.scalereach.ai/blog/opus-clip-review, B, 30 clips tracked 14 days): clips scoring 80+ averaged 2.3x the views of sub-50 clips, **but the best-performing clip scored 64 and the worst-performing clip scored 87**. Reviewers converge on "sorting heuristic, not a predictor" (https://www.nemovideo.com/blog/opus-clip-review-2026 C; https://www.eesel.ai/blog/opusclip-reviews C).

### 1.5 Reframing, active speaker detection and layouts

Layouts (https://help.opus.pro/docs/article/layout-and-reframing, A):

| Layout | Behaviour |
|---|---|
| Fill | Crops to the speaker and fills 9:16. |
| Fit | Crops the original to **4:3** and adds opaque padding top and bottom to fit 9:16. |
| Split | Stacks two speakers top/bottom, both talking and reacting. Only works when both appear together in the original frame. |
| Three / Four | Three or four speakers for panels. Same same-frame requirement. |
| Screenshare | Screen content in the upper half, speaker in the lower half. Falls back when no screenshare is detected. |
| Gameplay | 30% facecam on top, 70% gameplay below. |

- Layout can change per timeline segment ("Layout" dropdown on canvas). Manual Reframe window via crop icon (https://help.opus.pro/docs/article/how-to-manually-reframe-content A).
- Subject tracking (https://help.opus.pro/docs/article/subject-tracking.md, A): Automatic mode uses "voice and motion cues" to find the active speaker. Manual mode tracks any clicked subject (products, animals, hands) and can switch subjects per scene.
- B-roll layouts added: **Picture-in-Picture** (speaker in a small window, B-roll behind) and **Split** (B-roll and speaker stacked, swappable, not for 16:9) (https://opusclip.canny.io/changelog/new-b-roll-layouts-picture-in-picture-and-split A).
- Measured quality: 4 of 76 clips (5%) needed manual crop fixes on talking heads (https://www.scalereach.ai/blog/opus-clip-review B). On multi-speaker content, "occasionally cuts heads off during quick switches" (https://www.nemovideo.com/blog/opus-clip-review-2026 C). Split requires speakers to share a frame, so separately recorded remote guests (Riverside, Zoom gallery) are handled poorly (https://whipscribe.com/tools/clipping C).

### 1.6 Captions, emoji, keyword highlighting

- Named caption templates confirmed across sources: **Karaoke, Gameplay, Beasty, Deep Diver, Youshaei, Pod P, Mozi, Popline, Think Media, Simple, Glitch Infinite, Seamless Bounce, Baby Earthquake, Blur Switch** (https://clip.opus.pro/captions A; https://videomaker.me/blog-design-options-for-your-short-form-videos-opus-clip-tutorial-52532 C; https://www.tipard.com/video/opus-video-editing.html C). Opus markets them as inspired by Ali Abdaal, MrBeast, Think Media and Jon Youshaei (https://clip.opus.pro/captions). Visual descriptions are in Appendix A.
- Customization (https://help.opus.pro/docs/article/change-captions.md, https://help.opus.pro/docs/article/captions-and-emojis, A): font, size, colour, stroke, shadow, case, drag position anywhere, one-line or three-line layouts, custom fonts and logo in brand templates (Pro). No bulk caption editing across clips.
- AI Keyword Highlighter and AI Emoji are toggles in the "AI Enhance" panel. Emoji are added per word and editable (https://help.opus.pro/docs/article/ai-emojis-keywords.md A). Default highlight colour `#04f827` (opus-skills, A). Speaker colour coding is available (https://www.nemovideo.com/blog/opus-clip-review-2026 C).
- Brand Vocabulary (Sept 7, 2026): persistent custom dictionary for names and jargon (https://opusclip.canny.io/changelog A).
- Caption accuracy measured by ScaleReach (B): ~95% clean solo studio audio, ~92% light noise, ~90% two-person clean (wrong speaker attribution), ~88% overlap or non-American accents (proper nouns).
- Opus's own guidance on preset families (https://www.opus.pro/blog/best-caption-presets-styles-boost-retention, C): Bold Statement (Montserrat Bold/Bebas Neue/Impact, 60-80 pt, upper or centre third, minimal animation), Dynamic Word-by-Word (white to yellow or brand accent, word highlights 50-100 ms before it is spoken), Minimal Clean (Helvetica Neue/Lato 40-50 pt, subtle shadow or background blur), Emoji-Enhanced (max one emoji per caption line), Branded Custom. Its percentage claims (23-40% watch time etc.) are unsourced.

### 1.7 Auto Hook, titles and social copy

- **Auto Hook**: "short text overlay automatically added to the first 5 seconds" of the **top 10 clips**, "smart placement: never covers faces or captions", on by default (https://opusclip.canny.io/changelog/meet-auto-hook-your-clips-now-grab-attention-from-the-first-second A). Rendered as bold black text on a white rounded box (opus-skills, A). A feature request to move a hook *sentence* to the start exists (https://opusclip.canny.io/feature-requests/p/including-hooks-at-beginning-of-video A). The editor lets a user "add a new hook sentence, or any part from your original video" at the start manually (https://www.opus.pro/ai-video-editor A).
- Social copy generator: titles in styles interesting, catchy, serious, question; descriptions; hashtags (https://www.opus.pro/blog/opusclip-clip-different A). "YouTube full video link" checkbox inserts a link to the long video in Shorts captions (Sept 4, 2026, changelog A).

### 1.8 B-roll

- Sources: AI-generated images, stock video from Pexels (Storyblocks and Getty planned), AI video B-roll "powered by Agent Opus", text-to-video "lab" B-roll with styles (photorealistic, pop art) (https://help.opus.pro/docs/article/ai-broll.md A; https://www.opus.pro/blog/opusclip-clip-different A).
- Placement: sidebar toggle, or select transcript sentences and "Add". Not settable globally in brand templates. Daily caps: Pro 50 AI-image clips, unlimited stock.
- Measured quality: 11 of 30 clips received B-roll, **4 of those 11 were contextually wrong** ("coffee cup for equipment discussion") (https://www.scalereach.ai/blog/opus-clip-review B). Reports of static images inserted where video was expected (https://www.eesel.ai/blog/opusclip-reviews C).
- Opus's own dataset: B-roll appears in only **6.0% of 13.5M exported clips** (Jan-Mar 2026); transitions 2.4%; text overlays 4.5%; outros 4.6%; intros 1.0%; "visual hooks" 0.04% (https://www.opus.pro/research/broll-visual-effects-short-form, vendor data). Users mostly switch B-roll off.

### 1.9 Transitions, zooms, cleanup, audio

- Transitions (https://help.opus.pro/docs/article/add-transition-effects.md, A): six types, **cross fade, cross zoom, zoom in, zoom out, fade in, fade out**. "Auto Transitions" detects jump cuts and applies the selected transition.
- Auto zoom: Opus says it "analyzes your speech patterns and automatically adds zooms at moments of emphasis" (https://www.opus.pro/blog/best-auto-zoom-in-tools, C). No published scale values.
- Speech Cleanup (https://help.opus.pro/docs/article/speech-cleanup.md, A): fillers ("um", "uh", "you know", stutter repeats) selectable by type; pause removal with a **default 0.5 s** threshold slider; "Bad takes" detection (retakes, restarts, self-corrections, repetitions). Nothing is deleted without approval. Claims >90% filler detection.
- Speech Enhancement upgrade (Sept 10, 2026) with noise-reduction and voice sliders. Audio fade in/out up to 5 s for music and SFX, saveable in brand templates (Sept 2, 2026) (changelog A).
- Profanity censor jobs with optional beep (API, A).

### 1.10 Brand templates, export, scheduling

- Brand templates: up to five custom presets with naming conventions, default layouts, logos, caption styles, colour themes; one can be the default (https://www.futurepedia.io/courses/opus-clip-ai/lessons/preset-templates C).
- Export: MP4 HD/4K; **XML for Premiere Pro and DaVinci Resolve** on Pro. The XML folder contains the XML, an SRT, original video segments and tutorials, with **30 s added before and after each clip** as handles. Captions come as SRT only, so styling is lost; no reframe keyframes or B-roll are documented in the XML (https://www.opus.pro/export-to-xml A; https://help.opus.pro/docs/article/import-to-davinci-resolve A).
- Free tier: watermark, exports expire in ~3 days. Resolution for free is reported as both 480p (https://www.tipard.com/video/opus-video-editing.html C) and 1080p (https://www.opus.pro/tools/opusclip-captions A); treat as plan-dependent.
- Scheduler: YouTube, TikTok, Instagram, Facebook, LinkedIn, X. In a 30-day test TikTok auth dropped twice and one TikTok post was silently never published (https://www.scalereach.ai/blog/opus-clip-review B). Reap's benchmark puts Opus Pro at ~15 TikTok posts/day and 6 connected accounts (https://reap.video/reports/state-of-top-ai-video-clipping-tools-2026, vendor).
- Speed: ~25 min time-to-first-clip on a 90-min podcast in Reap's April 2026 benchmark (vendor); 24 clips from a 59-min episode in 8 min in The Podcast Host's test (https://www.thepodcasthost.com/recording-skills/can-opusclip-make-your-podcast-go-viral/ B). Opus claims +300% speed for one-hour videos in 3.0.
- Pricing (2026): Starter ~$15/mo, Pro ~$29/mo; credits roll 60 days (https://www.scalereach.ai/blog/opus-clip-review B).

### 1.11 What Opus Clip gets wrong (evidence table)

| Failure mode | Evidence | Source |
|---|---|---|
| Cuts mid-sentence or mid-thought, strips the sentence that gives context | 10 of 76 clips (13%) unusable: "cut mid-sentence, missed punchline, or topic the AI misread"; 25% more needed light editing | https://www.scalereach.ai/blog/opus-clip-review (B) |
| Low keep rate | "roughly 40% of generated clips end up in the trash" over 50+ clips | https://bigvu.tv/blog/opus-clip-tested-2026-where-ai-wins-40-percent-discard/ (B) |
| Low keep rate on a podcast | 14 clips in 9 min, only 3 publish-ready on a 42-min episode | https://www.heygen.com/blog/opus-pro-alternatives (B, competitor-authored) |
| Multi-speaker keep rate collapses | ~70% usable on solo speaker, "about 4 out of 10" on multi-speaker | https://www.nemovideo.com/blog/opus-clip-review-2026 (C) |
| Misses jokes, sarcasm, comedic timing; cuts before the punchline | Reddit quote: "you didn't use the good parts" | https://www.eesel.ai/blog/opusclip-reviews (C) |
| Picks off-topic tangents because they score as "hooky" | Flagged a throwaway joke about Taylor Swift's hair in an episode on podcast automation; read "abducted by aliens" as human trafficking | https://www.thepodcasthost.com/recording-skills/can-opusclip-make-your-podcast-go-viral/ (B) |
| Filler removal leaves "audible edits" around each um/uh | Same test | same (B) |
| Caption errors on names, homophones, brand words | "knight" for "night"; misspelled URL and "Resillence"; fixes cost credits | Podcast Host (B); https://www.trustpilot.com/review/opus.pro (C) |
| Caption drift | "Caption alignment drift during processing" | BIGVU (B) |
| Wrong face during crosstalk; heads cut on quick switches | multiple tests | nemovideo (C); heygen (B) |
| B-roll irrelevant or static | 4 of 11 wrong | ScaleReach (B); eesel (C) |
| Virality score weakly predictive | top clip 64, worst 87 | ScaleReach (B) |
| Captions stack on top of burned-in source subtitles | clutter | eesel (C) |
| Thin editor (no multitrack, no fine audio, no music in some tiers) | "cannot do multi-track editing or fine-tune audio" | ScaleReach (B); nemovideo (C) |
| Scheduler failures, auth drops, billing/cancellation friction | 22% one-star in a 302-review Trustpilot sample | ScaleReach (B) |

The common thread: effects are fine. **Editorial judgement about what the clip is, where it starts and where it ends** is where users lose time.

---

## 2. The rest of the field

### 2.1 Summary table

| Tool | Distinctive features and effects | Main weaknesses | Sources |
|---|---|---|---|
| **Submagic** | Caption-first. 42 named templates via API (default "Sara"); theme categories All, Premium, New, Speakers, Emoji, Trend, Custom. Magic Zooms (6 styles incl. "zoom fast", "crash zoom out", "smooth zoom in"), Magic B-rolls (6 transition styles), transitions ship with a bundled SFX, SFX library (whooshes, dings, impacts), AI Hook Title (themes, size, Y position, duration), emoji per scene, keyword highlight, stroke S/M/L, safe-zone overlay filter, clean audio, eye contact, silence and bad-take trim, colour adjust, music library, 1080p/2K/4K at 30/60 fps, subtitle export. Magic Clips (long to short) is a $19/mo add-on, 10 long videos/mo. API and MCP bundles. | Weak long-form moment detection (needs pre-trimmed input per Choppity); Magic Clips is an upsell; translation generic; no true multi-speaker split; bright highlight colours hurt legibility (user comment on "Tracy"). | https://docs.submagic.co/api-reference/templates (A); https://care.submagic.co/en/article/what-are-themes-and-themes-categories-1pv8wvz/ (A); https://www.submagic.co/features/auto-zooms (A); https://www.submagic.co/features/transition-editor (A); https://care.submagic.co/en/article/how-to-use-submagic-v2-step-by-step-guide-pafx7o/ (A); https://care.submagic.co/en/article/how-to-add-hook-titles-to-your-videos-using-ai-on-submagic-11kzi3m/ (A); https://thebusinessdive.com/submagic-review (B); https://www.submagic.co/features/magic-clips (A); https://capzai.com/en/blog/submagic-review-2026 (C) |
| **Captions app (company renamed Mirage, Sept 2025)** | AI Edit: cuts silences and fillers, adds B-roll, zooms, music, SFX, captions in a named style (20+ styles, e.g. Prism Pro, Stack, Bloom, Chalk). AI Edit V3 (Jan 2026) "sharper cuts and better pacing"; horizontal AI Edit (Dec 2025); Long-to-Short flow; **Clips Chat** (Aug 2026) to ask for different clips conversationally. Caption engine: 30+ presets, active-word colour/background, **AI Emphasis** (underline, emphasize, supersized), negative (inverted) captions, caption background stroke, randomized rotation, auto movement/scale, AI emoji (placement model retrained Feb 2026). Eye contact, denoise per shot, AI twin, dubbing, "Looks" colour presets. | Mobile-first creator tool; clip selection from long video is newer and less proven; heavy "AI look" styles. | https://captions.ai/help/whats-new (A); https://captions.ai/features/edit-with-ai (A); https://captions.ai/help/docs/captions/styles (A); https://en.wikipedia.org/wiki/Captions_(app) (A) |
| **Vizard** | Up to 40 clips per source with virality score; captions with auto-emoji and auto-bolded keywords; active-speaker centering; auto B-roll; transcript editing; scheduler; API from Creator tier; ~10 min TTFC on 90 min. | Speaker tracking "wobbled on crosstalk sections, cropping wrong face twice"; single-speaker bias; limited style depth; no prompt-driven selection (per one review). | https://vizard.ai/tools/clip-maker (A); https://www.heygen.com/blog/opus-pro-alternatives (B); https://creatify.ai/review/vizard-ai (C); https://whipscribe.com/tools/clipping (C) |
| **Klap** | Detects talk-show, interview, panel formats; "AI Reframe 2" layouts (split screen, screencasts, gaming); facial recognition to place "responsive subtitles"; 52 caption languages, 29 dubbing; word-level highlighted captions "we would ship untouched"; ~$0.03 per source minute; API. | Reframe "struggles on group shots and camera movement"; keeps screenshots centred, obscuring subjects; caption edits do not resync; single source only. | https://klap.app/ (A); https://www.heygen.com/blog/opus-pro-alternatives (B); https://www.aitoolssme.com/blogs/i-tested-klap-for-creating-shorts (C) |
| **Munch** | Trend-scored moment selection (trend matching on Elite), keyword/SEO analytics, multilingual captions, auto-crop, social copy; 2026 "Munch Studio" relaunch adds planner, posters, carousels. | Highest entry price ($49/mo annual); limited editing; ranked last of 9 in Reap's benchmark. | https://kompozy.io/reviews/munch (C); https://sendshort.ai/guides/munch-review/ (C); Reap benchmark (vendor) |
| **Descript** | Underlord agentic co-editor; "Create clips" from transcript keywords and emotional peaks; delete text to delete video (fixes mid-thought cuts at the source); layouts (Bold, Editorial, Simple, Vintage families); Studio Sound; Eye Contact; automatic multicam; filler removal; best English transcription (~98%) in Reap test. | Underlord "often applies generic captions in the center of the screen"; not one-click; dual metering (media minutes plus AI credits). | https://www.descript.com/clips (A); https://www.descript.com/blog/article/descript-season-6-meet-underlord (A); https://chasejarvis.com/blog/descript-underlord-ai/ (C); https://www.heygen.com/blog/opus-pro-alternatives (B) |
| **Riverside Magic Clips** | Signals: keyword relevance, sentiment, speaker energy; 30-90 s clips, ~2 per 5 min; clips from local uncompressed 4K recordings; focus-speaker and keyword controls; Co-Creator chat editing (Sept 2025). | Static block subtitles (no word-level karaoke); "starts too early, ends too late, misses the peak"; no silence removal (8-12 s silences kept); wrong speaker on three-person panels; only works on Riverside recordings. | https://riverside.com/magic-clips (A); https://support.riverside.com/hc/en-us/articles/12124048765981-AI-Magic-Clips (A); https://blitzcutai.com/blog/riverside-magic-clips-review-2026 (C); https://www.heygen.com/blog/opus-pro-alternatives (B) |
| **CapCut** | AI long-to-short (up to 3 h / 10 GB), highlight detection, subject-tracking reframe, auto captions in many languages, huge trend-tuned template and caption-style library, beat-sync zooms, AutoCut, free tier. | No virality score; generative features on separate credits; features differ across web, desktop, mobile; manual effort; CapCut's own page tells users to "review each generated clip to make sure it contains enough context to stand on its own". | https://www.capcut.com/tools/long-video-to-shorts (A); https://www.heygen.com/blog/opus-pro-alternatives (B); https://magichour.ai/blog/best-ai-captioning-tools-2026 (C) |
| **VEED** | "Clips" with goal presets (e.g. viral highlight, insight teaser), max-length setting, portrait or landscape, optional prompt, preset subtitle styles; Magic Cut removes fillers and dead air (8 min to <6 min in ~30 s); 125+ subtitle languages, 97% line match. | "Clip selection accuracy trails Vizard, Klap, and Opus"; clips feature is one-time on free, no YouTube import for clips; credit burn. | https://support.veed.io/en/articles/11652474-how-to-use-our-clips-feature (A); https://www.heygen.com/blog/opus-pro-alternatives (B) |
| **quso.ai (formerly vidyo.ai, rebranded late 2024)** | Intelliclips (moment finding), CutMagic (scene detection plus face/speaker tracking), virality score out of 100, word-level captions in 50+ languages with highlighted keywords, auto-emoji, **progress bar**, brand kit, scheduler, filler removal. | Undifferentiated; review coverage mostly promotional. | https://quso.ai/features (A); https://creatify.ai/review/vidyo-ai (C) |
| **Choppity** | Custom AI selection criteria; transcript-native editor; "magic reframe" with Follow tracking boxes; stacked split-screen for two speakers; word-level karaoke captions; profanity censor; scheduler, analytics, "Ideas Board"; creator-style recreation pages. | Free tier preview-only; self-published rankings. | https://www.choppity.com/features/ (A); https://www.choppity.com/blog/best-opus-clip-alternatives/ (C, self-ranking) |
| **Spikes Studio** | Model trained on broadcast and gaming footage; auto crop and zoom, auto transitions, B-roll photos/text, music and SFX library, AI titles and hashtags, emoji suggestions, live-stream "Clip Better". | Weak on podcasts and interviews; $32.99 first paid tier. | https://www.spikes.studio/ (A); https://www.nemovideo.com/alternative/spikes-studio (C) |
| **2short.ai** | YouTube-link-first; "center stage facial tracking" that "held host centered through full batch"; one-click animated subtitles (20+ languages); brand presets; all features from $9.90/mo. | "Two clips captured setup without payoff"; basic editor. | https://2short.ai/ (A); https://www.heygen.com/blog/opus-pro-alternatives (B) |
| **Reap** | Fastest TTFC in its own benchmark (4-5 min on 90 min); 100 transcription languages, **Romanized-script captions** (Hinglish, Arabizi, Romanized Urdu/Bengali, Taglish), 80+ dubbing languages, 50+ caption styles; multi-segment clips from non-contiguous source sections; audiogram waveform overlays; native MCP server (10 tools), public CLI, API from $9.99. Internal claim: ~1 in 5 generated clips reaches performance thresholds. | Vendor ran the benchmark; limited independent review. | https://reap.video/reports/state-of-top-ai-video-clipping-tools-2026 (vendor); https://reap.video/mcp (A) |
| **Eklipse** | Gaming: reads kills, clutches, wins from on-screen game UI; voice command "clip it"; TikTok templates with facecam tracking; memes; July 2026 engine also scores Just Chatting, IRL, podcast moments. | Gaming-centric. | https://eklipse.gg/features/ (A); https://blog.eklipse.gg/tools/ai-clip-maker-gaming.html (A) |
| **Clipchamp** | Auto compose (slideshow from assets), free autocaptions, short-form templates, Copilot script suggestions. | No real long-to-short moment detection. | https://clipchamp.com/en/blog/ai-video-editor-auto-compose-clipchamp/ (A); https://support.microsoft.com/en-us/clipchamp/how-to-use-autocaptions-in-clipchamp (A) |
| **YouTube Studio (native)** | Create Shorts or clips from own long videos with **AI-suggested segments and an AI outline** (10 countries, 7 languages); captions from the transcript (colour, font, style, position); horizontal sources become a **blurred crop**; the source video is auto-attached as the Short's related video; YouTube states reuse is not penalized. "Edit with AI" for Shorts (Nov 2025). | Only for the channel's own videos; basic styling. | https://support.google.com/youtube/answer/15824265 (A) |
| **Kapwing** | Smart Cut removes dead air before clipping (removed 4 min); AI Clip Maker; collaborative editor; integrated generative video models. | Credits freeze features mid-project. | https://www.heygen.com/blog/opus-pro-alternatives (B) |
| **HeyGen** | Positioned as an alternative that generates a short from a prompt instead of clipping. | Different job (synthetic video). | https://www.heygen.com/blog/opus-pro-alternatives (B, self-authored) |

### 2.2 Reap's April 2026 benchmark (vendor-run, useful for numbers)

Nine tools, same six-video corpus (90-min bilingual podcast, 45-min webinar, 30-min interview, 12-min talking head, 45-min gaming stream, 5-min sports reel), paid plans, same 200 Mbps line (https://reap.video/reports/state-of-top-ai-video-clipping-tools-2026):

| Tool | TTFC on 90-min podcast | Language coverage (transcription / translation / dubbing) | Agent access |
|---|---|---|---|
| Reap | 4-5 min | 100 / 100+ / 80 + Romanized | REST from $9.99, MCP, CLI |
| Vizard | ~10 min | ~25 / ~35 / undocumented | API on higher tiers |
| Submagic | 8-12 min | 48-50 / 100+ / 100+ | API on higher tiers |
| OpusClip | ~25 min | 22-25 / 1 / 0 (the opus-skills CLI now exposes `--target-lang` and `--dubbing-language`, so this is dated) | Business-only API in the report; MCP and Claude connector since |
| Descript | ~20 min | ~98% English accuracy (category-leading) | none observed |

Ranking by the author: Reap, OpusClip, Vizard, Submagic, Klap, Descript, VEED, CapCut, Munch. Its predictions for 2027: agent-first access (API/MCP) as table stakes, throughput as the pricing axis.

### 2.3 2026 newcomers and adjacent tools

| Tool | What is new | Source |
|---|---|---|
| **shortshort** (reviewed Sept 21, 2026) | Clips "stand on their own and end where a sentence ends", taken from the word-level transcript; face tracking with **"one zoom level per shot"** and **emphasis pushes bounded between x1.0 and x1.6**; **"slides, screens, and wide shots are detected and kept whole rather than cropped"**; output only 1080x1920 at 30 fps; no dubbing, posting or B-roll; €12-79/mo per source hour. | https://www.newsshooter.com/2026/09/21/shortshort-takes-one-long-uploaded-video-creates-vertical-916-cutdowns-with-word-by-word-captions/ (B) |
| **Flightcast** (Steven Bartlett's platform, Oct 2025) | Auto-clipping to Shorts, titles, descriptions, chapters "customized to match individual creators' existing styles" from their prior content; cross-platform analytics with a data chatbot. | https://www.tubefilter.com/2025/10/07/steven-bartlett-diary-of-a-ceo-flightcast-video-podcast-distribution/ (B) |
| **Captions Clips Chat** (Aug 2026) | Ask for different clips from the same long video conversationally. | https://captions.ai/help/whats-new (A) |
| **Whipscribe** | Per-speaker crops and dynamic split screen from **separately recorded sources**; "story-arc detection via Claude"; one export in 9:16, 1:1, 4:5, 16:9; self-hosted Whisper; one-time credit packs. | https://whipscribe.com/tools/clipping (C, self-description) |
| WayinVideo, Vugola, Blitzcut, Ssemble, ScaleReach, Joyspace, Cliphi | Mostly Opus clones with pricing or posting differences; many publish SEO "reviews" of each other. | https://wayin.ai/blog/opusclip-alternative/ (C); https://www.vugolaai.com/blog/best-opus-clip-alternatives-2026 (C) |
| FireCut, Gling, ChatCut, AutoCut | NLE-side assistants (Premiere plugins or web): silence cutting, retake removal, captions, podcast angle switching, chapters, **XML export** to Premiere/Resolve/FCP. | https://coldiq.com/tools/firecut-ai (C); https://chatcut.io/blog/best-ai-video-editor-2026 (C) |

### 2.4 Open-source reference implementations (useful to borrow from)

| Project | Notable technique | Source |
|---|---|---|
| OpenShorts (MIT) | Gemini moment detection over transcript plus PySceneDetect boundaries (3-15 moments); layouts **TRACK** (MediaPipe + YOLOv8), **GENERAL** (blurred background), **SPLIT** (two speakers stacked, **captions on the seam "where they cover nobody"**, switches back to a single face crop when the cut goes to one person), **SCREENCAST** (screen above presenter); faster-whisper word timings; AI hook overlays; ElevenLabs dubbing. | https://github.com/mutonby/openshorts (A) |
| ShortsFlow / shorts-generator | EMA smoothing plus velocity clamping on face-crop to prevent jitter; "Padded Silence Removal" with an **80 ms safety buffer**; Remotion spring-physics captions; presets HORMOZI, GLOW_BOX, BOUNCE, MINIMAL; 12 colour-grade presets. | https://github.com/ghost1412/shorts-generator (A) |
| AI-Youtube-Shorts-Generator, issue #81 | Documents the three classic two-person crop failures: jitter, "stays focused on only one person for too long", "switches too quickly ... very unnatural". | https://github.com/Anil-matcha/AI-Youtube-Shorts-Generator/issues/81 (A) |
| supoclip V1 spec (issue #12) | A concrete "rival Opus" motion spec: Energy preset punch-in **1.0 to 1.25x**, cut 0.15-0.20 s, hold 0.6-1.0 s, whip/slide transitions 0.30-0.35 s, 2-3 zooms max synced to caption chunks and emphasis words; Calm preset **1.0 to 1.12x**, 0.25 s entry, dissolve 0.22 s; one freeze frame per clip (0.8-1.2 s at 1.06x, audio continues) for CTA/question clips; three hook variants per clip; progress bar 8 px, 40%-opacity white track; logo 12% width bottom-left with 0.5 s fade; audio chain with sidechain ducking, whoosh on cuts, pop on hook, riser before punchlines, denoise, de-esser, presence EQ, compression, limiter, loudness normalization last; blur fallback when no B-roll matches. | https://github.com/Marwichmisi/supoclip/issues/12 (A as a spec, not a measurement) |
| Podcli | Local-first, `podcli mcp` local MCP server, transcription plus clip suggestions plus caption burn. | https://podcli.com/ (A) |
| NaufalRizqullah/opensource-clipping | Pyannote audio diarization for "who is talking", MediaPipe, Gemini, kinetic karaoke subtitles, contextual B-roll. | https://github.com/NaufalRizqullah/opensource-clipping (A) |

Research models for active speaker detection and reframing: TalkNet, Light-ASD, LoCoNet, LR-ASD (efficiency ranking LR-ASD > TalkNet > GateFusion > LoCoNet), Google AutoFlip (MediaPipe) for saliency-driven reframing (https://github.com/SJTUwxz/LoCoNet_ASD A; https://link.springer.com/article/10.1007/s11263-025-02399-2 A; https://opensource.googleblog.com/2020/02/autoflip-open-source-framework-for.html A).

---

## 3. What professional short-form editors do that the tools do not

### 3.1 The gap in one table

| Professional practice | What the tools do instead | Source |
|---|---|---|
| Design the story in text first: reduce two hours to core soundbites, then order them into an arc before touching video (DOAC editor Ant Smith). | Score contiguous windows, render them. | https://callummcdonnell.substack.com/p/meet-the-viral-editor-behind-steven (B) |
| Trailers follow **Hook, Lesson, Emotional rollercoaster, Cliffhanger**; information-heavy content gets "multiple hooks" to jolt the viewer back. | Single contiguous excerpt, one hook overlay. | same (B) |
| Enter mid-conversation at 0.0 s, speech from the first frame, no preamble. | Often start at the start of the answer's lead-in ("So yeah, I think..."). | https://www.writepanda.ai/blog/how-diary-of-a-ceo-edits-podcast-clips/ (C) |
| Put the payoff late (one analysis says 55-80% of runtime) so the open loop holds. | Picks windows by density of "hooky" sentences. | same (C) |
| Title banner that names the payoff, exits by ~5.5 s; three hook strategies: **redacted pull-forward** (mute the operative words of the best line), **banner frontload** (name the concept before it is spoken), **trap question** (open on a rhetorical question already in the source). | Generic auto-hook text. | same (C) |
| Switch caption register with emotion: bold condensed uppercase for standard content; "small lowercase mixed-case text with soft shadow, no yellow, no emoji" for emotional material. | One template for every clip. | same (C) |
| Colour-code captions by speaker (e.g. yellow host, white guest). | Rare; Opus has it as an option. | same (C); nemovideo (C) |
| Reaction cutaways of 1-1.5 s with the speaker's audio continuing (J/L cuts); switch at real turn changes, never on backchannels ("right", "exactly"). | Crop jumps to whoever makes noise; jitter on crosstalk. | writepanda (C); https://www.openshorts.app/podcast-to-shorts (C) |
| Adjust pace to emotion: somber parts move slower; natural pauses kept in serious clips. | Uniform silence removal at one threshold. | https://iamandrewellis.medium.com/4-ways-the-diary-of-a-ceo-hooks-their-audience-f0723871f8e8 (C, via search summary); writepanda (C) |
| Hide cuts: a boom SFX on the cut in trailers, or change animated text on the cut so the eye is elsewhere. | Hard jump cuts or generic cross-zoom. | Medium DOAC article (C) |
| A/B test visual decisions (opening on the guest's face beat opening on B-roll) and judge by comments plus average view duration. | Virality score. | Callum McDonnell (B) |
| Keep laughter; keep clip audio dry (no music bed) for podcast clips. | Add music beds and SFX by default. | writepanda (C) |
| End card restating the title for 1.5-2 s; emotional clips end cold on the last word. | Abrupt end or CTA. | writepanda (C) |
| Exclude sponsor reads, intros, scheduling talk and "anything that depends on a chart the viewer cannot see". | Picks them if they score. | https://overlap.ai/blogs/best-way-to-make-podcast-clips (C) |
| Verify names, numbers and the word "not" in captions because those errors reverse meaning. | ASR output shipped. | https://overlap.ai/blogs/how-to-add-captions-to-clips (C) |
| Keep slides and screens whole; never crop text off a slide. | Face-centred crop cuts slides in half; Klap centres screenshots over subjects. | shortshort (B); aitoolssme Klap test (C) |

### 3.2 Channel dossiers

**The Diary of a CEO (clips and trailers).** Base caption grammar: 1-3 words per screen, bold condensed uppercase, heavy black outline, at 60-70% of frame height (below the chin, above the title banner). Title banner: white box, black uppercase text naming the payoff, off screen by ~5.5 s. Camera follows the speaker at turn boundaries; target hard-cut cadence one cut every **4.1-6.3 s**; punch-ins break any monologue hold longer than ~12 s, alternating crops every 5-6 s, tightening to ~2.5-3 s near the payoff. Podcast clips are dry (no music, no SFX), laughter kept. Typical length 65-139 s (https://www.writepanda.ai/blog/how-diary-of-a-ceo-edits-podcast-clips/, C: an analysis piece, numbers plausible but unverified). Trailers differ: SFX booms on nearly every cut, animated text to mask cuts, emotional arcs, ~90 s, multiple hooks (Callum McDonnell interview with editor Ant Smith, B; Medium analysis, C). DOAC has since built Flightcast, whose auto-clipping learns the creator's prior clip style (Tubefilter, B).

**Alex Hormozi.** Captions: bold geometric sans in Black weight, uppercase, thick black outline plus drop shadow, word-by-word pop with slight bounce, active word yellow, previous words white; 1-3 words per caption; text in the lower third (Choppity style page https://www.choppity.com/tools/recreate-video-editing-style/alex-hormozi/, C; Ascynd spec https://ascynd.io/en/blog/hormozi-captions, C: Montserrat Black/Anton/Bebas Neue, 80-120 px on 1080x1920, stroke 8-12 px, highlight `#FFD93D` yellow or `#39FF14` green, one keyword per phrase, Y at 60-70% from top, 200-500 ms per word). Old era: TheBoldFont, uppercase, shadow, no stroke. New era: Anton, uppercase, slight shadow, yellow stroke, pop-in from bottom to top (https://www.submagic.co/blog/how-to-make-alex-hormozi-captions, C). Edit: "frequent 10-20% digital punch-ins", average shot 1-3 s via jump cuts between two framings, all pauses and fillers removed, cuts on emphasis words, minimal B-roll, no transition SFX ("the voice carries the energy"), subtle low-energy music, high-contrast warm skin on near-black background (Choppity, C). A 2026 analysis argues the aesthetic now reads as "marketing guru" content and recommends "dynamic minimalism" (clean sans, white text with subtle shadow, smooth fades) while keeping the mechanics: silence removal, zoom pulses, hook text in the first 3 s (https://joyspace.ai/hormozi-editing-style-2026-analysis, C).

**Leila Hormozi.** "Clean minimal framing, warm neutral tones, no visible captions, and confident direct-to-camera delivery" (https://www.choppity.com/tools/recreate-video-editing-style/, C). Worth noting as proof that high-performing business shorts can run captionless.

**Ali Abdaal.** Black-and-white or desaturated grade with selective colour pops (yellow accent), handwritten/script caption font in sentence case, multi-line captions to the side of the speaker, phrase-by-phrase reveals, 2-5 s shots cut at thought transitions, lo-fi/ambient music, opens with a question or reframe; paper fold-out screenshot animations (https://www.choppity.com/tools/recreate-video-editing-style/ali-abdaal/, C; https://techbullion.com/an-ultimate-guide-to-ali-abdaal-video-editing-style-and-methods/, C). Submagic's "Ali" template (built with his editing team) uses TT Fors, sober colours, word-by-word fade to black, no floating or rotation (https://www.submagic.co/blog/make-captions-like-ali-abdaal, C).

**Iman Gadzhi.** Montserrat, white only, **lowercase**, each line animates from light to bold weight as spoken, no coloured keywords, "premium" minimalism; long-form uses filmic B-roll, motion graphics, heavy sound design (https://www.submagic.co/blog/how-to-make-captions-like-iman-gadzhi, C; https://sendshort.ai/guides/iman-gadzhi-style/, C).

**Dan Koe.** Minimal black-and-white motion graphics, no "TikTok-ified" subtitles, high-contrast authority look; often faceless text-and-animation shorts (https://medium.com/@jakeFromJSI/dan-koe-isnt-doing-enough-here-7dffd35b4030, C; tutorials on YouTube).

**MrBeast captions.** Komika font, uppercase, thick black stroke, ~2 words per line, keywords in green with glow (https://www.submagic.co/blog/how-to-make-captions-like-mrbeast, C).

**Devin Jatho.** Montserrat Extra Bold, uppercase, light colours, floating motion plus glow (https://www.submagic.co/blog/how-to-make-subtitles-like-devin-jatho-in-3-clicks, C).

**Tom Noske and Codie Sanchez.** Noske: "bold 3D-shadow captions, cinematic B-roll intros, word-by-word text, shallow depth-of-field close-ups". Sanchez: "bold white captions on a warm eclectic set, text-heavy hooks" (https://www.choppity.com/tools/recreate-video-editing-style/, C).

**Modern Wisdom.** Six videos a week (three episodes, three clips); the first 15-20 s of a clip must deliver value; titles and thumbnails "open a loop" (https://podcast.creatorscience.com/chris-williamson/, B). No reliable written breakdown of the vertical shorts style was found.

**Lex Clips, Huberman Lab Clips.** Primarily horizontal 16:9 clip channels on YouTube (separate channels: https://www.youtube.com/@LexClips, https://www.youtube.com/@HubermanLabClips). No written style breakdown found. Direct observation is needed before encoding a "horizontal clip" template.

**Colin and Samir.** Their playbook teaches Ernesto Perez's **"Stop, Hook, Payoff"** method for Shorts and "respect their time" as a rule (https://www.colinandsamir.com/playbook, B).

**Lecture and talk channels (YC, Stanford, MIT).** No written breakdown found for their shorts. Evidence from tools that handle lectures well: keep slides whole, reframe only the speaker, intercut full-screen slide and speaker, or slide with the speaker as picture-in-picture (shortshort, B; https://github.com/mutonby/openshorts SCREENCAST layout, A; Opus Screenshare layout, A). Keynote slides that are mostly an image plus 5-10 words repurpose best (https://dalaillama.in/blog/turn-keynote-into-shorts, C).

### 3.3 Technique reference with parameters

Values marked **(sourced)** come from the sources cited. Values marked **(default proposal)** are engineering defaults synthesized from those sources for the skill to start with.

| Technique | Parameters and guidance |
|---|---|
| Hook window | First 1-3 s decide the swipe; TikTok's official ad guidance: "introduce your content proposition in the first 3 seconds" and "prioritize your hook in the first 6 seconds" (https://ads.tiktok.com/help/article/creative-best-practices A, sourced). A Short "has no intro... the first frame is the hook" (https://prepublish.ai/guides/youtube-shorts-retention C). Hook delivered in ~2-2.5 s (OpusClip blog C). |
| Cold open / pull-forward | Move the strongest line (or a muted/redacted version of it) to 0.0 s, then cut back to the setup; DOAC's "redacted pull-forward" (writepanda C). Opus only offers a manual "add hook sentence". **(default proposal)**: offer a pull-forward variant whenever the payoff line sits after 50% of the clip; cap the pulled line at 2-4 s; add a hard audio cut plus a short visual reset at the rejoin. |
| Text hook / title card | Opus auto-hook: first 5 s, bold black on white rounded box, avoids faces and captions (A). DOAC banner: white box, black uppercase, exits by ~5.5 s (C). TikTok ad guidance: 5-10 words per second of on-screen text (A); hook text 6-10 words in the upper-centre of the safe zone during 0-3 s (C). Slow typewriter reveals now lose viewers before the sentence finishes (https://ugccopilot.ai/blog/viral-hooks-that-convert/ via search summary, C). |
| Punch-in zoom amount | Hormozi "10-20% digital punch-ins" = 110-120% (Choppity C). supoclip Energy 1.00-1.25, Calm 1.00-1.12 (A as spec). shortshort bounds emphasis pushes to x1.0-x1.6 with one zoom level per shot (B). **(default proposal)**: 1.00 / 1.12 / 1.25 as the three framing states for 1080p-from-4K sources; cap at 1.15 when the source is 1080p to avoid softness; never exceed 1.6. |
| Zoom timing | On emphasis words, punchlines, key numbers, sentence starts (Opus blog C; Submagic "synced to transcript" A). A 30-min interview "might need 80-120 individual zoom keyframe pairs" (https://caption-x.com/auto-zoom-premiere-pro C), which is one zoom every 15-22 s in long-form; shorts run denser. Alternate framing at every jump cut so the cut reads as intentional (https://www.conbersa.ai/learn/podcast-clip-jump-cuts C: "zoom jump cuts... mask the discontinuity"). |
| Slow push-in | "Zoom pulses that slowly zoom in during serious moments" (Joyspace on Hormozi, C). **(default proposal)**: 1.00 to 1.06 over 3-6 s with ease-in-out for emotional beats, instead of hard punch-ins. |
| Jump cuts / silence removal | Remove gaps over 0.3-0.5 s for social (tutorials 0.3-0.5, solo talking head 0.5-0.7, interview cuts 0.3) with padding ~50 ms before and ~200 ms after speech (PremiereGPT default), or 250-400 ms padding and -40 to -45 dB threshold for interviews (https://www.autocut.com/en/blogs/autocut-silences-parameters/ C; https://docs.premierecopilot.com/features/jump-cut C). Opus default pause threshold 0.5 s (A). ShortsFlow uses an 80 ms safety buffer (A). 4-8 cuts per minute for podcast clips (https://www.conbersa.ai/learn/podcast-clip-jump-cuts C). "Any silence longer than 1 second damages retention" (prepublish, C). |
| J and L cuts | 1-2 per 30-60 s short; the opening 3 s favours a hard cut (https://cutfa.st/en/blog/j-cut-l-cut-audio-transition-editing-cutfast-method-2026 C). Reaction cutaways 1-1.5 s with the speaker's audio underneath (writepanda C). |
| Cut cadence / pattern interrupts | New beat every 2-3 s to every 5-7 s depending on source (OpusClip blog "one cut every 2-4 seconds", "new visual or story beat every 5-7 seconds", C). DOAC 4.1-6.3 s (C). "After approximately 12-15 seconds of a static frame... a meaningful percentage of viewers will start scrolling" (https://joyspace.ai/pattern-interrupt-reset-attention-span via search summary, C). Claims like "40-60% higher retention" are unsourced. |
| Speed ramps, whips | Used in cinematic B-roll styles (Iman Gadzhi, Tom Noske) and in transitions; supoclip whip/slide 0.30-0.35 s (A as spec). Rare in podcast clips. Speed-up of delivery: Hormozi pacing "accelerated via post-production" (Choppity C). **(default proposal)**: no speed ramps on talking heads; allow 1.05-1.10x speech speed-up only with pitch preservation and only when the user opts in. |
| B-roll cutaways | Opus data: only 6% of clips use B-roll (vendor). "Use 3-5 second B-roll clips maximum"; "keep intros under 2 seconds" (https://www.opus.pro/research/broll-visual-effects-short-form vendor). Tools get B-roll wrong often (4/11). DOAC found opening on the guest's face beat opening on B-roll (B). **(default proposal)**: B-roll off by default for podcast and lecture clips; when on, only for concrete visualizable nouns, 1.5-4 s, never in the first 2 s, prefer source-native visuals (slides, demos, screen recordings, the paper's figures) over stock. |
| Keyword pop-ups and emphasis | One highlighted word per caption phrase; "every second word is highlighted, nothing is" (overlap.ai C); Hormozi rule "exactly one keyword per phrase" (Ascynd C). Captions app "AI Emphasis" offers underline, emphasize, supersized (A). |
| Emoji | Max one emoji per caption line (Opus blog C). Off for emotional or serious clips (DOAC C). Opus/Captions/Submagic all auto-insert by default. |
| Progress bar | quso offers an auto progress bar (A); supoclip spec: 8 px, bottom, 40%-opacity white track, highlight-colour fill (A as spec). Shorts and Reels already draw a UI progress bar at the bottom, so a custom bar belongs at the top edge or not at all **(default proposal)**. |
| Looping endings | End on a line that flows back into the first frame; replays count as new Shorts views since March 31, 2025 (https://ppc.land/youtube-changes-how-shorts-views-are-counted-from-march-31/ C; https://support.sproutsocial.com/hc/en-us/articles/35874991211533-YouTube-Shorts-View-Count-Update-March-2025 B). Retention above 100% signals rewatching (https://www.shortimize.com/blog/youtube-shorts-retention-rate C). |
| Freeze frame | One per clip, 0.8-1.2 s at 1.06x, audio continues, for CTA or question clips (supoclip spec). |
| Split screen / podcast layout | Stack two speakers in half-frames when both are engaged; caption on the seam; hard-cut to the single speaker when one holds the floor (OpenShorts A; https://shortgenius.com/blog/split-screen-video-editing C). Mouth-activity normalization per speaker so lighting differences do not bias the switch (https://www.openshorts.app/podcast-to-shorts C). |
| Headline bar styles | (a) White rounded box, bold black text, top third (Opus auto-hook; DOAC banner). (b) Horizontal video centred in 9:16 with a headline in the top band and captions in the bottom band (common clip-channel format; YouTube Studio uses a blurred crop instead). (c) Solid-colour block behind phrase captions ("Subtitle Block"/"Colored Background Block", https://blitzcutai.com/blog/best-caption-style-tiktok C). |
| Letterbox vs blur-fill | Blurred copy of the source behind a sharp centre crop fills the frame; black letterboxing reads as low effort (https://www.ffmpeg-micro.com/blog/how-to-add-a-blurred-background-to-vertical-video-9-16-fill-with-ffmpeg C; https://www.wkyt.com/2026/08/06/good-question-why-do-some-videos-have-blurred-or-black-bars-sides-screen/ C). YouTube's own clip tool uses blurred crops (A). Opus "Fit" uses 4:3 with opaque padding (A). |
| Sound design | Trailers and high-energy edits: whoosh on cuts and zooms, pop on text/hook, riser whose peak lands on the punchline or reveal, hit on the reveal (supoclip spec; https://sound.krotosaudio.com/whoosh-sound-effects/ C; Epidemic riser guidance C). Podcast clips: dry (DOAC, C). Hormozi talking heads: no transition SFX (Choppity, C). Submagic bundles an SFX with every transition (A), a likely source of the "cheap" feel. |
| Music bed level | Music 18-25 dB under speech with voice near -14 LUFS; duck 6-12 dB with 30-80 ms attack and 250-700 ms release, or deeper 15-25 dB ducks (https://pureaudioinsight.com/blogs/content-production/background-music-volume-how-loud-should-it-be C; https://zellahq.com/blog/music-ducking-explained/ C). Traditional rule of thumb: voice around -12 dBFS, music -20 to -30 dBFS (Adobe community, C). |
| Colour grade | Hormozi: high contrast, warm skin, crushed blacks; Ali Abdaal: desaturated with selective yellow; Leila Hormozi: warm neutral (Choppity, C). Captions app "Looks" presets and ShortsFlow's 12 filters show grades are now a one-click layer (A). |
| Speaker labels | Colour-code or reposition captions per speaker instead of text labels to save space (overlap.ai C); DOAC uses colour per speaker (C). **(default proposal)**: a first-appearance lower-third with name and role for guests (1.5-2 s), then colour coding. |

---

## 4. Platform specifics in 2026

### 4.1 Lengths and hard limits

| Platform | Hard limit | Distribution-relevant limit | Observed clip lengths | Sources |
|---|---|---|---|---|
| YouTube Shorts | Square or vertical up to **3 min** is a Short (uploads since Oct 15, 2024) | From **Sept 24, 2026**, 1-3 min Shorts with an active Content ID claim are no longer auto-blocked; Shorts Audio Library tracks usable up to 90 s (some 60 or 30) | Paddy Galloway (5,400 Shorts, 3.3B views): most made 20-40 s but longer Shorts that held duration did better; AVD >50 s averaged 4.1M views | https://support.google.com/youtube/answer/15424877 (A); https://threadreaderapp.com/thread/1646898356419981315.html (B) |
| TikTok | 10 min in-app camera, 60 min upload | Creator Rewards requires videos **≥60 s** | Opus dataset (2.19M TikTok clips): 30-60 s = 38.5%, 15-30 s = 25.9%, 60-90 s = 18.7%, 90+ s = 13.2%; podcast clips average **56.8 s** | https://flowshorts.app/blog/how-long-can-tiktok-be (C); https://postlinkapp.com/blog/tiktok-creator-rewards-program (C); https://www.opus.pro/research/tiktok-video-guide (vendor) |
| Instagram Reels | Up to 3 min since Jan 2025 (Mosseri); 15-20 min uploads rolling out | Reels over 3 min are not recommended to non-followers | Ranking signals: watch time, likes, sends; "sends are slightly more important for unconnected content" (Mosseri, Jan 22, 2025) | https://www.socialmediatoday.com/news/instagram-officially-expands-reels-length-3-minutes/737766/ (B); https://www.dataslayer.ai/blog/instagram-algorithm-2025-complete-guide-for-marketers (C) |
| X | Free 140 s; Premium up to 4 h | n/a | Opus dataset (380K X clips): 30-60 s = 40.7%; podcast clips ~58 s; 9:16 dominant | https://buzzvoice.com/blog/how-long-can-twitter-videos-be (C); https://www.opus.pro/research/twitter-x-video-guide (vendor) |
| LinkedIn | 3 s to 15 min organic (10 min via mobile); 30 min ads | Dedicated vertical video feed promoted in 2026 | 30-90 s sweet spot reported | https://contentin.io/blog/linkedin-video-format/ (C); https://linkedgrow.ai/blog/linkedin-video-guide (C) |
| YouTube long-form clips (16:9) | n/a | Must be wider than square to avoid Shorts classification | Clip channels (Lex Clips, Huberman Lab Clips) post multi-minute horizontal segments; no reliable length study found | YouTube help above (A) |

Unreliable claims to ignore: "Shorts hard limit 60 s", "Reels 90 s max", "Reels sweet spot 7-15 s" (outdated or unsourced, e.g. https://joyspace.ai/ideal-video-length-social-platform-2026).

### 4.2 Technical delivery

| Item | Recommendation | Sources |
|---|---|---|
| Frame | 1080x1920, 9:16 for TikTok/Reels/Shorts/LinkedIn vertical; X accepts 1:3 to 3:1; LinkedIn feed also 4:5 (1080x1350) | https://www.nemovideo.com/blog/twitter-video-specs-guide-2026 (C); https://posteverywhere.ai/blog/linkedin-aspect-ratios (C) |
| Codec | H.264 High profile, MP4, AAC-LC 48 kHz (YouTube recommends 384 kbps stereo) | https://support.google.com/youtube/answer/1722171 (A) |
| Bitrate | YouTube 1080p30 8 Mbps, 1080p60 12 Mbps; 4K30 35-45 Mbps; Instagram at least 3,500 kbps (5-10 Mbps common); X 8-12 Mbps for 1080p30 | YouTube help (A); https://www.stayabundant.com/blog/best-instagram-reels-export-settings (C); nemovideo (C) |
| Frame rate | 30 fps safe everywhere; Instagram processes Reels at 30 fps (drops frames from 60) | https://doom10.org/recommended-instagram-reels-video-settings-and-specs/ (C) |
| Loudness | YouTube: -14 LUFS, -1 dBTP, turns down only (official). TikTok, Instagram, Facebook, X, LinkedIn publish no LUFS target; Meta uses adaptive xHE-AAC loudness; TikTok in-feed playback reported as not normalized (July 2026), so louder files play louder. Many creators master -10 to -12 LUFS as a deliberate trade. | https://www.forasoft.com/learn/audio-for-video/articles-audio/lufs-targets-per-platform-2026 (B); https://trackgleam.com/learn/master-for-tiktok-reels-shorts (C) |
| File size | Reels 1 GB (some sources); X 512 MB free / 8 GB Premium | sources above (C) |

### 4.3 Safe zones on a 1080x1920 canvas

| Platform | Top | Bottom | Left | Right | Safe box | Source |
|---|---|---|---|---|---|---|
| TikTok | 108 | 320 | 60 | 120 | 900x1492 | https://postplanify.com/blog/social-media-safe-zones-2026-complete-guide (C) |
| Instagram Reels | 210 | 310 | 0 | 84 | 996x1400 | same (C) |
| YouTube Shorts | 120 | 300 | 0 | 96 | 984x1500 | same (C) |
| Facebook Reels | 100 | 300 | 0 | 60 | 1080x1520 | same (C) |
| Instagram Stories | 100 | 200 | 0 | 0 | 1080x1620 | same (C) |
| Universal | centred 900x1400 box | | | | | same (C) |

Alternative published values: TikTok top ~130, bottom ~250, sides ~60; Reels top ~108, bottom ~320, sides ~60; Shorts "avoid bottom 10-15%" (https://kreatli.com/guides/safe-zone-guide C). Notched phones remove ~40 px more at the top. TikTok ads need an extra ~50 px at the bottom. A three-line platform caption with hashtags can consume 250+ px at the bottom (postplanify, C). Safe-zone guidance from a caption-placement guide: keep text out of the top 14%, bottom 35% and 6% side margins, i.e. roughly y = 270-1248 px usable (https://overlap.ai/blogs/how-to-add-captions-to-clips C). Submagic ships a safe-zone overlay filter (LinkedIn post by the founder, B).

**(default proposal)** for burned captions: centre of caption block at y ≈ 1150-1300 (60-68% of height), max width 900 px, never below y = 1400; hook card top edge at y ≥ 220.

### 4.4 Caption and title burn-in conventions

- Word-level or short-phrase captions dominate; TikTok recommends 5-10 words per second of on-screen text (A). Max two lines on screen (overlap.ai C). 1-3 words per screen for high-energy styles (DOAC, Hormozi, MrBeast ~2 words/line; C).
- In OpusClip's 13.5M-clip dataset, 80.2% of clips carry captions and 78.6% animated captions versus 1.6% static (usage share only, not performance) (https://www.opus.pro/research/best-caption-strategy-short-form, vendor).
- TikTok search indexes spoken words (ASR), on-screen text (OCR) and the post caption; saying the keyword early and showing it on screen helps discovery (https://almcorp.com/blog/tiktok-seo/ C; mechanism widely reported, magnitude claims unsourced).
- Watermarks: Instagram excludes content with other-platform watermarks from recommendations and demotes reposts/aggregators; cropping or adding a credit does not count as original (https://sociallyin.com/blog/instagram-algorithm-update-repost/ C; https://gotmenow.com/2026/05/12/instagram-original-content-rule-2026/ C). Export clean masters per platform.

### 4.5 First frame, covers, thumbnails

- YouTube Shorts: pick a frame (mobile) or one of three suggested frames on desktop; since July 2026 custom thumbnail upload for YouTube Partner Program creators (https://vidiq.com/blog/post/youtube-shorts-custom-thumbnails/ C; https://miraflow.ai/blog/youtube-shorts-custom-thumbnails-2026 C). YouTube Studio auto-links the source video as the Short's related video (A).
- Instagram: profile grid shows a **centre 3:4 crop (1080x1440)** of the 9:16 cover since 2025; keep face and title in the centre (https://www.oktopost.com/blog/instagram-grid-size-guide/ C).
- Shorts start playing before sound is on, so on-screen text lands before audio (https://www.opus.pro/blog/youtube-shorts-hook-formulas C).
- **(default proposal)**: make frame 0 a designed frame (face mid-expression plus hook card) because the first frame doubles as the default cover and the swipe decision.

### 4.6 Are hooks-as-text still effective?

Yes as reinforcement. Consensus across 2026 sources: the text hook, the spoken line and the first visual must agree; when two of the three are missing even a strong line underperforms; slow text reveals lose viewers (C sources above). OpusClip's data shows text overlays in only 4.5% of exported clips and "visual hooks" in 0.04%, so a well-made hook card is still differentiating (vendor). Leila Hormozi's captionless style shows captions are optional when delivery and framing carry the hook (C).

---

## 5. Research and credible data on retention, virality and clip completeness

### 5.1 Distribution metrics that matter

- **Viewed vs swiped away (YouTube Shorts)**: Galloway's study found Shorts under 60% VVSA "rarely performed well"; best performers sat at 70-90% (https://threadreaderapp.com/thread/1646898356419981315.html, B). Secondary benchmarks: swipe-away above 40% is a red flag; APV above 70% healthy (https://humbleandbrag.com/blog/youtube-shorts-benchmarks C). YouTube advises comparing against your own videos of similar length rather than universal numbers (https://www.shortimize.com/blog/youtube-shorts-retention-rate C).
- **Engaged views** keep the old threshold-based count and drive YPP revenue; raw views count every start or replay since March 31, 2025 (Sprout Social support, B).
- **Instagram**: watch time, likes, sends (Mosseri, C via dataslayer).
- **TikTok**: completion and rewatch weigh heavily; TikTok's own ad guidance pins the hook to 3-6 s (A).
- Retention curve reading (https://prepublish.ai/guides/youtube-shorts-retention C): sharp drop in 0-3 s means a weak hook; mid-clip dips mean dead air or over-explaining; an end drop means a non-looping close.

### 5.2 What makes a clip "complete"

- Spotify's production LLM preview system (hundreds of thousands of podcast previews, Gemini 1.5 Pro): previews must "begin engagingly, exclude ads, start/end with complete thoughts", run ~60 s; transcripts are **sentencized with start/end timestamps per sentence** so the LLM returns sentence indices, not raw timestamps; few-shot prompts refined with human feedback; LLM previews were better or equal 81% of the time in offline review (238 episodes, ~20 evaluators) and lifted evaluation time in a 6-week A/B test across 67 countries (https://arxiv.org/html/2505.23908, A).
- PodReels (human-AI teaser co-creation): LLM receives the transcript and returns sentence IDs; formative study identifies selection mental load and editing time as the two creator bottlenecks (https://arxiv.org/abs/2311.05867, A).
- Practitioner definitions: "starts where a stranger can understand the question and ends after the answer lands"; must "stand alone without episode context"; good moments combine a concrete claim or number, emotional stakes, novelty, standalone context, a quotable line, a clear payoff (https://thepodcastconsultant.com/blog/podcast-clips C; https://overlap.ai/blogs/best-way-to-make-podcast-clips C; https://www.writepanda.ai/blog/how-diary-of-a-ceo-edits-podcast-clips/ C).
- Setup without payoff is a named failure in independent tests (2short, B) as is the missed punchline (Opus, B).

### 5.3 How good are LLMs at picking highlights?

- **Rhapsody** (13,364 YouTube podcast episodes; ground truth from YouTube's "Most replayed" heatmap, 100 points per video, threshold 0.5 among top 20 segments): zero-shot GPT-4o hit rate 26.5%, Gemini text-only 32.7%, a fine-tuned Llama-3.2-1B with a segment classifier 47.7%; best precision only 0.216. Audio embeddings helped the fine-tuned model but not zero-shot models (https://arxiv.org/html/2505.19429v1, A).
- Implications: (1) naive "ask the LLM for viral moments" is weak; (2) the "Most replayed" heatmap is a free, audience-grounded prior for any source already on YouTube; (3) audio energy features need a trained combiner to help.
- Commercial tools confirm the ceiling: 20-40% discard (BIGVU, ScaleReach), 3 of 14 publish-ready (HeyGen test), Reap's own internal "1 in 5 clips reaches performance thresholds" (vendor).

### 5.4 Hook types

- OpusClip's classifier over 8,254 YouTube clips (7-day views): Expertise/Authority/Credibility hooks averaged 6,706 views; Viewer Challenge and Filter 4,739; Process Explainer 2,833; the most common types (Direct Address/Question, Shock/Surprise) averaged ~1,000 (https://www.opus.pro/research/best-video-hooks-youtube, vendor; correlational, confounded by channel size).
- Common taxonomy across sources: pattern interrupt, direct promise, question/curiosity gap, contrarian statement, stakes/story teaser, credibility/authority, challenge/filter ("if you do X, stop"), identity statement (https://www.opus.pro/blog/youtube-shorts-hook-formulas C).
- DOAC's editor: the hook "is the single most important part"; feature the unexpected; then earn trust with a lesson early (B).

### 5.5 Pauses, pacing and dead air

- Silence over ~1 s hurts (prepublish, C). Standard tools cut at 0.3-0.5 s (A/C above). Riverside keeping 8-12 s silences is called out as a defect (C). Emotional clips keep natural pauses (DOAC, C). Word density guide: ~70 words per 30 s, ~140 per 60 s (prepublish, C).

### 5.6 Captions and sound-off

- Frequently cited: captioned videos get "12% more watch time" and are "80% more likely to be watched to completion"; "85% of Facebook videos are watched without sound" (https://www.kapwing.com/resources/short-form-video-statistics-tiktok-reels-and-shorts-by-the-numbers-in-2026/ C). The 85% figure traces back to a 2016 Digiday report and should not be relied on for 2026 TikTok, which is sound-on by default (TikTok creative guidance, A). The "karaoke beats static on every metric" claim (Blitzcut, C) is unsourced.

### 5.7 Style fatigue

- Several 2026 sources report fatigue with loud Hormozi-style captions and emoji ("production blindness", reads as sales pitch) and a drift toward minimal, legible styles (Joyspace C; Iman/Ali/Leila styles as counterexamples). No controlled data found. Treat as a design reason to ship restrained defaults with loud styles opt-in.

### 5.8 Stats to treat as noise

Unsourced figures recur across SEO blogs: "pattern interrupts every 3-5 s give 40-60% higher retention", "jump cuts improve retention 10-25%", "emoji presets boost retention 15-25%", "71% decide in 3 s", "karaoke captions outperform static". None link to a study. Do not encode them as facts in the skill.

---

## 6. Design implications for a tool that beats Opus Clip

1. **Selection is the product.** Every independent test shows the effects layer is acceptable while 13-60% of clips fail on boundaries, context or topic. Spend the compute on selection: sentence-indexed transcript, candidate generation, adversarial critique ("would a stranger understand the first sentence?", "is the payoff inside the clip?", "is this a joke, tangent or sponsor read?"), then ranking with written reasons.
2. **Boundaries on sentences, not timestamps.** Sentencize with word timings (Spotify system); the model returns sentence IDs; the cut lands in the silence after the last word with 150-250 ms tail and 50-100 ms head.
3. **Use audience ground truth when available.** If the source is on YouTube, pull the "Most replayed" heatmap (the Rhapsody ground truth) as a prior. After publishing, feed real performance back (Flightcast, Reap do this).
4. **Standalone test.** Require that the first spoken sentence makes sense cold, or add a 1-line context card ("Asked why agents collude...") instead of starting earlier.
5. **Payoff placement.** Prefer windows where the payoff sits in the back half; offer a pull-forward variant when it sits late.
6. **Multi-speaker done properly.** Diarization plus active speaker detection with hysteresis: minimum shot 1.5-2 s, switch only at turn boundaries, ignore backchannels, reaction cutaways 1-1.5 s, stacked split when both are engaged, captions on the seam. Support separately recorded sources (Riverside/Zoom tracks), which Opus Split cannot.
7. **Never crop slides or screens.** Detect slides and screen shares; keep them whole (shortshort); use slide-over-speaker or PiP layouts for lectures.
8. **Bounded, motivated zooms.** Three framing states (1.00, 1.12, 1.25), one level per shot, change on emphasis words or at jump cuts, cap by source resolution, smooth tracking with EMA plus velocity clamp.
9. **Emotion-aware pacing.** Silence threshold and cut density depend on register: tight (0.3 s) for explainers, loose (keep pauses) for emotional or reflective moments.
10. **Hooks with variants.** Generate three hook cards per clip (title card, question, stake/number) plus an optional cold-open edit; keep the card short (≤8 words), top third, gone by ~5 s; make sure it agrees with the first spoken line.
11. **Caption presets that respect register.** Ship restrained defaults (Iman/Ali/"minimal" families) with loud styles (Hormozi, Beast) as options; one highlight per phrase; speaker colour coding; emoji off by default.
12. **Caption correctness as a gate.** Per-show vocabulary (names, jargon, product names) injected into ASR prompts; flag every proper noun, number and negation for review.
13. **B-roll off by default.** Only source-native visuals by default (slides, figures, demos); stock only on explicit request; never in the first 2 s.
14. **Audio chain.** Denoise, de-ess, light compression, loudness to -14 LUFS / -1 dBTP (optionally -12 for TikTok), crossfades of 10-20 ms at every jump cut to avoid "audible edits", dry voice by default, music only when asked and ducked 18-25 dB under speech.
15. **Safe-zone-aware layout.** Compute caption and card positions from per-platform safe boxes; the universal 900x1400 box by default.
16. **Per-platform renders.** Different length targets per platform (TikTok ≥60 s if monetization matters; Reels ≤3 min; Shorts ≤3 min; X ≤140 s unless Premium; LinkedIn 30-90 s), same edit decision list.
17. **Designed first frame and cover.** Frame 0 = face plus hook card; export a separate cover image with centre-safe 3:4 area for Instagram.
18. **Loop-aware endings.** End on a complete sentence that points back at the opening, or end cold; no "subscribe" outros.
19. **Editable edit decision list.** Represent every clip as a JSON EDL (source ranges, crop keyframes, caption words, overlays, audio ops) like Opus's EditingScript, so Claude and humans can edit it; render from the EDL.
20. **NLE handoff.** Export FCPXML/Premiere XML or OTIO with handles (Opus gives 30 s) plus styled caption data, which Opus's SRT-only XML lacks.
21. **Explain rankings.** Replace a 0-99 score with a short rationale per clip (hook, standalone, payoff, novelty, risk flags); Opus's score is weakly predictive.
22. **Review UX.** Storyboard contact sheet per clip (Opus has a 2x2 storyboard command), side-by-side hook variants, transcript diff of what was cut.
23. **Honest failure flags.** Flag clips that depend on unseen visuals, contain sponsor reads, jokes out of context, unverifiable claims, or private names.
24. **Clean exports.** No watermarks, native per-platform masters; this also protects Instagram originality standing.
25. **Agent-native from day one.** Opus now has a Claude connector, an MCP server and a Claude Code plugin; Reap has MCP and a CLI. Parity requires the skill to be scriptable end to end; the edge must come from judgement, craft and control.

---

## 7. Appendix A: every named caption preset found

Legend: **V** = visual description verified in a source; **I** = inferred from the name or stated inspiration only; **N** = name only, no visual evidence found.

### A.1 OpusClip caption templates

| Preset | Description | Basis |
|---|---|---|
| Karaoke | Word-by-word captions; the active word is highlighted as spoken, others stay white; Opus's default highlight colour is bright green `#04f827` | V (https://www.opus.pro/blog/best-caption-presets-styles-boost-retention; opus-skills) |
| Beasty | MrBeast-inspired: heavy uppercase comic-style type, thick black stroke, colour-highlighted keywords | I (https://clip.opus.pro/captions names MrBeast as an inspiration) |
| Deep Diver | Named creator-style preset; visual not verified | N |
| Youshaei | Jon Youshaei-inspired preset | I |
| Pod P | Podcast-oriented preset | I (name) |
| Mozi | Hormozi-inspired: bold condensed uppercase, 2-4 words at a time, word-synced, loud keyword colours (yellow emphasis, green wins, red warnings) | V (search-summary description of the Mozi format; C) |
| Popline | Words pop in line by line | I (name) |
| Think Media | Think Media-inspired preset | I |
| Simple | Plain, minimally styled captions | I |
| Gameplay | Preset for gaming/streaming clips (pairs with the 30/70 Gameplay layout) | I |
| Glitch Infinite | Glitch-effect animated captions | I (name) |
| Seamless Bounce | Words bounce in continuously | I (name) |
| Baby Earthquake | Words shake/jitter on entry | I (name) |
| Blur Switch | Words transition via a blur in and out | I (name) |
| Auto Hook card (overlay, not a caption preset) | Bold black text on a white rounded box, first 5 s, placed to avoid faces and captions | V (opus-skills; changelog) |

### A.2 Submagic templates (API list, default "Sara")

42 names returned by `GET /v1/templates` (https://docs.submagic.co/api-reference/templates): Matt, Jess, Jack, Nick, Laura, Kelly 2, Caleb, Kendrick, Lewis, Doug, Carlos, Luke, Leila, Mark, Sara, Daniel, Dan 2, Hormozi 4, Dan, Devin, Tayo, Ella, Tracy, Hormozi 1, Hormozi 2, Hormozi 3, Hormozi 5, Jason, William, Leon, Ali, Beast, Maya, Karl, Iman, Umi, David, Noah, Gstaad, Malta, Nema, seth.

| Preset | Description | Basis |
|---|---|---|
| Beast | Komika font, uppercase, thick black stroke, about 2 words per line, keywords in green with glow | V (https://www.submagic.co/blog/how-to-make-captions-like-mrbeast) |
| Iman | Montserrat, white only, lowercase, each line animates from light to bold weight as spoken, no coloured keywords | V (https://www.submagic.co/blog/how-to-make-captions-like-iman-gadzhi) |
| Devin | Montserrat Extra Bold, uppercase, choice of three light colours, floating motion with glow halo | V (https://www.submagic.co/blog/how-to-make-subtitles-like-devin-jatho-in-3-clicks) |
| Ali | TT Fors font, sober colours, word-by-word colour fade to black as spoken, no floating or rotation, punctuation support | V (https://www.submagic.co/blog/make-captions-like-ali-abdaal; founder's LinkedIn post) |
| Hormozi 1, 2, 3 | "Old" Hormozi styles with minor differences in animation and word highlighting; old Hormozi look = TheBoldFont, uppercase, shadow, no stroke | V for family (https://www.submagic.co/blog/how-to-make-alex-hormozi-captions; search summary) |
| Hormozi 4, Hormozi 5 | Newer Hormozi variants (Hormozi 4 listed under "New"); the "new" Hormozi look is Anton, uppercase, slight shadow, yellow stroke, pop-in from bottom | I (mapping of 4/5 to the new look is an inference) |
| Tracy | Word-highlight style with very bright highlighted words (a user found them hard to read even without shadow) | V (partial; search summary of a Submagic feedback post) |
| Noah | Template introduced for readability | V (partial; founder's LinkedIn post) |
| Sara | Default template; listed under "New" | N |
| Daniel, Dan 2 | Listed under "New" | N |
| Matt, Jess, Jack, Nick, Laura, Kelly 2, Caleb, Kendrick, Lewis, Doug, Carlos, Luke, Leila, Mark, Dan, Tayo, Ella, Jason, William, Leon, Maya, Karl, Umi, David, Gstaad, Malta, Nema, seth | Names only; theme categories include Speakers, Emoji, Trend, Premium | N |

### A.3 Captions app (Mirage)

- **AI Edit styles** (full-edit presets covering cuts, B-roll, zooms, music, SFX, captions; https://captions.ai/features/edit-with-ai and https://captions.ai/help/whats-new): Prism Pro (horizontal; "vivid, high-contrast visuals and dynamic motion"), Prism, Bloom (vertical), Paper II, Prime, Elevate, Impact II, Sketch, Lens, Vista, Pop, Orbit, Y2K, Form, Chalk, Linen, Evo, Focus, Lift, Stack, Align, Atrium, Aperture, Bitmap, Byline, Kai, Grit, Rocket, Sonnet. Only Prism/Prism Pro and the Bloom vs Prism Pro orientation split are described (V); the rest are N.
- **Caption styles**: "over 30 preset templates" (names not published); options include active-word colour and background, AI Emphasis (underline, emphasize, supersized), negative/inverted captions, caption background stroke, randomized rotation, auto movement and scale, AI emoji (https://captions.ai/help/docs/captions/styles, V for options).

### A.4 Descript

- Layout/template families: **Bold, Editorial, Simple, Vintage** (https://www.descript.com/clips; N for exact visuals). Default Underlord captions: generic, centred (C).

### A.5 Open-source presets

| Preset | Description | Source |
|---|---|---|
| HORMOZI (ShortsFlow) | Word spring animation, black strokes, neon highlights | https://github.com/ghost1412/shorts-generator (V) |
| GLOW_BOX (ShortsFlow) | Glassmorphic gradient pill boxes with neon glow | same (V) |
| BOUNCE (ShortsFlow) | Upward jump animation with drop-shadow glow | same (V) |
| MINIMAL (ShortsFlow) | Dark translucent box with accent border | same (V) |
| Hormozi, MrBeast, Karaoke, Minimal, Bounce, Classic (ai-video-captions) | Whisper plus FFmpeg word-level presets named after the familiar styles | https://github.com/nicolaigaina/ai-video-captions (N beyond names) |
| Split-duo, Karaoke-pop (supoclip spec) | Orange hook with cyan captions; gradient word highlight | https://github.com/Marwichmisi/supoclip/issues/12 (V as spec) |

### A.6 Creator styles offered as presets by tools

| Style | Description | Source |
|---|---|---|
| Alex Hormozi (Choppity) | Black-weight geometric sans uppercase, black outline plus shadow, active word yellow with bounce, 1-3 s shots, 10-20% punch-ins | https://www.choppity.com/tools/recreate-video-editing-style/alex-hormozi/ (V) |
| Leila Hormozi (Choppity) | No visible captions, clean minimal framing, warm neutral tones | https://www.choppity.com/tools/recreate-video-editing-style/ (V) |
| Ali Abdaal (Choppity) | Handwritten sentence-case captions beside the speaker, yellow highlights, B&W with selective colour | https://www.choppity.com/tools/recreate-video-editing-style/ali-abdaal/ (V) |
| Tom Noske (Choppity) | Bold 3D-shadow captions, word-by-word, cinematic B-roll intros | Choppity index (V) |
| Codie Sanchez (Choppity) | Bold white captions, text-heavy hooks, warm eclectic set | Choppity index (V) |
| Hormozi spec (Ascynd) | Montserrat Black/Anton/Bebas Neue, 80-120 px, 8-12 px black stroke, white fill, `#FFD93D` or `#39FF14` highlight, 1-3 words, y 60-70% | https://ascynd.io/en/blog/hormozi-captions (V) |
| DOAC standard / DOAC emotional | Bold condensed uppercase with heavy black outline, 1-3 words, y 60-70%; emotional variant small lowercase with soft shadow, no yellow, no emoji | https://www.writepanda.ai/blog/how-diary-of-a-ceo-edits-podcast-clips/ (V, C-grade source) |

### A.7 Generic style families named by 2026 caption tools

- Blitzcut's four families: **The Bold Highlight** (white bold sans, one key word yellow/red/orange, lower-middle third, static), **The Word Pop** (each word scales/fades/bounces in, centred), **The Subtitle Block** (3-5 word phrases on a semi-opaque box, lower third), **The Colored Background Block** (text on a solid yellow/white/brand block, lower third) (https://blitzcutai.com/blog/best-caption-style-tiktok, V).
- VFX AI's list: Comic Burst, Neon Punch, Clean Impact, Aqua Edge, Signature Flow, Bold Stack, Bold Duo, Purple Wave, Clean Energy, Creator Badge, Spotlight Card, Golden Frame, Flame Bold, Clean Card (one-phrase descriptions only; https://www.vfxai.com/blog/trending-caption-styles-for-2026, I).
- Opus blog families: Bold Statement, Dynamic Word-by-Word, Minimal Clean, Emoji-Enhanced, Branded Custom (V, see section 1.6).

---

## 8. Appendix B: source index (primary and most useful)

First-party and official (A):
- OpusClip help center: https://help.opus.pro/docs/article/virality-score, https://help.opus.pro/docs/article/layout-and-reframing, https://help.opus.pro/docs/article/subject-tracking.md, https://help.opus.pro/docs/article/add-transition-effects.md, https://help.opus.pro/docs/article/speech-cleanup.md, https://help.opus.pro/docs/article/ai-broll.md, https://help.opus.pro/docs/article/clip-anything-prompt-manual, https://help.opus.pro/docs/article/select-keywords, https://help.opus.pro/docs/article/change-captions.md, https://help.opus.pro/docs/article/captions-and-emojis, https://help.opus.pro/llms.txt
- OpusClip product and changelog: https://opusclip.canny.io/changelog, https://www.opus.pro/export-to-xml, https://www.opus.pro/mcp, https://www.opus.pro/blog/opusclip-clip-different, https://www.opus.pro/ai-reframe, https://github.com/opus-pro/opus-skills
- Submagic: https://docs.submagic.co/api-reference/templates, https://care.submagic.co/en/article/what-are-themes-and-themes-categories-1pv8wvz/, https://care.submagic.co/en/article/how-to-use-submagic-v2-step-by-step-guide-pafx7o/
- Captions: https://captions.ai/help/whats-new, https://captions.ai/features/edit-with-ai, https://captions.ai/help/docs/captions/styles
- YouTube: https://support.google.com/youtube/answer/15424877, https://support.google.com/youtube/answer/15824265, https://support.google.com/youtube/answer/1722171
- TikTok: https://ads.tiktok.com/help/article/creative-best-practices
- Research: https://arxiv.org/html/2505.19429v1 (Rhapsody), https://arxiv.org/html/2505.23908 (Spotify previews), https://arxiv.org/abs/2311.05867 (PodReels)
- Open source: https://github.com/mutonby/openshorts, https://github.com/ghost1412/shorts-generator, https://github.com/Marwichmisi/supoclip/issues/12, https://github.com/Anil-matcha/AI-Youtube-Shorts-Generator/issues/81

Independent tests (B):
- https://www.scalereach.ai/blog/opus-clip-review
- https://bigvu.tv/blog/opus-clip-tested-2026-where-ai-wins-40-percent-discard/
- https://www.thepodcasthost.com/recording-skills/can-opusclip-make-your-podcast-go-viral/
- https://www.heygen.com/blog/opus-pro-alternatives (competitor-authored but with a stated single-source test)
- https://www.newsshooter.com/2026/09/21/shortshort-takes-one-long-uploaded-video-creates-vertical-916-cutdowns-with-word-by-word-captions/
- https://callummcdonnell.substack.com/p/meet-the-viral-editor-behind-steven
- https://threadreaderapp.com/thread/1646898356419981315.html (Paddy Galloway)
- https://www.forasoft.com/learn/audio-for-video/articles-audio/lufs-targets-per-platform-2026

Vendor data (biased but large): https://reap.video/reports/state-of-top-ai-video-clipping-tools-2026, https://www.opus.pro/research/broll-visual-effects-short-form, https://www.opus.pro/research/best-caption-strategy-short-form, https://www.opus.pro/research/tiktok-video-guide, https://www.opus.pro/research/twitter-x-video-guide, https://www.opus.pro/research/best-video-hooks-youtube

Gaps not closed in this pass: visual appearance of most OpusClip and Submagic presets (galleries need a logged-in session with video previews); written breakdowns of Lex Clips, Huberman Lab Clips, Modern Wisdom and YC/Stanford/MIT shorts formats (needs direct viewing); Reddit threads (not fetchable from this environment).
