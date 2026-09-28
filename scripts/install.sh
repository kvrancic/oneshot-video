#!/usr/bin/env bash
# One-time setup: Python venv, local models, Remotion, sound kit, skill symlink.
set -euo pipefail
CR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$CR"
command -v ffmpeg >/dev/null || brew install ffmpeg
command -v whisper-cli >/dev/null || brew install whisper-cpp
command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
[ -x .venv/bin/python ] || uv venv -q .venv --python 3.12
uv pip install -q --python .venv/bin/python onnx-asr onnxruntime huggingface_hub numpy scipy soundfile opencv-python-headless
mkdir -p models
dl() { [ -s "models/$1" ] || curl -L --fail -o "models/$1" "$2"; }
dl ggml-large-v3-turbo-q8_0.bin https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo-q8_0.bin
dl ggml-silero-v5.1.2.bin https://huggingface.co/ggml-org/whisper-vad/resolve/main/ggml-silero-v5.1.2.bin
dl face_detection_yunet_2023mar.onnx https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx
(cd renderer && npm install --no-audit --no-fund)
mkdir -p bin && swiftc -O scripts/matte.swift -o bin/matte   # person matte for text behind the speaker
.venv/bin/python scripts/sfx.py
mkdir -p "$HOME/.claude/skills"
[ -e "$HOME/.claude/skills/cutroom" ] || ln -s "$CR" "$HOME/.claude/skills/cutroom"
"$CR/scripts/doctor.sh"
