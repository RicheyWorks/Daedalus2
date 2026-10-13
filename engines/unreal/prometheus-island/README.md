# Prometheus Island pipeline (prometheus, Team Grok)
1. `python terrain_gs.py <tokenId>`: Gray-Scott heightmap (`heightmap.npy`, `island.json`); then `python mkobj.py` (terrain OBJ) and dump `heights.json`.
2. `blender -b --factory-startup -noaudio --python blender_items.py -- <start> <count>`: 500 items as FBX plus `manifest_*.json` (run 4x125 in parallel, hidden).
3. `python audio_pi.py`: SW_PI_Stream / SW_PI_Song (dark, low-passed).
4. In a granted editor turn: `ue_send.py pi_place.py` (import + place into /Game/Prometheus/Maps/PrometheusIsland at ARK_ORIGIN 2000000,2000000,0), then `ue_send.py prom_turn.py` (Wild Biomes + livestock + scene-capture shots; saves own packages only).
Generated binaries (FBX, WAV, npy, umap) are not committed: they are fully reproducible from these sources and the seed (15).
