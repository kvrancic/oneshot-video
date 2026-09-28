# Platforms (September 2026)

| platform | aspect | length that works | ceiling | notes |
|---|---|---|---|---|
| TikTok | 9:16 | 20 to 60 s; 60 s+ for Creator Rewards | 10 min | safe core about 900x1492; right column 120 to 180 px from y 1100 down |
| Instagram Reels | 9:16 (grid shows a centred 3:4) | 15 to 90 s | recommended to non-followers only up to 3 min | demotes other platforms' watermarks; keep face and title in the centre 3:4 |
| YouTube Shorts | 9:16 | 30 to 60 s; up to 3 min | 3 min | every replay counts as a view: loop endings pay; custom thumbnails for YPP creators |
| X | 16:9 or 1:1 in the feed; 9:16 works in the media tab | 45 to 90 s | 140 s free, much longer with Premium | a 16:9 frame shows at 0.56x the size of a 9:16 on a phone: captions +15 percent |
| LinkedIn | 1:1, 4:5 or 16:9 | 30 to 90 s | 10 min | captions matter more (sound off by default) |
| YouTube | 16:9 | segments 5 to 25 min | | chapters every 3 to 8 min |

## Safe zones on 1080x1920

Top 160 px, bottom 400 px, left and right 72 px and the right 140 px below y 1100. Everything important (face, captions, graphics) stays in x 72 to 1008, y 160 to 1520. The renderer's `SAFE` table encodes this.

## Export

- H.264 High, 30 fps constant, yuv420p, 8 Mbps for 9:16, 10 Mbps for 16:9, AAC 256 kbps 48 kHz stereo, `+faststart`.
- -14 LUFS, true peak -1 dBTP.
- One clean file per format, burned-in captions, no watermark. A sidecar `captions.srt` for platforms that accept one.
- Cover: a frame with the face and the hook legible, centred for the Reels 3:4 grid crop.

## Copy

`post.md` holds the title and caption per platform. Hooks and titles use the speaker's own strongest line; frame the moment, never invent it. No engagement bait ("wait for it", "you won't believe"), no polls, no hashtags beyond two or three plain ones.
