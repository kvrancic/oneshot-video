#!/usr/bin/env bash
# One-time setup: Python venv, local models, Remotion, matte tool, skill links.
#
# The heavy parts (~2 GB) live in $ONESHOT_HOME (default ~/.oneshot-video) and are linked into
# the skill folder, so a plugin update or a fresh clone re-links in seconds instead of downloading
# again. Safe to re-run: it only does what is missing.
set -euo pipefail
CR="$(cd "$(dirname "$0")/.." && pwd)"
DATA="${ONESHOT_HOME:-$HOME/.oneshot-video}"
mkdir -p "$DATA/models" "$DATA/renderer" "$DATA/bin"
cd "$CR"

command -v brew >/dev/null || { echo "Homebrew is required: https://brew.sh"; exit 1; }
command -v ffmpeg >/dev/null || brew install ffmpeg
command -v whisper-cli >/dev/null || brew install whisper-cpp
command -v node >/dev/null || brew install node
command -v uv >/dev/null || brew install uv

# Python
[ -x "$DATA/venv/bin/python" ] || uv venv -q "$DATA/venv" --python 3.12
uv pip install -q --python "$DATA/venv/bin/python" onnx-asr onnxruntime huggingface_hub numpy scipy soundfile opencv-python-headless
ln -sfn "$DATA/venv" .venv

# Models (~1 GB)
dl() { [ -s "$DATA/models/$1" ] || curl -L --fail -o "$DATA/models/$1" "$2"; ln -sf "$DATA/models/$1" "models/$1"; }
dl ggml-large-v3-turbo-q8_0.bin https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo-q8_0.bin
dl ggml-silero-v5.1.2.bin https://huggingface.co/ggml-org/whisper-vad/resolve/main/ggml-silero-v5.1.2.bin
dl face_detection_yunet_2023mar.onnx https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx
dl rnnoise-sh.rnnn https://raw.githubusercontent.com/GregorR/rnnoise-models/master/somnolent-hogwash-2018-09-01/sh.rnnn   # voice cleaning (rnnoise-nu, recording model)

# Remotion: installed where it survives updates, reinstalled only when the lockfile changed
if ! cmp -s renderer/package-lock.json "$DATA/renderer/package-lock.json" || [ ! -d "$DATA/renderer/node_modules/remotion" ]; then
  cp renderer/package.json renderer/package-lock.json "$DATA/renderer/"
  (cd "$DATA/renderer" && npm ci --no-audit --no-fund)
fi
ln -sfn "$DATA/renderer/node_modules" renderer/node_modules

# Person matte (Apple Vision) for text behind the speaker
[ "$DATA/bin/matte" -nt scripts/matte.swift ] || swiftc -O scripts/matte.swift -o "$DATA/bin/matte"
ln -sfn "$DATA/bin" bin

# Sound kit (synthesized, shipped in the repo; rebuilt only if missing)
[ -s assets/sfx/tick.wav ] || .venv/bin/python scripts/sfx.py

# Make the skill visible to agents when installed from a clone (plugins and `npx skills add` do this themselves)
case "$CR" in
  */plugins/cache/*|*/.agents/skills/*|*/.claude/skills/*) ;;
  *) for dir in "$HOME/.claude/skills" "$HOME/.agents/skills"; do
       mkdir -p "$dir"
       if [ -L "$dir/oneshot-video" ] || [ ! -e "$dir/oneshot-video" ]; then ln -sfn "$CR" "$dir/oneshot-video"; echo "linked $dir/oneshot-video"; fi
     done ;;
esac

"$CR/scripts/doctor.sh"
