# Technical stack: long lecture video to polished shorts on Apple Silicon (September 2026)

Scope: a local macOS pipeline, driven by Claude Code running Python and Node scripts, that turns a long horizontal lecture or podcast recording into vertical (1080x1920) and horizontal (1920x1080) clips with word-level karaoke captions, tracked reframing, motion graphics, B-roll, music and SFX.

## 0. Test bench and what the footage looks like

Measurements in this document were taken on the author's machine: Apple M3 Pro, 36 GB, macOS 26.2, ffmpeg 8.0 (Homebrew, with libass, VideoToolbox, arnndn, no whisper filter), Node 24.9, Python 3.12 venv via uv. The machine was shared with other sessions during the tests (load average reached 80), so every timing below is a pessimistic upper bound. Scratch artifacts live in `scratchpad/bench/`.

The three files in `sources/video/` define the problem better than any generic benchmark:

| File | Format | What the frame shows |
|---|---|---|
| `in-progress-edit.mp4` | 1920x1080 H.264, 30 fps, 50 min | Phone at the back of a lecture hall. Presenter is about 200 px tall, face about 40 px. Projector screen fills the left third. Twenty or more audience heads in the foreground. |
| `edit-in-progress-Sequence01_2.mp4` | 1920x1080 H.264, 52 min | MIT classroom from the side. Presenter beside the screen. Captions are already burned in from an earlier edit. |
| `IMG_E1423.MOV` | 3840x2160 HEVC, SDR bt709, 98 min, avg 29.9965 fps (mildly variable) | Seminar room, two presenters, one slide screen, one seated guest in the foreground. |

Consequences that shape every choice below:

1. Face detectors tuned for selfies find nothing in the 1080p hall shots. Person detection at high input resolution is the reliable signal.
2. A 9:16 crop of the 1080p files is at most 607 px wide. A tight crop of a 200 px presenter means a 3x to 5x upscale, which looks soft. The 4K file allows crops down to 1080 px wide at 1:1. Recording future talks in 4K on a tripod roughly doubles the usable framing options.
3. The slide carries half the meaning in a lecture. A stacked layout (slide on top, speaker below) is the default vertical layout. speakers usually own their decks, so the filmed screen can be replaced by the crisp slide.
4. Phone audio from the back of a room arrives very quiet: the 2-minute sample measured -34.4 LUFS integrated with a true peak of -14.8 dBTP.

## 1. Recommended stack

| Stage | Tool (version) | Why | Install |
|---|---|---|---|
| Proxy / normalization | ffmpeg 8.0 | Constant 30 fps, short GOP H.264 proxy per clip window so frame indices agree across detector, transcript and renderer; VideoToolbox encode | `brew install ffmpeg` |
| Transcript, diarization | ElevenLabs Scribe v2 REST (`scribe_v2`) | Lowest WER and best word timing of the commercial APIs on the FA-Bench Buckeye conversational set; stable under noise; up to 32 speakers; 1,000 keyterms; $0.22 per audio hour | `pip install requests` (or `elevenlabs` SDK) |
| Timing refinement (optional, clip windows only) | Montreal Forced Aligner 3.4.2 | About 20 ms mean boundary error; 68% of boundaries within 20 ms | `conda create -n aligner -c conda-forge montreal-forced-aligner` |
| Local fallback ASR | parakeet-mlx 0.5.2, `mlx-community/parakeet-tdt-0.6b-v3` | 15x realtime measured on the M3 Pro; keeps fillers ("Uh"); Apache-2.0 code | `uv pip install parakeet-mlx` |
| VAD | silero-vad 6.2.3 | MIT; confirms gaps before cutting | `pip install "silero-vad[audio]"` |
| Shot detection | PySceneDetect 0.7.1 (`AdaptiveDetector`), ffmpeg `scdet` | Per-shot framing decisions; slide-change events inside the screen region | `pip install "scenedetect[opencv]"` |
| Person detection and tracking | Ultralytics 8.4.163, `yolo26n-pose.pt` at `imgsz=1280`, `device="mps"`, ByteTrack | The only fast detector that found the presenter in the wide hall shot: 16 ms per frame on MPS | `pip install ultralytics` (AGPL-3.0) |
| Which person is the presenter | One Claude vision call per scene on a frame with numbered boxes | Cheap, robust, no training | (Claude Code reads images) |
| Lip activity (big faces only) | MediaPipe 0.10.35 FaceLandmarker `jawOpen` blendshape on head crops | Works on head crops of 100 px or more | `pip install "mediapipe>=0.10.30,<1.0"` |
| Virtual camera | cvxpy 1.9.3 L1-optimal path (CLARABEL) | 0.18 s to solve one minute of frames; produces holds, constant pans and eased transitions | `pip install cvxpy` |
| Slide panel | OpenCV perspective warp of the screen quad, or the matching page of the original deck | Legible slide in the stacked layout | `pip install opencv-python` |
| Person matte for text-behind-subject | Apple Vision `VNGenerateForegroundInstanceMaskRequest` in a 60-line Swift CLI | 8 to 11 ms per 1080p frame; clean single-subject silhouette on tight crops | Xcode command line tools (`swiftc`) |
| Audio cleanup | ElevenLabs Voice Isolator for hero clips; ffmpeg `highpass` + `arnndn` + `afftdn` locally | | |
| Loudness | ffmpeg: limiter, then `loudnorm` two-pass linear to -14 LUFS / -1 dBTP; verify with `ebur128` | | |
| Music ducking | ffmpeg `sidechaincompress` + `amix normalize=0` | | |
| Final renderer | Remotion 4.0.529 with `@remotion/media`, `@remotion/captions`, `@remotion/transitions`, `@remotion/layout-utils` | Frame-driven React; springs; typed JSON props; the `remotion-best-practices` skill is already installed; free for an individual | `npx create-video@latest --yes --blank --no-tailwind` |
| Draft renderer | ffmpeg crop expression + libass ASS karaoke | 30 s vertical clip in 4.6 s | built in |
| Music, SFX | ElevenLabs Music (`music_v2_5`) and Sound Effects v2; Pixabay and Mixkit libraries | Commercial use on paid plans | API |
| B-roll | Pexels API; Wikimedia Commons API for public figures; fal.ai for generation (Veo 3.1 Fast, Kling v3) | | API keys |
| QA | ffmpeg `ebur128`, `blackdetect`, `silencedetect`; contact sheet read by Claude; geometric caption collision checks | | |

## 2. Transcription with word timings and diarization

### 2.1 ElevenLabs Scribe v2 (primary)

Endpoint: `POST https://api.elevenlabs.io/v1/speech-to-text` (multipart). Header `xi-api-key`. Regional hosts exist for US, EU, India and Singapore.

Parameters that matter for this pipeline:

| Parameter | Value to use | Notes |
|---|---|---|
| `model_id` | `scribe_v2` | Scribe v1 is no longer listed in the capability docs. `scribe_v2_realtime` is the streaming model. |
| `file` or `source_url` | file | Exactly one. `source_url` accepts hosted media including YouTube and TikTok links. `cloud_storage_url` is deprecated. |
| `timestamps_granularity` | `word` | `character` also exists; each word also carries a `characters` array. |
| `diarize` | `true` | Up to 32 speakers. |
| `num_speakers` | set when known (1 for a solo lecture, 2 or 3 for a seminar) | Max 32. |
| `diarization_threshold` | leave null unless speakers merge or split | Only meaningful with `diarize=true` and no `num_speakers`. |
| `tag_audio_events` | `true` | Emits `(laughter)`, `(applause)` as `type: "audio_event"`; useful as highlight signals. |
| `keyterms` | names and jargon: Acme, example.com, Rivera, RSI, Bostrom, ICLR | Up to 1,000 terms of up to 50 characters each; adds $0.05 per hour. |
| `no_verbatim` | leave `false` | `true` strips fillers and false starts from the transcript. The cutter needs those words with their timings, so keep verbatim output and decide what to hide at render time. |
| `language_code` | `en` | Skips language detection. |
| `webhook` | optional | Async for long files. |
| `enable_logging` | `false` if zero retention is wanted | Enterprise feature. |
| `entity_detection` | optional | Adds $0.07 per hour. |

