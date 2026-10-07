#!/usr/bin/env bash
# Start a from-scratch film project: the template, the kit, fonts and the sound kit, no install.
#
#   film.sh DIR        -> DIR/src (Main.tsx, timing.ts, kit -> the skill's kit), DIR/public/{fonts,sfx,footage,audio}
#
# Then: npx remotion studio (from DIR) to preview, scripts/master.sh DIR to render and master.
set -euo pipefail
CR="$(cd "$(dirname "$0")/.." && pwd)"
DIR="${1:?usage: film.sh DIR}"
[ -e "$DIR/src/Main.tsx" ] && { echo "$DIR already has a film"; exit 1; }
mkdir -p "$DIR"
cp -R "$CR/templates/film/." "$DIR/"
ln -sfn "$CR/renderer/src/kit" "$DIR/src/kit"
ln -sfn "$CR/renderer/node_modules" "$DIR/node_modules"
mkdir -p "$DIR/public/fonts" "$DIR/public/sfx" "$DIR/public/footage" "$DIR/public/audio" "$DIR/out"
cp "$CR"/renderer/public/fonts/* "$DIR/public/fonts/"
cp "$CR"/assets/sfx/*.wav "$DIR/public/sfx/"
echo "film project: $DIR"
echo "  preview:  (cd $DIR && npx remotion studio)"
echo "  render:   $CR/scripts/master.sh $DIR"
