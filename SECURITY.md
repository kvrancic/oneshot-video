# Security

oneshot-video runs on your machine with your agent's permissions. It reads the footage you point it at and writes to `./oneshot-video/` in the folder you work in. Heavy tools and models are stored in `~/.oneshot-video`.

## What it runs and fetches

- **Install (`scripts/install.sh`):** Homebrew packages (ffmpeg, whisper-cpp, node, uv), Python packages from PyPI into a private venv, npm packages for Remotion, and model files from Hugging Face, GitHub (opencv_zoo, rnnoise-models) and ggml-org. Every URL is in the script.
- **While editing:** local tools only (ffmpeg, whisper.cpp, Parakeet, Remotion, Apple Vision). The optional network calls are:
  - Pexels, for stock footage, only if you ask for stock
  - Wikimedia Commons, for portraits of public figures
  - GitHub, only when you file a bug report, after you approve the draft
- **No telemetry.** Nothing else leaves the machine except what your agent itself sends to its model.

## Reporting a vulnerability

Email kvrancic11@gmail.com, or use GitHub's private vulnerability reporting ("Report a vulnerability" on the Security tab). Please don't open a public issue for a security problem. You'll get a reply within a week.