Limits: 3 GB and 10 hours per file in standard mode (the API reference also mentions uploads under 5 GB); multichannel mode up to 5 channels. Files over 8 minutes are processed in parallel chunks internally. Minimum 100 ms of audio. The current `/clip` skill splits long recordings into 30-minute parts because it goes through the MCP tool; the REST endpoint takes the whole lecture in one call. Upload a compressed audio track (`ffmpeg -i in.mp4 -vn -ac 1 -c:a aac -b:a 64k audio.m4a`) rather than the video to cut upload time.

Pricing (API page, September 2026): Scribe v2 $0.22 per audio hour; keyterms +$0.05 per hour; entity detection +$0.07 per hour; Scribe v2 Realtime $0.39 per hour. A 50-minute lecture costs about $0.23 with keyterms.

Response shape:

```json
{
  "language_code": "en", "language_probability": 0.99,
  "text": "...",
  "words": [
    {"text": "Okay,", "type": "word", "start": 1.12, "end": 1.44, "speaker_id": "speaker_0", "logprob": -0.02,
     "characters": [{"text": "O", "start": 1.12, "end": 1.18}]},
    {"text": " ", "type": "spacing", "start": 1.44, "end": 1.68, "speaker_id": "speaker_0"},
    {"text": "(laughter)", "type": "audio_event", "start": 9.1, "end": 10.3, "speaker_id": "speaker_1"}
  ],
  "transcription_id": "...", "audio_duration_secs": 3013.1, "entities": []
}
```

Handling: drop `spacing` entries; keep `audio_event` entries in a separate track; punctuation is attached to the word text; convert `logprob` to confidence with `exp(logprob)`. Map to Remotion's `Caption` type as `{text: " " + word, startMs, endMs, timestampMs: (start+end)/2 * 1000, confidence}` (Remotion captions are whitespace sensitive: a leading space before every word except the first).

### 2.2 How accurate are the word timings?

FA-Bench (olewave/fa-bench, September 2026 snapshot) is the only public benchmark found that scores word boundary timing for commercial APIs against human labels. Track 2 on Buckeye (spontaneous conversational English, test split, clean audio):

| System | WER % | Word MAE ms | Share of boundaries within 20 / 50 / 100 ms | MAE under noise |
|---|---|---|---|---|
| ElevenLabs Scribe v2 | 10.6 | 34.8 | 43% / 78% / 95% | 35 to 37 ms (reverb, noise, music, babble) |
| Google Chirp 2 | not extracted | 26.9 | | 28 to 30 ms |
| Amazon Transcribe | | 52.8 | | |
| AssemblyAI Universal 3.5 | 12.2 | 56.4 | 25% / 57% / 88% | 63 to 69 ms |
| Deepgram Nova-3 | 10.8 | 97.8 | 18% / 41% / 73% | 84 to 104 ms |
| Whisper large-v3 (native timestamps) | 13.7 | 122.7 | 9% / 21% / 53% | 119 to 126 ms |
| Whisper then WhisperX alignment | 14.2 | 46.2 | 35% / 74% / 93% | 51 to 66 ms |
| Parakeet-TDT (one step) | 11.0 | 80.7 | 16% / 39% / 69% | 80 to 81 ms |
| Parakeet-TDT then MFA 3.4 | 10.9 | 20.3 | 68% / 93% / 98% | 27 to 36 ms |
| Parakeet-TDT then Olign 1.0 (commercial aligner) | 10.7 | 20.1 | 74% / 90% / 96% | 27 to 31 ms |
| Qwen3-ASR then Qwen3-ForcedAligner | | 30.6 | | 42 ms |

Track 1 (aligners given the true transcript, Buckeye test): MFA 3.4 21.3 ms; Charsiu 28.1; Qwen3-FA 33.8; MMS-FA (the ctc-forced-aligner family) 37.1; WhisperX 41.7; CrisperWhisper 43.1; NeMo-FA 40 ms 62.8; stable-ts 71.2.

Reading:

- Scribe v2 is the best single call: best WER of the APIs, 35 ms mean error. It barely degrades with noise, which matters for audience-POV hall audio. At 30 fps one frame is 33 ms, so 78% of words land within about 1.5 frames. That is acceptable for karaoke highlighting without refinement.
- Whisper's own `word_timestamps=True` (openai-whisper, mlx-whisper, whisper.cpp token timestamps) is about 120 ms off on average. It is the wrong source for karaoke unless followed by alignment.
- Parakeet timestamps are quantized to 80 ms encoder frames (visible in the local test: 1.12, 1.44, 1.68...). Good enough for cutting at gaps, coarse for karaoke.
- The biggest single improvement is a second-pass forced alignment. MFA on top of any decent ASR brings mean error to about 20 ms and puts two thirds of boundaries within 20 ms.

Recommendation: Scribe v2 for the whole lecture once. For the handful of selected clip windows, optionally re-align Scribe's words with MFA if a rendered clip shows early or late highlights. MFA on a 60-second window takes seconds.

MFA commands (MFA 3.4.2 on conda-forge; Apple Silicon has native builds via conda-forge; the docs mention Rosetta only as a fallback):

```bash
conda create -n aligner -c conda-forge montreal-forced-aligner -y && conda activate aligner
mfa model download acoustic english_mfa && mfa model download dictionary english_mfa
# corpus dir: clip.wav + clip.txt (or clip.lab) with the Scribe words
mfa align ./corpus english_mfa english_mfa ./aligned --clean --single_speaker
# output: TextGrid per file with word and phone tiers; out-of-vocabulary words need `mfa g2p` first
```

### 2.3 Local options on Apple Silicon

| Tool | Version | Word timing | Speed (M-series) | Notes |
|---|---|---|---|---|
| parakeet-mlx | 0.5.2 (June 2026) | token level, 80 ms quantized; merge sub-word tokens that do not start with a space | 120 s of audio in 7.8 s on the loaded M3 Pro (15x realtime); first model load 124 s including download | Default model `parakeet-tdt-0.6b-v3` (25 European languages); chunking `--chunk-duration 120 --overlap-duration 15`; CLI `parakeet-mlx audio.wav --output-format json --highlight-words`; keeps "Uh" |
| mlx-whisper | 0.4.3 (Aug 2025) | cross-attention DTW (about 120 ms error) | large-v3-turbo about 2x faster than whisper.cpp; 5x to 14x realtime depending on chip | `mlx_whisper.transcribe(path, path_or_hf_repo="mlx-community/whisper-large-v3-turbo", word_timestamps=True)` |
| whisper.cpp | via `@remotion/install-whisper-cpp` 4.0.529 | token level | about half the speed of mlx-whisper | Remotion's own caption tooling uses it; pins whisper.cpp 1.5.5 in the skill example |
| lightning-whisper-mlx | 17 commits, quiet | no word timestamps | fast batched decoding | Not suitable |
| WhisperX | 3.8.6 (May 2026), BSD-2 | wav2vec2 forced alignment, 42 to 46 ms | CPU only on Mac (`--device cpu --compute_type int8`), no MPS | Diarization via pyannote `speaker-diarization-community-1` (needs a Hugging Face token and accepted terms); `uvx whisperx` works (HyperFrames uses it) |
| mlx-qwen3-asr | 0.4.4 (Sept 2026) | Qwen3-ForcedAligner, 31 to 34 ms | MLX aligner about 2.6x faster than PyTorch | 11 languages, 300 s per call |
| ctc-forced-aligner | 1.0.2 | MMS CTC, 30 to 37 ms | CPU | Default model `mms-300m-1130-forced-aligner` is CC-BY-NC 4.0 |
| CrisperWhisper 2.0 | | 41 ms conversational; best disfluency detection (fillers as `[um]`) | PyTorch backend on Mac | Weights under a non-commercial research license |

Diarization offline: pyannote.audio 4.0.7 with `speaker-diarization-community-1` (runs on MPS or CPU; CoreML ports exist). Scribe's built-in diarization is enough for lectures with audience questions.

## 3. Subject tracking and 16:9 to 9:16 reframing

### 3.1 Detector results on the real footage

All numbers on the M3 Pro under load, over the first 90 frames of a 1080p hall clip.

