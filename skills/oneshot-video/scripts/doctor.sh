#!/usr/bin/env bash
# Check everything oneshot-video needs; print the fix for anything missing.
CR="$(cd "$(dirname "$0")/.." && pwd)"
ok=1
chk() { if eval "$2" >/dev/null 2>&1; then printf "  ok    %s\n" "$1"; else printf "  MISS  %s  ->  %s\n" "$1" "$3"; ok=0; fi; }
echo "oneshot-video doctor ($CR)"
chk "ffmpeg" "command -v ffmpeg" "brew install ffmpeg"
chk "whisper-cli (whisper.cpp)" "command -v whisper-cli" "brew install whisper-cpp"
chk "node 20+" "node -e 'process.exit(parseInt(process.versions.node)>=20?0:1)'" "brew install node"
chk "python venv" "test -x $CR/.venv/bin/python" "$CR/scripts/install.sh"
chk "python packages" "$CR/.venv/bin/python -c 'import onnx_asr, cv2, soundfile, scipy, numpy'" "$CR/scripts/install.sh"
chk "Whisper large-v3-turbo model" "test -s $CR/models/ggml-large-v3-turbo-q8_0.bin" "$CR/scripts/install.sh"
chk "Silero VAD (whisper.cpp)" "test -s $CR/models/ggml-silero-v5.1.2.bin" "$CR/scripts/install.sh"
chk "RNNoise voice model" "test -s $CR/models/rnnoise-sh.rnnn" "$CR/scripts/install.sh"
chk "YuNet face model" "test -s $CR/models/face_detection_yunet_2023mar.onnx" "$CR/scripts/install.sh"
if test -d "$HOME/Library/Application Support/com.pais.handy/models/parakeet-tdt-0.6b-v3-int8" || ls "$HOME/.cache/huggingface/hub" 2>/dev/null | grep -q parakeet-tdt-0.6b-v3; then
  echo "  ok    Parakeet TDT v3"
else
  echo "  note  Parakeet TDT v3: downloads once (~650 MB) on the first transcription"
fi
chk "Remotion (node_modules)" "test -d $CR/renderer/node_modules/remotion" "$CR/scripts/install.sh"
chk "matte tool (text behind speaker)" "test -x $CR/bin/matte" "$CR/scripts/install.sh"
chk "sound kit" "test -s $CR/assets/sfx/tick.wav" "$CR/.venv/bin/python $CR/scripts/sfx.py"
chk "pdftoppm (decks to PNG, optional)" "command -v pdftoppm" "brew install poppler"
free_gb=$(df -g "$HOME" | awk 'NR==2{print $4}')
if [ "${free_gb:-0}" -lt 5 ]; then echo "  MISS  disk: ${free_gb} GB free  ->  renders need 5 GB; free space first"; ok=0;
elif [ "${free_gb:-0}" -lt 10 ]; then echo "  warn  disk: ${free_gb} GB free (under 10 GB: render one format at a time)";
else echo "  ok    disk: ${free_gb} GB free"; fi
[ $ok = 1 ] && echo "ready" || { echo "fix the MISS lines above"; exit 1; }
