# the recording isle: video pipeline (on the Grok box)
- `cards.py`: makes the title and end cards and 6 lowercase lower-third captions, using IBM Plex Mono and the dragon stamp from `/workspace/youtube/branding`. Output goes to `cards/`.
- `assemble.sh <shots_dir> <out.mp4> [song.mp3]`: builds the cut. A 3 s title card comes first, then each shot from `shots.txt` (frames at 30 fps, 0.5 s fades, caption overlay), then a 3 s end card. The seed song is looped to length with fades and loudnorm at -16 LUFS. Output is a 1080p30 H.264/AAC mp4.
- `make_placeholders.sh`: makes test shots that pan across the banner's Turing pattern, in the same layout as MRQ output (`<SequenceName>/0000.jpg`).
- **Tested:** `test_recording_isle.mp4` is 78 s at 1920x1080, 30 fps, with H.264 video and AAC audio.
- **Real renders:** copy `bot-team\art\NOTES\youtube-master\renders\<Seq>\` from BLACKBEARD into `shots/`, write `shots.txt`, then run `./assemble.sh shots recording_isle_v1.mp4`.