| Detector | Setting | ms per frame | Result on the wide hall frame |
|---|---|---|---|
| YOLO26n-pose | imgsz 640, MPS | 8.8 | Presenter found (1 of 10 persons) |
| YOLO26n-pose | imgsz 1280, MPS | 15.9 | Presenter found (1 of 22 persons) |
| YOLO26n-pose | imgsz 1280, CPU | 103.5 | same |
| YOLO26s (detect) | imgsz 1280, MPS | 29.4 | Presenter found (1 of 34) |
| YOLO11n-pose | imgsz 640, MPS | 7.9 | Presenter missed |
| YOLO11n-pose | imgsz 1280, MPS | 21.3 | Presenter found |
| Apple Vision `VNDetectHumanRectanglesRequest` | full frame | 3.7 | 0 humans |
| Apple Vision `VNDetectFaceRectanglesRequest` | full frame | 3.4 | 0 faces |
| MediaPipe BlazeFace short range | full frame | 2.2 | 1 false positive |
| MediaPipe BlazeFace full range | full frame | 6.0 | 0 faces |
| MediaPipe FaceLandmarker | 515 px head crop from 4K | 8.3 | face found, blendshapes returned |

Takeaways:

- Use Ultralytics YOLO26 pose (current generation, NMS-free) at `imgsz=1280` on MPS for wide footage. Use `model.track(source, persist=True, tracker="bytetrack.yaml", classes=[0], imgsz=1280, device="mps")` for identities. Sample every 2nd or 3rd frame and interpolate; a 60-second clip window is about 30 seconds of detection.
- License: Ultralytics code and weights are AGPL-3.0. Private local use is fine; distributing the pipeline or running it as a network service triggers AGPL obligations or an Enterprise license. Permissive alternatives: RT-DETR or D-FINE through Hugging Face transformers (Apache-2.0), YOLOX (Apache-2.0).
- MediaPipe (Google, Apache-2.0): version 1.0.1 (Aug 2026) aborts the Python interpreter on macOS arm64 for every Tasks Vision graph that contains `TensorsToDetectionsCalculator` (face detector, pose, landmarker): `Check failed: service_ Service is unavailable` from `DrishtiMetalHelper`. `delegate=CPU` does not avoid it (google-ai-edge/mediapipe issue 6356). Pin `mediapipe>=0.10.30,<1.0` (0.10.35 works). The legacy `mp.solutions` API is gone from both lines; use `mediapipe.tasks.python.vision`. BlazeFace models are 128x128 input and meant for selfie or phone distances; they are useless on hall footage. FaceLandmarker returns 478 landmarks plus 52 blendshapes (`jawOpen`, `mouthClose`) when `output_face_blendshapes=True`.
- InsightFace 2.0 (Sept 2026) added automatic CoreML provider selection. Its SCRFD detector handles tiny faces well, but the pretrained models are non-commercial research only.

### 3.2 Which person is the presenter, who is talking

- Single presenter: the presenter is the tracked person in the stage band (above the audience head line, near the screen), standing (pose: hips and knees visible, tall box), present most of the time. Audience detections are mostly backs of heads in the lower half.
- Robust, cheap trick: draw numbered boxes on one frame per scene and ask Claude "which number is the presenter; which are speakers". Store the track id.
- Two presenters (the 4K seminar file): Scribe diarization says when the speaker changes. Map `speaker_id` to track id by (a) `jawOpen` variance correlated with the diarized speech segments on 4K head crops of 100 px or more, (b) body motion energy while speaking, (c) a vision check on three frames per turn.
- Active speaker detection models: LR-ASD (IJCV 2025, MIT, 94.45% mAP on AVA-ActiveSpeaker, `python Columbia_test.py --videoName 0001 --videoFolder demo`), Light-ASD (CVPR 2023, MIT, 94.06%), TalkNet. All assume S3FD face tracks with visible lips at roughly 64 to 112 px and CUDA-era code. On audience-POV lecture footage the face is about 40 px, so they do not apply; the diarization mapping above is more reliable here.

### 3.3 Google AutoFlip, the reference design

AutoFlip (MediaPipe legacy solution, unsupported since March 2023, still the best documented design): per shot it detects faces, people and objects; fuses them into salient regions with per-class weights and "required" flags; picks one of three camera modes per scene: stationary (subject stays within `motion_stabilization_threshold_percent`, default 0.5 of the frame), panning at constant velocity, or tracking; smooths by fitting a low-degree polynomial path to the boxes with a least-squares objective; snaps to center when close (`snap_center_max_distance_percent`); letterboxes with a blurred or solid pad when required content cannot fit. Reimplement the logic, not the C++ graph.

### 3.4 The virtual camera operator

Because the whole clip is known in advance, solve the path offline.

1. Per frame target: presenter box center x; y chosen so the eyes sit at about one third from the top; desired crop height from box height (presenter occupying 45 to 70% of the crop height in speaker-only layout).
2. Gaps: linear interpolation for gaps up to 1 s; longer gaps hold the last position.
3. Segment by shot cuts (PySceneDetect) and by planned layout changes.
4. Per segment, solve an L1-optimal path, the method of Grundmann, Kwatra and Essa (CVPR 2011, used for the YouTube stabilizer): minimize `w1*|D1 p| + w2*|D2 p| + w3*|D3 p|` subject to the crop staying inside the source frame, with a soft penalty when the target leaves an inner safe band (the dead zone). L1 norms on the derivatives produce piecewise constant (tripod holds), linear (constant-velocity pans) and parabolic (ease in and out) segments, which is how a human operator moves. The Python test (cvxpy with CLARABEL, 1800 frames, weights 10 / 1 / 100, margin 110 px, synthetic stand-walk-stand track with noise and a detection dropout) solved in 0.18 s; 86% of frames came out perfectly static; peak speed 2.35 px per frame.

```python
p = cp.Variable(N)                       # crop center x per frame
fit = cp.sum(cp.pos(cp.abs(p[obs] - x[obs]) - margin))   # dead zone
obj = cp.Minimize(10*cp.norm1(cp.diff(p,1)) + 1*cp.norm1(cp.diff(p,2)) + 100*cp.norm1(cp.diff(p,3)) + 5*fit)
cp.Problem(obj, [p >= w/2, p <= W - w/2]).solve(solver=cp.CLARABEL)
```

Solve x, y and zoom as three coupled variables or solve zoom first on a slower schedule. Add a speed cap as a hard constraint (`cp.abs(cp.diff(p)) <= vmax`).

Online or simpler alternatives (useful for previews):

- Dead zone plus critically damped spring: ignore target moves inside the dead zone (10 to 15% of crop width); otherwise `a = w^2 (target - x) - 2 w v` with `w = 2*pi / T`, `T` about 0.8 to 1.2 s. No overshoot, natural settle.
- One Euro filter (Casiez et al. 2012) on raw detections before anything else: `min_cutoff` about 0.5 to 1 Hz for jitter, `beta` tuned so fast moves lag little, `d_cutoff` 1 Hz.
- Constant-velocity Kalman filter for tracking through short occlusions.

Cut or pan:

- Pan (tracking) when the presenter walks continuously and the path fits under the speed cap (about 25 to 35% of crop width per second).
- Cut when the needed move exceeds about a third of the crop width and would take more than about a second at the cap, when the speaker changes, or when the layout changes. Place the cut in a word gap or on a sentence boundary from the transcript, keep shots at least 1.5 to 2 s. Never cut and pan into the same moment.
- Presenter walking across a stage: pull back (larger crop) while velocity is high and tighten when they stop; this "breathing zoom" hides the lag a pure pan would show. On 1080p sources keep crop width at 720 px or more (1.5x upscale ceiling).

### 3.5 When the slide matters more than the face

Signals, computed per sentence: a slide change (perceptual hash or `HashDetector` run only inside the screen quad), deictic language in the transcript ("as you can see", "this chart", "look at"), a pointing gesture (wrist keypoint moving toward the screen), the presenter standing inside the screen area, dense text on the slide.

Layouts the renderer should support, chosen per sentence by the LLM planner:

| Layout | When | Geometry in 1080x1920 |
|---|---|---|
| speaker | personal story, punchline, no slide reference | 9:16 crop following the presenter |
| stacked | default for lecture explanation | slide panel 1080x608 on top (16:9); speaker crop in the remaining 1080x1312, or a 50/50 split |
| slide | slide change or deictic reference, dense chart | slide full width, speaker as a small circle or rounded picture-in-picture |
| wide | audience laughter, applause, Q&A | letterboxed wide shot with blurred fill |

