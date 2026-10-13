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
