#!/usr/bin/env bash
# assemble.sh <shots_dir> <out.mp4> [song.mp3]
# Title card -> each shot in <shots_dir>/shots.txt (frames at 30 fps, or one still held N s; 0.5 s fades; optional
# lower-third caption overlay) -> end card. Audio: the song looped to length with fades + loudnorm -16 LUFS, or silence.
# Cards come from $CARDS (default <shots_dir>/../cards), made by cards.py. Output: 1080p30 H.264/AAC mp4.
set -euo pipefail
SHOTS="$(cd "$1" && pwd)"; OUT="$2"; SONG="${3:-${SONG:-}}"
CARDS="${CARDS:-$SHOTS/../cards}"; FPS=30; FADE=0.5; CARD_S="${CARD_S:-3}"
[ -f "$CARDS/title.png" ] || { echo "no $CARDS/title.png: run cards.py <episode.json> --out $CARDS first" >&2; exit 2; }
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
py() { python3 -c "$1"; }
enc=(-c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p -r $FPS)
card() { ffmpeg -nostdin -v error -y -loop 1 -t "$CARD_S" -i "$1" -vf "scale=1920:1080,fade=in:0:15,fade=out:st=$(py "print($CARD_S-0.5)"):d=0.5" "${enc[@]}" "$2"; }
card "$CARDS/title.png" "$TMP/00_title.mp4"; echo "file '$TMP/00_title.mp4'" > "$TMP/list.txt"
i=0
while read -r folder cap hold _; do
  [ -z "${folder:-}" ] && continue; case "$folder" in \#*) continue;; esac
  i=$((i+1)); cap="${cap:--}"; seg="$TMP/$(printf %02d $i)_$folder.mp4"
  first=$(ls "$SHOTS/$folder" | grep -Ei '\.(jpe?g|png)$' | sort | head -1); ext="${first##*.}"
  n=$(ls "$SHOTS/$folder" | grep -Eic '\.(jpe?g|png)$')
  if [ "$n" -eq 1 ]; then
    dur="${hold:-4}"; input=(-loop 1 -t "$dur" -i "$SHOTS/$folder/$first")
  else
    dur=$(py "print($n/$FPS)")
    read -r pattern start <<<"$(py "import re;f='$first';m=re.search(r'(\d+)\.\w+$',f);print(f[:m.start(1)]+'%0'+str(len(m.group(1)))+'d.$ext', int(m.group(1)))")"
    input=(-framerate $FPS -start_number "$start" -i "$SHOTS/$folder/$pattern")
  fi
  vf="scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fade=in:0:$((FPS/2)),fade=out:st=$(py "print(max(0,$dur-$FADE))"):d=$FADE"
  if [ "$cap" != "-" ] && [ -f "$CARDS/cap_$cap.png" ]; then
    ffmpeg -nostdin -v error -y "${input[@]}" -loop 1 -i "$CARDS/cap_$cap.png" \
      -filter_complex "[0:v]$vf[v];[1:v]format=rgba,fade=in:st=0.6:d=0.6:alpha=1,fade=out:st=$(py "print(max(0,$dur-1.2))"):d=0.6:alpha=1[c];[v][c]overlay=0:0:shortest=1" \
      -t "$dur" "${enc[@]}" "$seg"
  else
    ffmpeg -nostdin -v error -y "${input[@]}" -vf "$vf" -t "$dur" "${enc[@]}" "$seg"
  fi
  echo "file '$seg'" >> "$TMP/list.txt"; echo "shot $i $folder ${dur}s cap=$cap"
done < "$SHOTS/shots.txt"
card "$CARDS/end.png" "$TMP/99_end.mp4"; echo "file '$TMP/99_end.mp4'" >> "$TMP/list.txt"
ffmpeg -nostdin -v error -y -f concat -safe 0 -i "$TMP/list.txt" -c copy "$TMP/video.mp4"
T=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$TMP/video.mp4")
if [ -n "$SONG" ] && [ -f "$SONG" ]; then
  ain=(-stream_loop -1 -i "$SONG"); af="[1:a]atrim=0:$T,afade=t=in:d=1.5,afade=t=out:st=$(py "print(max(0,$T-2.5))"):d=2.5,loudnorm=I=-16:TP=-1.5[a]"
else
  ain=(-f lavfi -i "anullsrc=r=48000:cl=stereo"); af="[1:a]atrim=0:$T[a]"; echo "no song: silent audio track"
fi
ffmpeg -nostdin -v error -y -i "$TMP/video.mp4" "${ain[@]}" -filter_complex "$af" \
  -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k -movflags +faststart -shortest "$OUT"
echo "OUT $OUT $(ffprobe -v error -show_entries format=duration:stream=width,height,r_frame_rate -of compact=p=0 "$OUT" | tr '\n' ' ')"
