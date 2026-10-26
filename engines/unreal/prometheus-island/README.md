# Prometheus Island (engines/unreal/prometheus-island)
Builder: prometheus (Team Grok). Doc: docs/islands/PROMETHEUS_ISLAND.md.
Pipeline (all hidden/headless):
1. `python terrain_gs.py 15`: Gray-Scott terrain (heightmap.npy, island.json); `mkobj.py`-equivalent OBJ export lives in pi_place inputs.
2. `blender -b --factory-startup --python blender_items.py -- <start> <count>`: 500 items, run as 4x125 in parallel -> fbx/ + manifest_*.json.
3. `python audio_pi.py`: SW_PI_Stream.wav / SW_PI_Song.wav (dark, soft, low-passed).
4. Editor turn via ue_send.py: `pi_place.py` (import + place into /Game/Prometheus/Maps/PrometheusIsland at ARK_ORIGIN 2000000,2000000,0),
   then `prom_turn.py` (Wild Biomes + multipart livestock with Turing coats + scene-capture shots; saves own packages only).
Not committed here (binary, regenerable from the scripts): 500 FBX, terrain OBJ, wavs, heights.json, .umap/.uasset.
They live on BLACKBEARD in bot-team/art/prometheus_island and C:/Unreal/DaedalusRealm/Content/Prometheus.

## Terrain transform (r5 diagnosis, 2026-10-13)
- `SM_PrometheusIsland_Terrain.obj` is Z-up, meters: vertex (x,y,z) = (lx, ly, height), 128x128, footprint +-240 m, z -12..36.6 m.
  Peak (-20.8, 13.2, 36.6) = heights.json cell (i=67, j=58). Same frame as `hz()` in pi_place.py, so no flip is needed in principle.
- r2's auto-fit forced actor scale 100 and picked roll 180 + mirror Y (mean error ~25 m), and the r4 capture shows a mesa. Likely the import
  units were not what scale 100 assumed.
- `prom_fix_terrain_r5.py` derives the uniform scale from the mesh bounds (480 m footprint), then searches 72 rotation/mirror options with
  complex line traces against the heightmap. It keeps the result only if the mean error is under 3 m, otherwise it restores the old transform.
  It then snaps every PI_ item to the traced surface, keeping each item's designed offset, saves PrometheusIsland + /Game/Prometheus, and re-captures.
- Blender: `pi_blender_hero_v2.py` with `PIB_PARITY=1` places items from `data/islands/prometheus/ue_transforms.json`, the real UE export; `PIB3=1` gives the v3 framing.

## Hero render modes (pi_blender_hero_v2.py)
- `PIB_PARITY=1`: place items from the real UE export `ue_transforms.json`. Lanterns are lit.
- `PIB3=1`: horizon glow tamed, sun behind the camera, frames heart -> stream -> cistern. Tune with `PIB3_UP`, `PIB3_BACK`, `PIB3_SIDE`.
- `PIB3_FOCUS=water|pens`: close-ups of the water chain or the livestock pens.
- `PIB4=1`: warm area fills along the gorge plus a faint teal water glow.
- Final hero: `PIB_PARITY=1 PIB3=1 PIB3_UP=32 PIB4=1 blender -b -P pi_blender_hero_v2.py -- PI_hero_v4.png 256 100` (about 40 s on an RTX 4090).
- Do not render while another bot holds the editor turn (referee rule, 00:50).