Getting a clean slide: detect the screen quad once per static camera segment (brightest large quadrilateral via `cv2.findContours` plus `approxPolyDP`, or ask Claude for four corners and refine), then `cv2.getPerspectiveTransform` and `cv2.warpPerspective` to a 1920x1080 panel. Better still: the speaker usually has the decks. Match each filmed slide to its PDF page (perceptual hash on the warped panel, or a vision call) at every slide-change timestamp, then render the original page. The filmed screen is washed out and keystoned; the original is perfect. This is the largest quality win available for lecture clips.

## 4. Scenes, silence, fillers, audio cleanup, loudness

### 4.1 Shot and slide-change detection

PySceneDetect 0.7.1 (July 2026; the docs ask you to pin `<0.8` because the API still moves):

```python
from scenedetect import detect, AdaptiveDetector, ContentDetector
scenes = detect("clip.mp4", AdaptiveDetector())          # adaptive_threshold=3.0, min_scene_len=15, window_width=2, min_content_val=15.0
scenes = detect("clip.mp4", ContentDetector(threshold=27.0, min_scene_len=15))
```

`AdaptiveDetector` tolerates camera motion (handheld phones). `HashDetector` (threshold 0.395) and `HistogramDetector` (0.05) are faster alternatives. For a single-shot phone recording, shot detection mostly matters for pre-edited files like the MIT one. ffmpeg's `scdet` filter (`-vf scdet=threshold=10`) is a quick first pass.

### 4.2 Silence and pauses

- Primary source: gaps between Scribe word timestamps. They are already aligned with the text.
- Validation: Silero VAD 6.2.3 (MIT, 16 kHz or 8 kHz, under 1 ms per 30 ms chunk on one CPU thread): `get_speech_timestamps(wav, model, threshold=0.5, min_speech_duration_ms=250, min_silence_duration_ms=100, speech_pad_ms=30, return_seconds=True)`.
- ffmpeg `silencedetect` defaults are `noise=-60dB:d=2`, far too long for pacing edits. On the quiet hall audio `silencedetect=noise=-35dB:d=0.4` found 43 pauses in 2 minutes. The threshold must be relative to the file's level, so measure loudness first.
- Pacing rule of thumb for shorts: shorten pauses over about 350 ms to 150 to 250 ms; keep pauses before a punchline.

### 4.3 Filler removal

1. Detection: verbatim transcript (Scribe with `no_verbatim=false`; Parakeet also emits "Uh"). Deterministic list for "um, uh, er, ah, hmm, mm". An LLM pass over the transcript with word ids decides contextual fillers ("like", "you know", "so", "I mean"), repeated words and false starts; it returns ids to drop.
2. Boundaries: cut in the gap between the previous kept word's end and the next kept word's start; pad 30 to 60 ms; if the gap is under about 40 ms, refine the words with MFA or cut at the lowest-energy 10 ms frame between them.
3. Audio: 10 to 20 ms crossfade at every join (`acrossfade` or `afade` in and out on each segment) to prevent clicks; keep room tone continuous.
4. Video: jump cuts in a static shot are visible. Alternate the zoom between two levels (for example 100% and 108 to 112%) on successive cuts, or cover the join with a B-roll insert or graphic.
5. Known pitfall (daily.co write-up): Whisper-based detectors tend to clip parts of real words; Deepgram misses more fillers. Scribe plus a VAD and energy check is the safer combination.

### 4.4 Denoise and enhancement

| Option | Notes |
|---|---|
| ElevenLabs Voice Isolator, `POST https://api.elevenlabs.io/v1/audio-isolation` (field `audio`, optional `file_format=pcm_s16le_16`) | Files up to 500 MB and 1 hour; accepts audio and video containers (MP4, MOV, MKV and others); $0.12 per minute on the API. Best choice for hero clips recorded from the back of a room. Run it on the clip window only. |
| DeepFilterNet3 | PyPI package last released 2023 (0.5.6); active ports: `kylehowells/DeepFilterNet-mlx` (Swift/MLX, CoreML on the Neural Engine) and the Rust `deep-filter` binary. 48 kHz, very natural for steady noise. |
| ffmpeg `arnndn` | RNNoise; needs a model file from `richardpl/arnndn-models` (for example `sh.rnnn`, `cb.rnnn`, `bd.rnnn`): `arnndn=m=cb.rnnn:mix=0.8`. Fast, sometimes gritty. |
| ffmpeg `afftdn` | Spectral denoise, defaults `nr=12:nf=-50`; `tn=1` tracks noise. Gentle on voice. |
| ffmpeg `anlmdn` | Non-local means, slower. |

None of the classical filters remove reverb. Test the isolator on 60 seconds of each room before committing.

### 4.5 Loudness normalization

Targets: -14 LUFS integrated, -1 dBTP true peak for YouTube, Shorts, TikTok, Reels, X, LinkedIn.

Measured on the hall sample: input -34.4 LUFS, true peak -14.8 dBTP. A single `loudnorm` pass fell back to dynamic mode and landed at -15.75 LUFS. Rule: `loudnorm` only runs in linear mode when `input_tp + (target_I - input_I) <= TP`. Otherwise it silently switches to dynamic mode (visible as `"normalization_type": "dynamic"` in the JSON) and can pump. Quiet phone audio needs peak control first.

Recipe:

```bash
# 1) clean + pre-gain + true-peak limiter (limit well below TP so the final gain fits)
PRE="highpass=f=80,afftdn=nr=10:nf=-45,acompressor=threshold=-24dB:ratio=3:attack=5:release=120,volume=18dB,alimiter=limit=0.5:level=false"
# 2) measure
ffmpeg -i in.wav -af "$PRE,loudnorm=I=-14:TP=-1:LRA=11:print_format=json" -f null -
# 3) apply with measured values
ffmpeg -i in.wav -af "$PRE,loudnorm=I=-14:TP=-1:LRA=11:measured_I=..:measured_TP=..:measured_LRA=..:measured_thresh=..:offset=..:linear=true" -ar 48000 out.wav
# 4) verify: expect I=-14 +/-0.5, TP <= -1, normalization_type linear
ffmpeg -i out.wav -af ebur128=peak=true -f null -
```

`ffmpeg-normalize` (pip) automates the two passes. `loudnorm` upsamples to 192 kHz internally, so always set `-ar 48000` on output. Normalize the final mix (voice plus music plus SFX), not only the voice.

### 4.6 Music ducking

```bash
ffmpeg -i voice.wav -i music.mp3 -filter_complex \
 "[1:a]volume=0.5[m];[0:a]asplit=2[v][sc];[m][sc]sidechaincompress=threshold=0.03:ratio=8:attack=10:release=350:makeup=1[duck];[v][duck]amix=inputs=2:duration=first:normalize=0[out]" \
 -map "[out]" -ar 48000 mix.wav
```

`sidechaincompress` defaults are `threshold=0.125 ratio=2 attack=20 release=250 makeup=1 knee=2.83 detection=rms`, too gentle for music under speech. `amix` divides every input by the input count unless `normalize=0`.

## 5. Rendering engines

### 5.1 Remotion 4.0.529 (recommended final renderer)

Current: `remotion` and every `@remotion/*` package at 4.0.529 (Sept 25, 2026). The license file announces changes for Remotion 5.0.

Measured on the M3 Pro (under load), 1080x1920 at 30 fps, source 1080p video scaled to fill and panned, plus TikTok-style captions with a spring pop and active-word color:

| Configuration | 150 frames (5 s) | 900 frames (30 s) |
|---|---|---|
| `@remotion/media` `<Video>`, x264, default concurrency | 8.6 s (warm) | |
| `<OffthreadVideo>`, x264, default | 9.2 s | |
| `<Video>`, `--concurrency=4` | 6.8 s | 40.4 s |
| `<Video>`, `--concurrency=6` | | 44.2 s |
| `<Video>`, `--concurrency=6 --hardware-acceleration=if-possible --video-bitrate=12M` | 6.6 s | 25.5 s |
| `<OffthreadVideo>`, `--concurrency=6` | | 61.4 s |

So a 60-second vertical clip renders in roughly 50 to 90 seconds. The first render ever downloads Chrome Headless Shell (the first run took 25 s). Use `npx remotion benchmark` to pick concurrency; on this machine 4 beat 6 and 11.

Components and packages:

