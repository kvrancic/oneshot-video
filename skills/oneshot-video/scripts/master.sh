#!/usr/bin/env bash
# Render a film project and master it for playback: -14 LUFS integrated, -2 dBTP, AAC 320k.
#
#   master.sh DIR [--comp Film] [--out DIR/out/<name>.mp4] [--lufs -14] [--tp -2] [--scale 0.5] [--frames 0-149]
#
# --scale 0.5 renders a fast half-resolution draft (about 1.5x realtime) for review.
# Remotion's AAC carries 2048 priming samples it does not flag, so the decoded mix plays 42.7 ms
# late against the picture. They are trimmed here; hits stay on their frames.
set -euo pipefail
DIR="$(cd "${1:?usage: master.sh DIR [options]}" && pwd)"; shift
comp=Film lufs=-14 tp=-2 out="" extra=()
while [ $# -gt 0 ]; do
  case "$1" in
    --comp) comp="$2"; shift 2 ;;
    --out) out="$2"; shift 2 ;;
    --lufs) lufs="$2"; shift 2 ;;
    --tp) tp="$2"; shift 2 ;;
    --scale) extra+=("--scale=$2"); shift 2 ;;
    --frames) extra+=("--frames=$2"); shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
name="$(basename "$DIR")"
[ -n "$out" ] || out="$DIR/out/$name.mp4"
raw="$DIR/out/raw.mp4"
mkdir -p "$DIR/out"
cd "$DIR"
npx remotion render src/index.ts "$comp" "$raw" --concurrency=8 --crf=14 --audio-bitrate=320k --log=error ${extra[@]+"${extra[@]}"}

sync="atrim=start_sample=2048,asetpts=N/SR/TB"
m=$(ffmpeg -nostats -i "$raw" -vn -af "$sync,loudnorm=I=$lufs:TP=$tp:LRA=9:print_format=json" -f null - 2>&1 | sed -n '/^{/,/^}/p')
get() { echo "$m" | grep "\"$1\"" | sed 's/.*: "\(.*\)".*/\1/'; }
if [ "$(get input_i)" = "-inf" ] || [ -z "$(get input_i)" ]; then
  ffmpeg -v error -y -i "$raw" -c copy -movflags +faststart "$out"   # silent film: nothing to master
else
  lim=$(python3 -c "print(round(10 ** (($tp - 0.2) / 20), 4))")
  ffmpeg -v error -y -i "$raw" -c:v copy \
    -af "$sync,loudnorm=I=$lufs:TP=$tp:LRA=9:measured_I=$(get input_i):measured_TP=$(get input_tp):measured_LRA=$(get input_lra):measured_thresh=$(get input_thresh):offset=$(get target_offset):linear=true,alimiter=limit=$lim:attack=1:release=50:level=false:latency=1,apad" \
    -shortest -ar 48000 -c:a aac -b:a 320k -movflags +faststart "$out"
fi
rm -f "$raw"
ffmpeg -nostats -i "$out" -vn -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I|Peak):" | tr -s ' ' | sed 's/^/  /'
echo "$out"
