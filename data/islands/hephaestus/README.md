# Hephaestus Island data (disk-saver index)

Forge-and-hot-spring island. Data here, scripts in `tools/islands/hephaestus/`. Full design: `ISLAND.md`.

| File | What it holds |
|------|---------------|
| ISLAND.md | Island design doc, turn log, owed work |
| README.md | This index |
| layout.json | Placements (zones, landmarks, props) for heph_island_ue |
| preflight.json | heph_preflight output: assets, needs_import, lod1_ready, blocking |
| mechanics.json | disksaver-mechanics-v1 block: water, livestock, herbs, teas, forge_temper, balance |
| check_mechanics.py | Validator for mechanics.json (`python data/islands/hephaestus/check_mechanics.py`) |
| herbs.json | 36 herb species + temper values |
| livestock.json | Emberhen / Ashgoat / Forgeox / Lavaboar / Cinderwool / VentBees |
| water.json | Quench Network sources and treatment |
| materials_mpc.json | Forge glow material parameter collection |
| nft.json | NFT card, points at the Blender forge-overlook hero |

| Script (tools/islands/hephaestus/) | Role |
|------|------|
| heph_turn.py | 10-min editor turn runner (handoff/grant gated, bridge preflight, stop + save) |
| heph_island_ue.py | In-editor placement + sky gate + hero SceneCapture (granted turn only) |
| heph_preflight.py | Writes preflight.json (needs_import, lod1_ready) |
| heph_hero_glb.py / heph_blender_hero.py | Procedural hero glbs / off-editor Blender hero |
| heph_dual_cookbook.py, heph_forge_glow.py, heph_livestock.py, heph_ranch_budget.py | Data builders |
| test_heph_*.py | Headless tests (no Unreal): force_lod1, landmarks, sky_gate, handoff, give_up, capture_ladder, nft_card, temp_lights, hero_frame |

Next editor turn: heph_turn sets `HEPH_FORCE_LOD1=1` automatically when preflight lists lod1_ready and needs_import is empty (`HEPH_FORCE_LOD1=0` disables), so the 7 landmarks swap to LOD1. The forge-overlook hero is shot lit: the sky gate runs oddsreaper `restore_world_sky` once if DaedalusWorld reads storm-dark, then island-only `HEPH_TEMP_*` sun/fill/PPV lights (disk-saver v5 tuning: fill 5e5, EV100 9; `atmosphere_sun_light=False`; destroyed before any save; `HEPH_TEMP_LIGHTS=0` disables).

Hero framing: heph_island_ue fits the hero cam to the caldera_forge core (~78 m instead of 229 m, same view direction; `HEPH_HERO_FIT=0` keeps the fixed pose) and puts `MI_BasaltGround` on the blockout disc so the lit capture stops washing out.