- `<Video>` from `@remotion/media`: decodes with Mediabunny and WebCodecs, draws to a canvas, frame-accurate; props `trimBefore`, `trimAfter` (in frames), `playbackRate`, `volume` (static or per-frame callback), `muted`, `loop`, `objectFit`, `toneFrequency`, `audioStreamIndex`, `onVideoFrame`. Falls back to `<OffthreadVideo>` in preview and server render when the codec is unsupported (disable with `disallowFallbackToOffthreadVideo`). It is the default in the installed skill and was faster in the test.
- `<OffthreadVideo>` (core): extracts frames with the Rust compositor; still the path for alpha video (`transparent` prop, ProRes 4444 or VP9 alpha WebM) and exotic codecs.
- `@remotion/captions`: `createTikTokStyleCaptions({captions, combineTokensWithinMilliseconds, breakOnSilenceAfterMilliseconds})` returns `pages[]` with `{text, startMs, durationMs, tokens: [{text, fromMs, toMs}]}`; `ensureMaxCharactersPerLine({captions, maxCharsPerLine})`; `parseSrt`, `serializeSrt`. `Caption` is `{text, startMs, endMs, timestampMs, confidence}`.
- `@remotion/layout-utils`: `measureText({text, fontFamily, fontSize, fontWeight, letterSpacing})`, `fitText({text, withinWidth, fontFamily, fontWeight})` returns `{fontSize}`, `fitTextOnNLines({text, maxLines, maxBoxWidth, fontFamily, maxFontSize})` returns `{fontSize, lines}`, `fillTextBox`. Load the font first (`@remotion/google-fonts` `loadFont()` or `@remotion/fonts`), otherwise measurements are wrong. The test render showed a caption line running off the frame edge; fit every caption page with `fitTextOnNLines` against the safe width.
- `@remotion/transitions`: `<TransitionSeries>` with `fade`, `slide`, `wipe`, `flip`, `clockWipe`, `iris`, `none`; timing via `springTiming()` or `linearTiming()`; `<TransitionSeries.Overlay>` for effects over a cut (for example `@remotion/light-leaks` `<LightLeak seed hueShift>`, 4.0.415 and later, WebGL).
- `@remotion/lottie` (`<Lottie animationData>` synced to the frame), `@remotion/three` (`<ThreeCanvas>`), `@remotion/noise` (`noise2D/3D/4D` for organic drift), `@remotion/motion-blur` (`<Trail>`, `<CameraMotionBlur>`), `@remotion/paths` (`evolvePath`, `interpolatePath`, `getLength`) for drawn lines and arrows, `@remotion/shapes`, `@remotion/animated-emoji`, `@remotion/rounded-text-box`, `@remotion/sfx` (a few hosted SFX), `@remotion/elevenlabs`, `@remotion/web-renderer`.
- WebGL (three, light leaks, `<HtmlInCanvas>`) needs `--gl=angle` or `Config.setChromiumOpenGlRenderer("angle")`. `<HtmlInCanvas>` needs Chrome 149+ with a flag.
- Hardware encoding: `--hardware-acceleration=if-possible|required` (VideoToolbox ProRes from 4.0.228, H.264/H.265 from 4.0.236). `--crf` does not apply to hardware encoders; use `--video-bitrate` (8M for 1080p H.264 matches software file sizes; 10 to 12M for 1080x1920 with fast motion).
- Transparent output for overlays: `--codec=prores --prores-profile=4444 --pixel-format=yuva444p10le --image-format=png`, or VP9 WebM with `yuva420p`.
- Rules the skill enforces: animate only from `useCurrentFrame()` with `interpolate()`, `spring()` and `Easing`; CSS transitions, CSS animations and Tailwind animation classes do not render correctly.

License: free for individuals, for-profit companies with up to 3 employees, non-profits and evaluation, including commercial output. Otherwise a Company License: Creators $25 per seat per month with a 3-seat minimum; Automators $0.01 per render with a $100 monthly minimum; Enterprise from $500 per month. an individual making their own videos qualifies for free use. If the pipeline becomes a Acme product or runs for Acme with more than 3 employees, it needs the Automator license.

### 5.2 ffmpeg filtergraph plus libass ASS

Measured: the same 30-second vertical clip (scale, time-varying crop expression, ASS karaoke with a pop-in transform) rendered in 4.6 s with `h264_videotoolbox` and 10.0 s with libx264 medium. About 6x faster than Remotion. Ideal for drafts, previews and "captions only" variants.

What ASS can do: `\k`, `\kf` (left-to-right fill sweep), `\ko` karaoke; `\t(t1,t2,accel,...)` to animate `\fscx`, `\fscy`, `\frz`, `\c`, `\alpha`, `\bord`, `\blur`, `\clip`; `\move`, `\pos`, `\org`, `\fad`/`\fade`; rectangular and vector `\clip` masks; vector drawing mode `\p`; custom fonts via `ass=file.ass:fontsdir=fonts/`.

What it cannot do: real springs (only approximations by chaining `\t` with an `accel` exponent), per-frame data-driven motion except by writing one event per frame, images or video layers, gradients, blend modes, occlusion behind a subject (needs a separate matte and ffmpeg `overlay`/`alphamerge`), layout measurement. Per-frame reframing in pure ffmpeg works with `crop` expressions or `sendcmd` files, or by piping frames from Python (PyAV 18 or OpenCV) with subpixel `warpAffine`.

### 5.3 Alternatives

| Engine | Status (Sept 2026) | Verdict |
|---|---|---|
| HyperFrames (HeyGen), `hyperframes` 0.8.80 | Apache-2.0, 53.6k GitHub stars, updated daily, Node 22+ and ffmpeg. HTML plus data attributes; animations via GSAP, CSS, Lottie, Three.js, Anime.js, WAAPI through seekable adapters; headless Chrome capture plus ffmpeg; 21 agent skills including `/embedded-captions` (text behind the subject) and `/talking-head-recut` (lower thirds, callouts, PiP) | The strongest alternative. No license threshold. Agent-first by design. Not benchmarked here. Worth adopting if the Remotion company license becomes relevant. Worth reading now for its caption rules (below). |
| Revideo 0.11.0 (July 2026) | Fork of Motion Canvas for programmatic rendering; TypeScript generators on canvas | Smaller ecosystem; good for diagram-style animation |
| Motion Canvas 3.17.2 (Feb 2025) | Quiet for 19 months | Skip |
| MoviePy 2.2.1 (May 2025) | Python per-frame compositing; v2 renamed the API (`with_*`, `subclipped`) | Fine for simple assembly, slow and limited for motion graphics |

HyperFrames' `/embedded-captions` skill encodes production rules worth copying into the Remotion pipeline: most words go on a readable "rail" (lower subtitle in front of the subject); only the peak word of a thought is "embedded" behind the subject; at most one hero per beat with at least 0.6 s between hero windows; caption timings must match the transcript within 80 ms; every word keeps its own timing entry; group windows must envelop their words; do not animate `letter-spacing` or `filter: blur` on word entrances; the matte is the person (u2net_human_seg, CPU, about 2 fps at 1080p per their docs); CoreML execution was banned for matting after it corrupted face alpha with RVM.

### 5.4 Recommendation

Remotion as the final renderer, with ffmpeg on both sides.

- Dynamic crop and zoom from per-frame data: the camera path JSON becomes a per-frame transform on `<Video>` (or on a pre-cropped proxy). Subpixel, deterministic, no filter syntax.
- Animated word captions with springs: `spring()` and `interpolate()` per token, `createTikTokStyleCaptions` for paging, `fitTextOnNLines` for fitting. ASS cannot express springs.
- Motion graphics (kinetic type, charts, quote cards, lower thirds, logo reveals): React components with typed props; SVG, Lottie, Three.js and noise all frame-synced.
- B-roll with transitions: `TransitionSeries` plus light leaks and motion blur.
- Audio: keep Remotion's media muted. Build the audio mix in ffmpeg (clean dialogue, ducked music, SFX, two-pass loudness on the final mix), then mux: `ffmpeg -i video.mp4 -i mix.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -shortest out.mp4`. Remotion's per-frame `volume` callbacks can duck but cannot sidechain-compress or measure loudness.
- ffmpeg alone renders the fast drafts.

