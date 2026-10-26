# Wild Biomes flythroughs: shot list (youtube-master, Team Grok)
Zone: Wild Biomes live in sublevel /Game/Pythagoras/Maps/Island_Pythagoras (pythagoras), island origin (-60000, 60000, 2500) cm, 120 m island, five 30 m patches.
The old "rings 4.5-16 km around PlayerStart" plan is obsolete.
Output: /Game/YTM/Seq/WB_Flythrough_<biome> (12 s each, 30 fps) + WB_Flythrough_Master (60 s cut). Touches only /Game/YTM.
| # | Biome | Move | Radius / height | Lens | Mood (oddsreaper DT_WildBiomeMoods) |
|---|---|---|---|---|---|
| 1 | YoungMeadow | wide 120 deg orbit, push-in | 60 m / 9 m | 24 mm | young_meadow, golden hour |
| 2 | BrambleScrub | low 90 deg dolly | 35 m / 4 m | 35 mm | bramble_scrub, overcast |
| 3 | PineStand | high 150 deg crane orbit | 50 m / 25 m | 28 mm | pine_stand, fog |
| 4 | OldGrowthOak | under-canopy 100 deg | 40 m / 18 m | 21 mm | old_growth_oak, dappled |
| 5 | WillowRiverbank | water-level 110 deg | 45 m / 6 m | 35 mm | willow_riverbank, dusk |
Pets: AMF Mob_CaneCorso + Mob_* should be in frame (tag AMF_Pets). Audio bed: prometheus ambient / a seed song.
Render: Movie Render Queue 1920x1080 30 fps -> bot-team\art\NOTES\youtube-master\renders\ (for YouTube: richeyworks).
Editor-turn order (Grok shared turn): pythagoras flora -> art-master-flex pets -> oddsreaper sky -> youtube-master cams (~3 min) + render.

## Marker audit (Oct 18, from repo data on main 550e88fd)
Created by `engines/unreal/pcg-ecology/pyth_island_ue.py` (nothing in the repo uses `WB_Label_*` / `PYTH_WB_*` any more):
| Marker | What | Position (cm) |
|---|---|---|
| `PYT_Label_<Biome>` | TextRenderActor, tag `PYT_Island` | ORIGIN + patch centre + (0, 0, 2200) |
| `PYT_Habitat_<Biome>` | hidden 30 m cube, tags `DAEDALUS_Habitat`, `Habitat_<Biome>` | ORIGIN + patch centre + (0, 0, 300) |
| patch centres (`CENT`) | YoungMeadow (-3200,-3200), BrambleScrub (3200,-3200), PineStand (3200,3200), OldGrowthOak (-3200,3200), WillowRiverbank (0,0) | relative to ORIGIN |
`ytm_flythrough_ue.py` reads `PYT_Label_`, then `PYT_Habitat_`, then the legacy `WB_` names. If a biome has no loaded marker it now
aims at the `PYT_CENT` layout position above (ORIGIN + centre), not a ring. Shots on this island use tighter orbits (`PYT_ORBIT`, 18-24 m radius) because the patches are only 30 m wide. It only checks whether the sublevel is loaded; it never adds or saves it (read-only).
Island Youtube Master shots (YTM_Spring/Shrine/Garden/Farm/Dock + overview) are offsets from `YTM_Spawn`; sublevel `/Game/YTM/Maps/YTM_Island`, origin (0, -2600000, 0).
Stills for proof or the thumbnail: `tools/capture` job `jobs/ytm_island.json`. Editor use: ask codex-play-guard by NEED (sole Unreal writer); this prep touches no editor.
