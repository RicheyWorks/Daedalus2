# episode: the recording isle (Youtube Master Island + Wild Biomes)
- `shots.txt`: 11 shots in cut order. Folder names are the Level Sequences written by
  `engines/unreal/ytm-island/ytm_flythrough_ue.py` (`/Game/YTM/Seq/...`); Movie Render Queue writes one folder per sequence.
- `episode.json`: title/end/thumbnail text and the lowercase captions keyed by the second column of `shots.txt`.
- `METADATA.md`: draft YouTube title/description/tags. **Nothing is uploaded without Richey's ok**; first upload unlisted.
- Build: `bash tools/video/cut.sh tools/video/episodes/recording-isle out.mp4 <renders_root> [seed_song.mp3]`
  Shots without renders become labelled placeholder stills, so the cut can be checked before any editor time.
- Stills instead of renders (no Movie Render Queue needed): run the `tools/capture` job `jobs/ytm_island.json`, then
  `python tools/video/shots.py stills <capture_out>/manifest.json work/` and `bash tools/video/assemble.sh work out.mp4`.