Performance pattern: pre-cut the clip window with ffmpeg into a constant 30 fps, short-GOP H.264 proxy (`-fps_mode cfr -r 30 -g 30 -c:v h264_videotoolbox -b:v 20M`). When the crop never exceeds a fixed region, pre-crop generously so the browser does not decode 4K frames. The iPhone file is mildly variable frame rate (average 29.9965 fps); normalizing to CFR keeps detector frames, transcript times and render frames on the same index. iPhone originals are often HLG HDR (`color_transfer=arib-std-b67`); tone-map to bt709 during the proxy step (`zscale` plus `tonemap`) or colors will look wrong. The MIT file already has burned-in captions; use the raw recording.

## 6. Motion graphics generated by an LLM agent

Pattern that works with Claude Code:

1. The planner writes `edl.json`, validated by a zod schema shared with the Remotion project: source windows (in/out), layout per sentence, camera path file, captions file, overlays `[{type: "quote_card" | "lower_third" | "stat" | "chart" | "broll" | "title", from, durationInFrames, props}]`, transitions, SFX cues, music bed.
2. A component registry maps `type` to a vetted React component with a typed props interface. Most clips need only registry components with new props.
3. Bespoke graphics: the agent writes `src/bespoke/<clip-id>.tsx` implementing a fixed interface (`{durationInFrames, props}`), then runs `tsc`, renders 3 to 5 stills with `npx remotion still <comp> --frame=N --props=edl.json`, inspects them visually, fixes, then renders. Stills are cheap; full renders are for the end.
4. Big data (camera paths, word lists) goes in files under `public/` loaded with `staticFile()` plus `useDelayRender()`, or passed as `--props=path/to/edl.json` (a file path works).

Building blocks by effect:

| Effect | Approach |
|---|---|
| Kinetic typography | Per-word `spring({frame: frame - start, fps, config: {damping: 12 to 18, stiffness: 150 to 220}})` driving scale, y and opacity; stagger 2 to 4 frames; `fitText` for the hero word |
| Charts | Hand-written SVG bars and lines animated with `interpolate` and `spring`; `@remotion/paths` `evolvePath` for line draws; the installed skill ships a bar chart asset |
| Quote cards, lower thirds | Registry components; `@remotion/rounded-text-box` for tight caption plates |
| Logo reveals | SVG path draw with `evolvePath`, a mask wipe, or a Lottie file |
| Diagrams | Manim Community 0.21.0 (Aug 2026) rendered with transparency (`manim -qh --transparent --format webm scene.py`) and layered with `<OffthreadVideo transparent>` or `<Video>` on VP9 alpha; or Revideo |
| Lottie | Reuse LottieFiles assets and change colors and text; generating Lottie JSON from scratch is verbose and brittle for an LLM. The Python `lottie` package (0.7.2) is AGPL. |
| 3D | `@remotion/three` with `--gl=angle` |

Motion (framer-motion) 13.4.4 inside Remotion: its animations run on wall-clock time, so renders come out nondeterministic unless each animation is seeked from the current frame. Use Remotion's own `spring`, `interpolate` and `Easing`. GSAP is fine inside HyperFrames because its adapters seek timelines.

## 7. Fonts

| Font | Source and license | Notes for captions |
|---|---|---|
| TikTok Sans | Google Fonts (OFL), added April 2025, updated June 2026 | Variable: `wght` 300 to 900, `wdth` 75 to 150, `opsz` 12 to 36, `slnt` -6 to 0. Designed for the platform's own UI; condensed widths fit more words per line. |
| Inter, Inter Tight | Google Fonts (OFL) | `wght` 100 to 900, `opsz` 14 to 32; Inter Tight for heavy caption weights |
| Geist | Google Fonts (OFL) | `wght` 100 to 900 |
| Montserrat | Google Fonts (OFL) | The classic 800/900 creator caption look |
| Poppins | Google Fonts (OFL) | Static weights only |
| Instrument Serif | Google Fonts (OFL) | Single weight plus italic; good for quote cards and editorial titles |
| Bricolage Grotesque | Google Fonts (OFL) | `opsz` 12 to 96, `wdth` 75 to 100, `wght` 200 to 800; characterful display |
| Space Grotesk | Google Fonts (OFL) | `wght` 300 to 700 |
| Others worth a look | Anton, Bebas Neue, Archivo (width axis 62 to 125), Unbounded, Fraunces, Schibsted Grotesk (all OFL) | |
| Satoshi, General Sans | Fontshare, ITF Free Font License | Free for personal and commercial use including video; redistribution of the font files is not allowed, so keep them out of any public repo (the Fontshare license pages did not render for verification) |

Load OFL fonts in Remotion with `@remotion/google-fonts/<Name>` (`loadFont()` supports subsets and weights) so `measureText` sees them. For ASS drafts, point `fontsdir=` at local TTFs.

## 8. B-roll, stills and segmentation

### 8.1 Stock libraries

| Source | API | Limits | License and attribution |
|---|---|---|---|
| Pexels | `GET https://api.pexels.com/v1/search` and `/v1/videos/search`; header `Authorization: <key>`; params `query`, `orientation` (landscape, portrait, square), `size` (large 4K, medium FHD, small HD), `min_width`, `min_height`, `min_duration`, `max_duration`, `per_page` up to 80 | 200 requests per hour, 20,000 per month; more on request | Free commercial use; API terms ask for a prominent link to Pexels and credit to creators where possible. `video_files[]` carries `quality`, `width`, `height`, `fps`, `link`. |
| Pixabay | `GET https://pixabay.com/api/` and `/api/videos/`; `key=` | 100 requests per 60 s; responses must be cached 24 h; no permanent hotlinking of images | Pixabay Content License; show that results come from Pixabay. Video sizes large (3840x2160), medium, small, tiny. |
| Unsplash | `GET /search/photos` | 50 per hour demo, 1,000 per hour in production | Hotlinking required; call `download_location` on every download; attribution required |
| Wikimedia Commons | MediaWiki API (below) | Send a descriptive User-Agent | Per-file license (CC BY, CC BY-SA, public domain). Credit as Title, Author, Source, License. Personality rights apply to identifiable people. |
| Coverr, Mixkit | web downloads | | Mixkit has separate Free and Restricted licenses for stock video; check per asset. |

Commons query for photos of a public figure (tested live):

```bash
curl -A "content-brain/0.1 (contact)" "https://commons.wikimedia.org/w/api.php?action=query&generator=search&gsrsearch=filetype:bitmap%20%22Dario%20Amodei%22&gsrnamespace=6&gsrlimit=10&prop=imageinfo&iiprop=url|size|extmetadata&iiurlwidth=1080&iiextmetadatafilter=LicenseShortName|Artist|Credit|UsageTerms|AttributionRequired&format=json"
```

It returned, among others, "Dario Amodei at TechCrunch Disrupt 2023 01.jpg" (4000x2667, CC BY 2.0, TechCrunch) and "Dario Amodei in 2023.jpg" (1400x2240, CC BY 2.0, UK Prime Minister). Wikidata's `P18` property gives the canonical portrait when present (`wbsearchentities` then `Special:EntityData/<Q>.json`). Put the credit line on screen or in the post text; CC BY-SA crops count as adaptations.

### 8.2 Generative video and images (fal.ai as aggregator)

| Model | Endpoint | Price | Notes |
|---|---|---|---|
| Veo 3.1 | `fal-ai/veo3.1` (also `/image-to-video`, `/first-last-frame-to-video`, `/reference-to-video`, `/extend-video`) | $0.20 per second without audio, $0.40 with audio (720p/1080p); 4K $0.40 / $0.60 | 8 s per generation, 24 fps, 16:9 and 9:16; extend up to about 148 s |
| Veo 3.1 Fast | `fal-ai/veo3.1/fast` | $0.10 / $0.15 per second (720p/1080p) | Best value for B-roll |
| Kling Video v3 Pro image-to-video | `fal-ai/kling-video/v3/pro/image-to-video` (4K variant exists) | $0.112 per second, $0.168 with audio | 3 to 15 s; aspect follows the start image |
| Seedance 2.5 image-to-video | `bytedance/seedance-2.5/image-to-video` | about $0.47 per second at 720p, $0.22 at 480p | Native 30 s clips; 9:16 supported |
| Nano Banana Pro | `fal-ai/nano-banana-pro` (+ `/edit`) | $0.15 per image, 4K at double | 1K, 2K, 4K; 9:16 supported |
| Cheap image models | Seedream V4 $0.03, Nano Banana $0.0398, Flux Kontext Pro $0.04 per image | | |
| BiRefNet video background removal | `fal-ai/birefnet/v2/video` | listed at $0 per compute second | WebM with alpha, up to 1920x1080 |

