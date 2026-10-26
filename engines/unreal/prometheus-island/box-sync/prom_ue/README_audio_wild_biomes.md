# Wild Biomes audio + coat herds (Prometheus, Team Grok)
- Beds (art/audio/biomes): SW_Biome_{meadow,bramble,pine,oak,willow,cavespace}.wav, 64 s seamless loops, ~-21 LUFS (willow -24.6), low-passed <7 kHz. QA: checks.json. Credits: art/audio/LICENSES_biomes.md (Gravity Sound CC BY 4.0 credit required).
- Calls (art/audio/biomes/calls): SW_Call_<coat>.wav, one per coat genome, G2-G3, LP 2.5 kHz, -24 LUFS, 12 s loop with silence.
- Coats (art/coats8): 8 regimes + 3 bred children, rd-coat 512 px.
- Scripts (art/prometheus_ue): wild_biomes_place.py (beds + herds + calls + cave night bed + jukebox occlusion; anchors on WB_Label_<biome>), shot2.py (hidden SceneCapture PNGs), verify.py (checks earlier DA_* placements).
- Run with: python ue_send.py <script> 300 (async). Actors: DA_WB_* (tags WB_<biome>, DA_Coat, DA_Ambient, DA_CreatureCall, TOD_night).
- Not done: reverb AudioVolumes (brush volumes cannot be built from editor Python reliably; owner can add Audio Volumes over WB_<biome> areas).
