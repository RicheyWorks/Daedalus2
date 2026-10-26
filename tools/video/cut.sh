#!/usr/bin/env bash
# cut.sh <episode_dir> <out.mp4> [real_frames_root] [song.mp3]
# One command for an episode: cards (thumbnail from the middle real frame if any) -> shots.py prepare -> assemble.sh.
# <episode_dir> holds episode.json and shots.txt. Real renders: <real_frames_root>/<SequenceName>/*.jpg (MRQ layout).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; EP="$(cd "$1" && pwd)"; OUT="$2"; REAL="${3:-}"; SONG="${4:-}"
WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT
python3 "$HERE/shots.py" prepare "$EP/shots.txt" "$WORK/shots" ${REAL:+--real "$REAL"}
bg=""
if [ -n "$REAL" ]; then
  while read -r f _; do [ -z "${f:-}" ] && continue
    m=$(ls "$REAL/$f" 2>/dev/null | grep -Ei '\.(jpe?g|png)$' | sort | awk '{a[NR]=$0} END{if(NR) print a[int(NR/2)+1]}')
    [ -n "$m" ] && { bg="$REAL/$f/$m"; break; }
  done < "$EP/shots.txt"
fi
python3 "$HERE/cards.py" "$EP/episode.json" --out "$WORK/cards" ${bg:+--thumb-bg "$bg"}
CARDS="$WORK/cards" bash "$HERE/assemble.sh" "$WORK/shots" "$OUT" "$SONG"
cp "$WORK/cards/thumb.png" "${OUT%.*}_thumb.png" && echo "THUMB ${OUT%.*}_thumb.png${bg:+ (from $bg)}"