Runway API: $0.01 per credit; Gen-4.5 12 credits per second ($0.12/s); Veo 3.1 through Runway 10 to 40 credits per second; Aleph 2 28 credits per second. Higgsfield API: `https://api.higgsfield.ai`, header `Authorization: Key <HF_API_KEY_ID>:<HF_API_KEY_SECRET>`, submit then poll by `request_id` or webhook, outputs kept at least 7 days, Python and TypeScript SDKs; keys are read from the environment. Luma pricing was not verified.

For a lecture channel, generated B-roll should stay rare: an honest cutaway (a real screenshot of the agent run, the paper figure, the slide) usually beats a generated scene. It also fits rule 1 of the content brain.

### 8.3 Person segmentation for text behind the speaker

Measured on the M3 Pro, 1080p frames:

| Method | ms per frame | Quality on a tight 4K crop | On the wide 1080p hall shot |
|---|---|---|---|
| Apple Vision `VNGeneratePersonSegmentationRequest` fast | 4.1 (256x192 mask) | coarse | empty |
| same, balanced | 10.6 (512x384 mask) | usable | empty |
| same, accurate | 43.2 (2016x1512 mask) | good edges; includes every person plus the table in front | empty |
| Apple Vision `VNGeneratePersonInstanceMaskRequest` (macOS 14+) | 7.9 | per-person instances (3 found in the seminar frame) | |
| Apple Vision `VNGenerateForegroundInstanceMaskRequest` (macOS 14+) | 10.8 | cleanest single-subject silhouette | |
| MediaPipe selfie multiclass 256x256 | slow under load in this test | soft edges, grey background bleed | |
| rembg `u2net_human_seg` (HyperFrames' matte) | about 2 fps on CPU per HyperFrames docs | clean single subject | |
| RobustVideoMatting | CoreML models ship at 1920x1080 with fixed `downsample_ratio=0.25` | temporally stable matting | |
| MatAnyone (CVPR 2025) | heavy; MPS works | best temporal consistency (propagates a first-frame mask) | |
| SAM 2.1 / SAM 3.1 | MLX ports exist (`mlx-community/sam3.1-bf16`, about 870M params) | promptable video tracking | overkill |

Recommendation: Apple Vision instance masks through a small Swift CLI (`swiftc -O vision_bench.swift`; the working code is in `scratchpad/bench/vision_bench.swift` and `seg.swift`). Use `VNGenerateForegroundInstanceMaskRequest` (or the person instance request when a second person must be excluded), call `generateScaledMaskForImage(forInstances:from:)` for a full-resolution mask, write a grayscale mask video, smooth alpha over time (exponential moving average or a 3-frame median plus 1 to 2 px feather) to remove flicker, then build the foreground layer with ffmpeg `alphamerge` into ProRes 4444 or VP9 alpha WebM and stack it above the text layer in Remotion. The mask aspect differs from the input (2016x1512 for a 1920x1080 frame); scale it back to the frame size.

Condition that matters more than the model: every Apple model returned an empty or broken mask on the wide 1080p hall frame where the presenter is about 300 px tall. Run segmentation on the reframed crop. Only use the text-behind effect when the presenter fills at least about 40% of the frame height. In practice that means the 4K recordings or close shots, with one embedded hero word per beat.

pyobjc can call Vision from Python (`pyobjc-framework-Vision` 12.2.2), but a compiled Swift CLI that reads the video with AVFoundation is simpler and faster.

## 9. Audio assets and mixing

ElevenLabs Sound Effects: `POST https://api.elevenlabs.io/v1/sound-generation` with `text`, `duration_seconds` 0.5 to 30 (auto if null), `prompt_influence` 0 to 1 (default 0.3), `loop` (v2 only), `model_id` `eleven_text_to_sound_v2`, `output_format`. API price $0.12 per minute generated.

Eleven Music: `POST https://api.elevenlabs.io/v1/music` with `prompt` or `composition_plan` (not both), `music_length_ms` 3,000 to 600,000, `model_id` `music_v1` | `music_v2` | `music_v2_5`, `force_instrumental` (prompt mode only), `seed` (not with a plan), `output_format`. API price $0.15 per minute. Terms: all paid plans allow commercial use without attribution; the Free plan is non-commercial and requires crediting Eleven Music; self-serve plans exclude film, TV, radio and studio games; distribution to streaming services needs Creator or above. Social media use is covered on paid plans.

Free SFX libraries: Pixabay sound effects (Pixabay Content License, commercial, no attribution); Mixkit sound effects (Mixkit Free License); Freesound (per-file license: filter to CC0, avoid CC BY-NC); Sonniss GDC Game Audio bundles (royalty-free, commercial, no attribution); Zapsplat (free tier requires attribution); BBC Sound Effects (RemArc license is personal, educational and research only, so unsuitable here); the Remotion `@remotion/sfx` set (whoosh, whip, page-turn, switch, click, shutter, ding, vine-boom). These license summaries are from the libraries' public terms and were only partly re-verified this session.

Practical mix levels for talking-head shorts (working practice, not a standard):

- Dialogue: final mix at -14 LUFS integrated, -1 dBTP.
- Music bed under speech: about 18 to 24 dB below the voice (roughly -32 to -38 LUFS short-term while talking), rising 6 to 10 dB in gaps and on the outro; duck with a 10 ms attack and 300 to 400 ms release.
- SFX: whooshes and risers peak around -12 to -6 dBFS and sit 6 to 10 dB under the voice; place hits 1 to 2 frames before the visual event; keep density low (one accent every few seconds at most); never put an SFX on top of a word the viewer must hear.

## 10. Evaluating output automatically

Hard checks (ffmpeg and ffprobe, scriptable, zero cost):

```bash
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,pix_fmt,sample_rate -show_entries format=duration -of json out.mp4   # 1080x1920, 30/1, yuv420p, 48000, duration == EDL
ffmpeg -i out.mp4 -af ebur128=peak=true -f null -          # I = -14 +/- 1, true peak <= -1
ffmpeg -i out.mp4 -af astats=metadata=0 -f null -          # clipping: peak level, samples at peak
ffmpeg -i out.mp4 -vf blackdetect=d=0.1:pic_th=0.98:pix_th=0.10 -an -f null -   # black flashes
ffmpeg -i out.mp4 -vf freezedetect=n=-60dB:d=0.5 -an -f null -                 # stuck frames (lecture shots can be legitimately still; apply to overlay windows or tighten n)
ffmpeg -i out.mp4 -af silencedetect=noise=-45dB:d=0.8 -vn -f null -            # dead air
```

Defaults for reference: `blackdetect d=2.0 pic_th=0.98 pix_th=0.10`; `freezedetect n=-60dB d=2`.

Geometric checks (computed, no model):

- Caption collision: export every caption page's rendered box (Remotion `measureText` at render planning, or dump `getBoundingClientRect()` from a still render) and intersect with the presenter's face box and person mask for the same frames. Required: zero overlap with the face; under about 10% overlap with the body unless the caption is intentionally embedded.
- Platform UI zones on 1080x1920: keep captions and key graphics roughly inside x 90 to 990 and y 250 to 1340. The bottom 20 to 35% carries captions, names and buttons on TikTok, Reels and Shorts; the right edge carries the action column. These are commonly cited approximations; Meta's own Reels guidance could not be fetched this session.
- Subject in frame: rerun the detector on the output frames; the presenter box must stay inside the frame with headroom. No crop line should cut through the face.
- Text overflow: caption width at or below the safe width after `fitTextOnNLines`.
- Burned-in text in the source: OCR (Apple `VNRecognizeTextRequest`, or tesseract through ffmpeg's `ocr` filter, which this build includes) on source frames, so a new caption layer never stacks on old captions.
- AV sync: cross-correlate the output audio with the source window. Spot-check that highlighted words match audio onsets within 80 ms.

Vision review with Claude: build one contact sheet per clip and let the agent read it with the Read tool (it can view images directly, so no API call is needed inside Claude Code):

```bash
ffmpeg -i out.mp4 -vf "fps=1/2,scale=270:-1,drawtext=text='%{pts\:hms}':x=8:y=8:fontsize=18:fontcolor=white:box=1:boxcolor=black@0.5,tile=6x3" -frames:v 1 sheet.png
```

Ask for a structured verdict per tile: subject fully in frame, face covered by text, caption readable, text off the edge, slide legible, awkward crop (cutting at joints or the chin), obvious jump cut. Add 3-frame strips around every cut and transition. This is how the burned-in captions in the MIT file and the overflowing caption line in the test render were spotted during this research.

## 11. Gotchas collected

1. `mediapipe` 1.0.1 crashes Python on macOS arm64 for vision tasks with detections; pin `<1.0`. `mp.solutions` no longer exists.
2. Selfie-grade face detectors (MediaPipe BlazeFace, Apple Vision) return nothing on back-of-hall lecture footage. Use YOLO26 at `imgsz=1280`.
3. Ultralytics is AGPL-3.0.
4. InsightFace, CrisperWhisper and the default ctc-forced-aligner model carry non-commercial weight licenses.
5. Whisper's built-in word timestamps are about 120 ms off; Parakeet's are 80 ms quantized; Scribe v2 is about 35 ms; MFA refinement reaches about 20 ms.
6. Scribe `no_verbatim=true` deletes the fillers the cutter needs.
7. The REST STT endpoint takes files up to 3 GB and 10 hours; splitting into 30-minute parts is only an MCP-tool habit.
8. `loudnorm` silently switches to dynamic mode when the gain would push true peak over the target; quiet phone audio (here -34 LUFS) needs a limiter first. Always set `-ar 48000` after `loudnorm`.
9. `amix` halves levels unless `normalize=0`.
10. Remotion: animate only from `useCurrentFrame`; `--crf` does not apply with hardware encoding; WebGL needs `--gl=angle`; load fonts before measuring; captions need a leading space per word; the first render downloads Chrome Headless Shell; big props go in files.
11. `@remotion/media` `<Video>` rendered faster than `<OffthreadVideo>` here (40 s against 61 s for 30 s of 1080x1920); keep `<OffthreadVideo transparent>` for alpha layers.
12. Normalize phone footage to constant 30 fps (the iPhone file averages 29.9965) and tone-map HLG sources before detection and rendering.
13. Apple Vision person masks come back at their own resolution and aspect (2016x1512 for 1920x1080); scale to frame. They fail on small subjects; segment the crop.
14. Motion (framer-motion) is wall-clock driven and breaks deterministic renders.
15. Satoshi and General Sans are free to use in videos but their files must not be redistributed.
16. Remotion is free for individuals; a Acme deployment with more than 3 employees needs a paid license. HyperFrames (Apache-2.0) has no threshold.

## 12. Sources

- ElevenLabs STT API reference: https://elevenlabs.io/docs/api-reference/speech-to-text/convert
- ElevenLabs STT capability page: https://elevenlabs.io/docs/capabilities/speech-to-text
- ElevenLabs API pricing: https://elevenlabs.io/pricing/api
- Scribe v2 announcement (Jan 9, 2026): https://elevenlabs.io/blog/introducing-scribe-v2
- ElevenLabs Voice Isolator: https://elevenlabs.io/docs/capabilities/voice-isolator and https://elevenlabs.io/docs/api-reference/audio-isolation/convert
- ElevenLabs Music API: https://elevenlabs.io/docs/api-reference/music/compose ; capability page https://elevenlabs.io/docs/capabilities/music ; terms https://elevenlabs.io/eleven-music-model-specific-terms
- ElevenLabs Sound Effects API: https://elevenlabs.io/docs/api-reference/text-to-sound-effects/convert
- FA-Bench (Sept 2026 snapshot): https://github.com/olewave/fa-bench ; track 2 Buckeye: records/202609/en/asr/word/buckeye/README.md and Details.md ; track 1: records/202609/en/gold/word/{buckeye,timit}/README.md
- WhisperX: https://github.com/m-bain/whisperX ; timing issue vs MFA: https://github.com/m-bain/whisperX/issues/1247
- parakeet-mlx: https://github.com/senstella/parakeet-mlx
- mlx-whisper: https://pypi.org/project/mlx-whisper/ ; mlx vs whisper.cpp benchmark: https://notes.billmill.org/dev_blog/2026/01/updated_my_mlx_whisper_vs._whisper.cpp_benchmark.html ; mac-whisper-speedtest: https://github.com/anvanvan/mac-whisper-speedtest
- lightning-whisper-mlx: https://github.com/mustafaaljadery/lightning-whisper-mlx
- ctc-forced-aligner: https://github.com/MahmoudAshraf97/ctc-forced-aligner
- Montreal Forced Aligner: https://montreal-forced-aligner.readthedocs.io/en/latest/installation.html
- Qwen3-ForcedAligner / mlx-qwen3-asr: https://huggingface.co/Qwen/Qwen3-ForcedAligner-0.6B ; https://github.com/moona3k/mlx-qwen3-asr/
- CrisperWhisper: https://github.com/nyrahealth/CrisperWhisper
- pyannote community-1: https://www.pyannote.ai/blog/community-1
- MediaPipe PyPI: https://pypi.org/project/mediapipe/ ; face detector models: https://developers.google.com/edge/mediapipe/solutions/vision/face_detector ; face landmarker: https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker ; macOS 1.0.1 abort: https://github.com/google-ai-edge/mediapipe/issues/6356
- AutoFlip: https://github.com/google/mediapipe/blob/master/docs/solutions/autoflip.md ; https://research.google/blog/autoflip-an-open-source-framework-for-intelligent-video-reframing/
- L1-optimal camera paths (Grundmann, Kwatra, Essa, CVPR 2011): https://research.google.com/pubs/archive/37041.pdf
- Ultralytics YOLO26: https://github.com/ultralytics/yolo26 ; CoreML export: https://docs.ultralytics.com/integrations/coreml
- InsightFace: https://github.com/deepinsight/insightface
- LR-ASD: https://github.com/Junhua-Liao/LR-ASD ; Light-ASD: https://github.com/Junhua-Liao/Light-ASD
- auto-vertical-reframe (YOLOv11 + ByteTrack + AdaptiveDetector reference): https://github.com/KazKozDev/auto-vertical-reframe
- Apple Vision: https://developer.apple.com/documentation/vision/vngeneratepersonsegmentationrequest ; https://developer.apple.com/documentation/vision/vngenerateforegroundinstancemaskrequest
- RobustVideoMatting: https://github.com/PeterL1n/RobustVideoMatting ; MatAnyone: https://github.com/pq-yang/MatAnyone ; SAM 3.1 MLX: https://huggingface.co/mlx-community/sam3.1-bf16
- PySceneDetect: https://www.scenedetect.com/docs/latest/api.html and /api/detectors.html
- Silero VAD: https://github.com/snakers4/silero-vad
- ffmpeg filters: https://ffmpeg.org/ffmpeg-filters.html ; arnndn models: https://github.com/richardpl/arnndn-models
- DeepFilterNet MLX/CoreML: https://github.com/kylehowells/DeepFilterNet-mlx
- Filler removal write-up: https://www.daily.co/blog/ai-assisted-removal-of-filler-words-from-video-recordings/
- Remotion hardware acceleration: https://www.remotion.dev/docs/hardware-acceleration ; `<Video>`: https://www.remotion.dev/docs/media/video ; license: https://github.com/remotion-dev/remotion/blob/main/LICENSE.md ; pricing: https://www.remotion.pro/license
- Local skill used as current Remotion reference: ~/.agents/skills/remotion-best-practices/
- HyperFrames: https://github.com/heygen-com/hyperframes (README; skills/embedded-captions/SKILL.md)
- Google Fonts metadata: https://fonts.google.com/metadata/fonts
- Pexels API: https://www.pexels.com/api/documentation/ ; Pixabay API: https://pixabay.com/api/docs/ ; Unsplash API: https://unsplash.com/documentation ; Commons reuse: https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia
- fal.ai: https://fal.ai/models/fal-ai/veo3.1 ; https://fal.ai/models/fal-ai/kling-video/v3/pro/image-to-video ; https://fal.ai/models/bytedance/seedance-2.5/image-to-video ; https://fal.ai/models/fal-ai/nano-banana-pro ; https://fal.ai/models/fal-ai/birefnet/v2/video ; https://fal.ai/pricing
- Runway API pricing: https://docs.dev.runwayml.com/guides/pricing/
- Higgsfield API: https://docs.higgsfield.ai/
- Package versions: PyPI JSON API and `npm view`, queried 2026-09-27.
