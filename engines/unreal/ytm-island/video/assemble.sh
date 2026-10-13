#!/usr/bin/env bash
# assemble 'the recording isle': title card -> shots (frames + lowercase caption) -> end card, seed-song audio, 1080p30 mp4.
# usage: ./assemble.sh <shots_dir> <out.mp4> [song.mp3]
#   shots_dir/shots.txt: one line per shot, in order: "<folder> <caption_key>"  (caption_key -> cards/cap_<key>.png, or "-" for none)
#   each <folder> holds frames 0000.jpg/.png ... at 30 fps (Movie Render Queue output: {sequence_name}/{frame_number}.jpg)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; SHOTS="$1"; OUT="$2"
SONG="${3:-/workspace/rd-web/public/media/seedsongs/american-old-time.mp3}"
FPS=30; FADE=0.5; CARD_S=3
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
[ -f "$HERE/cards/title.png" ] || python3 "$HERE/cards.py" >/dev/null
enc=(-c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p -r $FPS)
card() { ffmpeg -nostdin -v error -y -loop 1 -t $CARD_S -i "$1" -vf "scale=1920:1080,fade=in:0:15,fade=out:st=$((CARD_S-1)).5:d=0.5" "${enc[@]}" "$2"; }
card "$HERE/cards/title.png" "$TMP/00_title.mp4"; echo "file '$TMP/00_title.mp4'" > "$TMP/list.txt"
i=0
while read -r folder cap; do
  [ -z "${folder:-}" ] && continue; i=$((i+1))
  first=$(ls "$SHOTS/$folder" | grep -Ei '\.(jpe?g|png)$' | sort | head -1); ext="${first##*.}"
  n=$(ls "$SHOTS/$folder" | grep -Eic '\.(jpe?g|png)$'); dur=$(python3 -c "print($n/$FPS)")
  pat=$(python3 -c "import re,sys;f='$first';m=re.search(r'(\d+)\.\w+$',f);print(f[:m.start(1)]+'%0'+str(len(m.group(1)))+'d.'+'$ext', int(m.group(1)))")
  read -r pattern start <<<"$pat"
  vf="scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fade=in:0:$((FPS/2)),fade=out:st=$(python3 -c "print(max(0,$dur-$FADE))"):d=$FADE"
  if [ "$cap" != "-" ] && [ -f "$HERE/cards/cap_$cap.png" ]; then
    ffmpeg -nostdin -v error -y -framerate $FPS -start_number "$start" -i "$SHOTS/$folder/$pattern" -loop 1 -i "$HERE/cards/cap_$cap.png" \
      -filter_complex "[0:v]$vf[v];[1:v]format=rgba,fade=in:st=0.6:d=0.6:alpha=1,fade=out:st=$(python3 -c "print(max(0,$dur-1.2))"):d=0.6:alpha=1[c];[v][c]overlay=0:0:shortest=1" \
      -t "$dur" "${enc[@]}" "$TMP/$(printf %02d $i)_$folder.mp4"
  else
    ffmpeg -nostdin -v error -y -framerate $FPS -start_number "$start" -i "$SHOTS/$folder/$pattern" -vf "$vf" "${enc[@]}" "$TMP/$(printf %02d $i)_$folder.mp4"
  fi
  echo "file '$TMP/$(printf %02d $i)_$folder.mp4'" >> "$TMP/list.txt"; echo "shot $i $folder ${dur}s cap=$cap"
done < "$SHOTS/shots.txt"
card "$HERE/cards/end.png" "$TMP/99_end.mp4"; echo "file '$TMP/99_end.mp4'" >> "$TMP/list.txt"
ffmpeg -nostdin -v error -y -f concat -safe 0 -i "$TMP/list.txt" -c copy "$TMP/video.mp4"
T=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$TMP/video.mp4")
# seed song looped to the cut, 1.5 s fade in, 2.5 s fade out
ffmpeg -nostdin -v error -y -i "$TMP/video.mp4" -stream_loop -1 -i "$SONG" \
  -filter_complex "[1:a]atrim=0:$T,afade=t=in:d=1.5,afade=t=out:st=$(python3 -c "print(max(0,$T-2.5))"):d=2.5,loudnorm=I=-16:TP=-1.5[a]" \
  -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k -movflags +faststart -shortest "$OUT"
echo "OUT $OUT $(ffprobe -v error -show_entries format=duration:stream=width,height,r_frame_rate -of compact=p=0 "$OUT" | tr '\n' ' ')"
