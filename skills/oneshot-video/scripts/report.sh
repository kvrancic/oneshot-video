#!/usr/bin/env bash
# Draft a GitHub issue for oneshot-video: what failed, the doctor output and versions, with
# home paths and the user name scrubbed. Prints the draft; files it only with --submit.
#
#   report.sh --title "render.py: Chrome timed out" --step "render 9x16" [--log FILE] [--note "..."] [--submit]
#
# --log takes the last 80 lines of a log or error output. Without gh the draft is printed with
# a link to open the issue in the browser.
set -uo pipefail
CR="$(cd "$(dirname "$0")/.." && pwd)"
REPO="${ONESHOT_REPO:-kvrancic/oneshot-video}"
title="" step="" log="" note="" submit=0
while [ $# -gt 0 ]; do
  case "$1" in
    --title) title="$2"; shift 2 ;;
    --step) step="$2"; shift 2 ;;
    --log) log="$2"; shift 2 ;;
    --note) note="$2"; shift 2 ;;
    --submit) submit=1; shift ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
[ -n "$title" ] || { echo "--title is required" >&2; exit 2; }

scrub() { sed -E -e "s#$HOME#~#g" -e "s#$(whoami)#<user>#g" -e "s#$(hostname -s)#<host>#g" \
              -e 's#[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}#<email>#g' \
              -e 's#(sk-|key=|token=|Authorization: )[^ "]*#\1<redacted>#g'; }
ver() { "$@" 2>/dev/null | head -1; }

body="$(mktemp -t oneshot-report)"
{
  echo "**What failed:** ${step:-unspecified}"
  [ -n "$note" ] && printf '\n%s\n' "$note"
  if [ -n "$log" ] && [ -f "$log" ]; then
    printf '\n<details><summary>Log (last 80 lines)</summary>\n\n```\n'; tail -80 "$log"; printf '```\n</details>\n'
  fi
  printf '\n**Environment**\n\n```\n'
  echo "oneshot-video $(git -C "$CR" describe --tags --always --dirty 2>/dev/null || echo unknown)"
  echo "macOS $(sw_vers -productVersion 2>/dev/null) $(uname -m), $(sysctl -n machdep.cpu.brand_string 2>/dev/null), $(( $(sysctl -n hw.memsize 2>/dev/null || echo 0) / 1073741824 )) GB"
  echo "ffmpeg: $(ver ffmpeg -version | awk '{print $3}')"
  echo "node: $(ver node --version)"
  echo "python: $(ver "$CR/.venv/bin/python" --version)"
  echo "remotion: $(node -p "require('$CR/renderer/node_modules/remotion/package.json').version" 2>/dev/null)"
  printf '```\n\n<details><summary>doctor.sh</summary>\n\n```\n'
  "$CR/scripts/doctor.sh" 2>&1
  printf '```\n</details>\n'
} | scrub > "$body"

echo "----- draft issue for $REPO -----"
echo "Title: $title"
echo
cat "$body"
echo "---------------------------------"
if [ $submit = 1 ] && command -v gh >/dev/null && gh auth status >/dev/null 2>&1; then
  gh issue create --repo "$REPO" --title "$title" --body-file "$body" --label "from-report"  2>/dev/null \
    || gh issue create --repo "$REPO" --title "$title" --body-file "$body"
else
  enc() { python3 -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.stdin.read()))'; }
  url="https://github.com/$REPO/issues/new?title=$(printf %s "$title" | enc)&body=$(head -c 6000 "$body" | enc)"
  [ $submit = 1 ] && echo "gh is not signed in; open this link to file it:" || echo "Not filed. Re-run with --submit to file it, or open:"
  echo "$url"
fi
rm -f "$body"
