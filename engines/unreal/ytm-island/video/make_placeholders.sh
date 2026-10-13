#!/usr/bin/env bash
# usage: make_placeholders.sh [dir] [sec] [shotlist.txt]
# placeholder shots: pan across the channel banner's Turing pattern, 12 s per shot at 30 fps, MRQ-style jpg frames.
set -euo pipefail
D="${1:-/workspace/youtube/recording-isle/test_shots}"; SEC="${2:-12}"; B=/workspace/youtube/branding/banner_2560x1440.png
mkdir -p "$D"; : > "$D/shots.txt"
i=0
LIST="${3:-}"
if [ -n "$LIST" ]; then mapfile -t SH < "$LIST"; else SH=("WB_Flythrough_YTMIsland island" "WB_Flythrough_YoungMeadow youngmeadow" "WB_Flythrough_PineStand pinestand" "WB_Flythrough_OldGrowthOak oldgrowthoak" "WB_Flythrough_WillowRiverbank willowriverbank" "YTM_Spring spring"); fi
for s in "${SH[@]}"; do
  read -r f c <<<"$s"; mkdir -p "$D/$f"; rm -f "$D/$f"/*.jpg
  z=$(python3 -c "print(1.15+0.1*$i)")
  ffmpeg -nostdin -v error -y -loop 1 -framerate 30 -t "$SEC" -i "$B" -vf "scale=iw*$z:-1,crop=1920:1080:x='(iw-1920)*t/$SEC':y='(ih-1080)*(0.5+0.4*sin(t/2+$i))',hue=h=$((i*40))" \
    -q:v 3 -start_number 0 "$D/$f/%04d.jpg"
  echo "$f $c" >> "$D/shots.txt"; i=$((i+1))
done
echo "placeholders in $D"; cat "$D/shots.txt"
