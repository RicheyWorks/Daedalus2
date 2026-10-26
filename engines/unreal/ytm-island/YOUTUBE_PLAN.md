# YouTube plan: first video (youtube-master, for the richeyworks channel)

**Status: plan only.** Nothing is uploaded or scheduled. Richey approves the final cut, title and description before anything goes public. **No launch dates anywhere public.**

## The video: "the recording isle"
- **Length:** about 75 s. That fits a regular upload, and a 60 s vertical cut can follow.
- **Look:** richeyworks. Black #0b0b0b, white text, IBM Plex Mono, all lowercase, short plain lines. The sea-dragon stamp sits small in a corner.

| time | shot (UE sequence) | on-screen text |
|---|---|---|
| 0-3 s | black, dragon stamp fades in | `richeyworks` |
| 3-15 s | `WB_Flythrough_YTMIsland`: wide orbit and push-in on Youtube Master Island | `one planet. one rock. ten thousand pieces.` |
| 15-27 s | `WB_Flythrough_YoungMeadow` | `young meadow` |
| 27-39 s | `WB_Flythrough_PineStand` | `pine stand` |
| 39-51 s | `WB_Flythrough_OldGrowthOak` | `old-growth oak` |
| 51-63 s | `WB_Flythrough_WillowRiverbank` | `willow riverbank` |
| 63-72 s | back to the island spring (clean water) | `drink before you build.` |
| 72-75 s | black | `daedalus` / `richeyworks` |

BrambleScrub is held back for the vertical short.

## Audio: seed songs
- **Where the files are:** the seed songs are on the **Grok box** at `/workspace/rd-web/public/media/seedsongs/`, not on BLACKBEARD. There are 48 MP3 clips of about 45 s each, and each has a matching .webp label.
- **Pick:** one folk or acoustic clip for the island. `american-old-time.mp3` is the first choice, with `alpine.mp3` as a fallback. Loop or crossfade it to about 75 s with ffmpeg (`afade` in/out 1.5 s).
- **Credit line:** `music: reaction / diffusion / song (seed song)`. No other track and no voice-over, so we can be sure we have the rights to all of it.

## Pipeline (one light editor turn, then everything else off the editor)
1. **Editor turn:**
   - `ytm_flythrough_ue.py` builds the sequences, using real biome centres when pythagoras's labels or habitats are loaded.
   - `ytm_render_preset_ue.py YTM_RENDER=WB_Flythrough_Master` renders JPG frames at 1080p30 with the light preset (1 sample, editor-only executor).
   - **RAM:** skip the render if free RAM is under 2 GB.
2. **Copy:** frames from `bot-team\art\NOTES\youtube-master\renders\` go to the Grok box with CopyToBox.
3. **On the box:**
   - Make the mp4 with `ffmpeg -framerate 30 -i %04d.jpg -c:v libx264 -crf 18 -pix_fmt yuv420p`.
   - Burn in the titles with `drawtext` (IBM Plex Mono, from `/workspace/rd-web/public/fonts`), then mix in the seed song.
4. **Preview:** send Richey the preview mp4 and a thumbnail: a black frame with the dragon stamp and the lowercase line `the recording isle`.
5. **Upload:** only after Richey OKs it, in the browser, to youtube.com/@richeyworks.
   - **Visibility:** Unlisted first, then Public when Richey says.
   - **Title:** `the recording isle | daedalus`
   - **Description:** `a fragment of one shattered planet. it kept its spring. / built by bots, for richeyworks.` No dates and no legal name.

## Blockers
- **Wild Biomes placement:** the biome sequences need pythagoras's flora and labels loaded in the world. In the 21:02 turn I found no `WB_Label_*` actors, and prometheus reported at 16:46 that `WildBiomes_Pythagoras.umap` is not on disk.
- **Render:** it needs a calm-RAM editor turn.
