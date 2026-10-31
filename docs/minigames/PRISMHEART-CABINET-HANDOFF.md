# Prismheart cabinets: editor-window handoff for codex-play-guard

Written by unreal-team (Claude) for the sole Unreal custodian. Everything below is source-only work already
merged or queued on `main`; nothing here touches the editor until the custodian's window opens after ingestion
(Buff's estimate: Nov 4–6 if the memory fix holds, else Nov 13–19). This page is the one thing to read then.

## What is ready

Eighteen Prismheart minigames are native `ADaedalusDesktopArcade` cabinets. Each one regenerates its game from
`StartGame(id, seed)` alone with a CPython-compatible PRNG, so the Unreal cabinet, the Python rules
(`tools/minigames/<id>.py`, prism-shard-dev's, the authority) and the web page all play the same seed identically.

| id | title | cabinet header | PR |
|---|---|---|---|
| `shardring` | Shardring Resonance | `DesktopGames/DaedalusDesktopShardringCore.h` | #930 |
| `lumenpath` | Lumenpath Refraction | `DesktopGames/DaedalusDesktopLumenpathCore.h` | #947 |
| `wardens_accord` | Wardens' Accord | `DesktopGames/DaedalusDesktopWardensAccordCore.h` | #956 |
| `facetlock` | Facetlock Lattice | `DesktopGames/DaedalusDesktopFacetlockCore.h` | #956 |
| `prismcairn` | Prismcairn Duel | `DesktopGames/DaedalusDesktopPrismcairnCore.h` | #986 |
| `prismvault` | Prismvault Weigh | `DesktopGames/DaedalusDesktopPrismvaultCore.h` | #987 |
| `shardfall` | Shardfall Gamble | `DesktopGames/DaedalusDesktopShardfallCore.h` | #988 |
| `shadewatch` | Shadewatch Vigil | `DesktopGames/DaedalusDesktopShadewatchCore.h` | #1048 |
| `glimmerloom` | Glimmerloom Ledger | `DesktopGames/DaedalusDesktopGlimmerloomCore.h` | #1050 |
| `prismchime` | Prismchime Ring | `DesktopGames/DaedalusDesktopPrismchimeCore.h` | #1064 / #1076 |
| `fogbell` | Fogbell Ferry | `DesktopGames/DaedalusDesktopFogbellCore.h` | #1101 / #1102 |
| `roostcall` | Roostcall | `DesktopGames/DaedalusDesktopRoostcallCore.h` | #1118 / #1120 |
| `emberkiln` | Emberkiln | `DesktopGames/DaedalusDesktopEmberkilnCore.h` | #1126 |
| `sluicegate` | Sluicegate | `DesktopGames/DaedalusDesktopSluicegateCore.h` | #1130 |
| `glowmoss` | Glowmoss Delve | `DesktopGames/DaedalusDesktopGlowmossCore.h` | #1148 (core by prism-shard-dev) |
| `spiritkite` | Spiritkite Weave | `DesktopGames/DaedalusDesktopSpiritkiteCore.h` | #1152 (core by prism-shard-dev) |
| `shardscale` | Shardscale | `DesktopGames/DaedalusDesktopShardscaleCore.h` | #1164 |
| `stonecourse` | Stonecourse | `DesktopGames/DaedalusDesktopStonecourseCore.h` | core + cabinet PR |

All eighteen share `DesktopGames/DaedalusDesktopSaveText.h` (save text, input names, edge latches) after the #993
beauty pass. Every cabinet has a save slot in `DaedalusDesktopSaveSlots.h` (`<id>.dgs`, manual style) and a
fixture-replay test under `engines/unreal/core-test/desktop_games/`. Portable proof is in CI (desktop-games.yml,
engines.yml); what it does **not** prove is the installed plugin, native class loading, PIE input, file I/O and
reopened saves. That is this window.

`spiritkite` (Spiritkite Weave) is Python-only (`host: PythonMinigame`) and has no native cabinet yet; place
nothing for it.

## Placement

`data/minigames/realm-cabinets.json` → realm `prismheart_realm`, anchor marker `arcade_plaza`, layout `row`,
2.5 m spacing (the row re-centres as cabinets are added, so offsets shift by 1.25 m per addition; read the JSON), every cabinet yaw 180° (facing the anchor). Offsets are metres from the anchor; seeds are
`crc32("prismheart_realm:<id>")` and are stable. Realm id is still `id_status: unconfirmed` (REALMS.md rule).

| id | offset (x, y, z) m | yaw | `StartGame` | option |
|---|---|---|---|---|
| `shardring` | 0, −16.25, 0 | 180 | `StartGame("shardring", 2061739538)` | 0 |
| `lumenpath` | 0, −13.75, 0 | 180 | `StartGame("lumenpath", 2037330375)` | 0 |
| `wardens_accord` | 0, −11.25, 0 | 180 | `StartGame("wardens_accord", 450290639)` | 0 |
| `facetlock` | 0, −8.75, 0 | 180 | `StartGame("facetlock", 1644454135)` | 0 |
| `prismcairn` | 0, −6.25, 0 | 180 | `StartGame("prismcairn", 557933909)` | 0 |
| `prismvault` | 0, −3.75, 0 | 180 | `StartGame("prismvault", 895410454)` | 0 |
| `shardfall` | 0, −1.25, 0 | 180 | `StartGame("shardfall", 242191464)` | 0 |
| `shadewatch` | 0, 1.25, 0 | 180 | `StartGame("shadewatch", 1433643621)` | 0 |
| `glimmerloom` | 0, 3.75, 0 | 180 | `StartGame("glimmerloom", 1712892515)` | 0 |
| `prismchime` | 0, 6.25, 0 | 180 | `StartGame("prismchime", 113376713)` | 0 |
| `fogbell` | 0, 8.75, 0 | 180 | `StartGame("fogbell", 404876817)` | 0 |
| `roostcall` | 0, 11.25, 0 | 180 | `StartGame("roostcall", 1603034746)` | 0 |
| `emberkiln` | 0, 13.75, 0 | 180 | `StartGame("emberkiln", 1270422306)` | 0 |
| `sluicegate` | 0, 16.25, 0 | 180 | `StartGame("sluicegate", 427050219)` | 0 |
| `glowmoss` | 0, 18.75, 0 | 180 | `StartGame("glowmoss", 1109382819)` | 0 |
| `spiritkite` | 0, 21.25, 0 | 180 | `StartGame("spiritkite", 630418058)` | 0 |
| `shardscale` | 0, 23.75, 0 | 180 | `StartGame("shardscale", 644661142)` | 0 |
| `stonecourse` | 0, 26.25, 0 | 180 | `StartGame("stonecourse", 492740943)` | 0 |

The same row also lists four canonical cabinets (`dungeon`, `riftwing`, `star_shooter`, `lanternwild` at
y = −16.25 … −8.75) that already exist elsewhere; place them the same way or leave them for a later pass. Read the
JSON rather than this table if the two ever disagree: the JSON is generated and schema-checked, this is a copy.

Each cabinet: spawn `ADaedalusDesktopArcade` at anchor + offset, set yaw, call `StartGame(id, seed)`, then
`SetGameOption(0)` (option 1 is the Guide/practice mode on every Prismheart cabinet; leave it 0 for the realm).

## Build

Source only changed under `engines/unreal/DaedalusLink/Source/DaedalusLink/Public/` (headers) and
`engines/unreal/core-test/`. No new modules, no new `.uasset`, no Build.cs change. The custodian's normal batched
rebuild through `engines/unreal/setup-unreal.ps1` is enough; the headers are already included through
`DesktopGames/DaedalusDesktopGameRegistry.h`. Preflight (`tools/unreal_preflight/preflight.py`) is clean on all nine
(no try/catch, no forbidden editor flags).

## Acceptance: what the first frame must show

These are the Python rules' own opening states at the realm seeds (difficulty `normal`), and the native cabinets
reproduce them bit for bit in the portable tests. In PIE, open each cabinet and compare:

| id | first frame |
|---|---|
| `shardring` | current shard **tide**; ring of 10 empty facets; pouch 50 |
| `lumenpath` | 6×6 lattice, beam enters row 3; grid `....#.` / `....*.` / `.*#...` / `*.....` / `......` / `......`; LIT 1/3, MOVES 10 |
| `wardens_accord` | altar offer **verdant, tide, gale**; rounds 14; pouch all zero |
| `facetlock` | board rows `EEGE` / `TTET` / `VVTV` / `GGGV`; MOVES 9 |
| `prismcairn` | cairns **1, 5, 8, 3**; round 1/3; take 1–3 |
| `prismvault` | 12 shards, 3 weighings, all 12 suspects (the hollow one is shard 9; do not show it, but naming 9 wins) |
| `shardfall` | round 1/5, pot 0, seam of 15 shards (3 cracked); first draw is a **4** (the bag's top is the last value) |
| `shadewatch` | three lanes; shades at the far end of lanes 1 and 3, lane 2 empty; hearts 3, light 1 |
| `glimmerloom` | day 1/10, purse 100; prices **12, 9, 6, 11** (ember, tide, verdant, gale); rumor: **tide falls** |
| `prismchime` | eight dark chimes, taps 8; charges **2, 2, 2, 1, 1, 2, 2, 2**; facings ← → → ← → → ← → |
| `fogbell` | 8×8 flat, ferry north-west, harbour south-east, tide 0; lanterns (in draw order) at (4,2), (6,5), (2,0), (3,7); top row heights `87736483` |
| `roostcall` | 7×7 yard, whistler north-west, roost south-east 2×2, turns 30; birds (draw order) at (3,4), (6,1), (5,3), (6,3) |
| `emberkiln` | 6×6 floor, 27 coals, 30 raw tiles, tongs at (0,0); top row `## 0/3 0/2 0/2 ## 0/2`, stone at (0,0), (0,4), (1,3), (4,1), (5,0), (5,4) |
| `sluicegate` | 8×8 field, 12 turns, 5 gates, marker on the headgate (0,4); cisterns (draw order) at (2,3), (2,1), (4,0), (2,6); mill at (7,0); top row `.#..H+##` (+ = next push) |
| `glowmoss` | 10×4 shaft, surface start at column 2, light 11, best 44, target 35; row 0 gems 1412 (native == Python) |
| `spiritkite` | 8 isles, wind 28, target 18, plan 6,7,2,5,4,3,1; lantern values 0,1,5,2,5,5,2,4 (native == Python) |
| `shardscale` | 10 shards 1,5,2,1,5,1,2,4,5,7, cap 5, tolerance 1, bench 2, hand on the cart's first shard (native == Python) |
| `stonecourse` | 8-wide wall, 5 courses, 26 stones 2,1,1,2,2,2,1,2,2,3,3,3,3,2,1,2,3,2,2,3,1,1,3,3,3,3, 3 skips, marker at column 0 (native == Python) |

Then per cabinet, in this order, with the evidence named in parentheses:
1. Keyboard and pad input both act (one key press and one pad press change the frame).
2. Finish or abandon, press R / pad Start: the cabinet restarts at the same seed and shows the same first frame.
3. Save mid-game (Manual style: pause, then F5 / pad X writes `<id>.dgs`; F9 / pad Y continues it), close, reopen: score, note and board match, and the
   next random event (next shard, next spawn, next price drift) matches an unbroken session (cabinet tests prove
   this portably; here it proves the file round-trips through `DaedalusDesktopSaveSlots`).
4. Option 1 shows the Guide/practice counsel (blue mark) and option 0 removes it.
5. The access strip (KEYS line + MARK ACT / MARK WAIT) is on screen and readable at cabinet distance.

Report each cabinet as its own line: `placed` / `PIE input` / `restart` / `save round-trip` / `guide` / `access`,
with the build identity (commit on `main`) and a screenshot of the first frame. A cabinet that fails one step is
reported with that step, not pulled; unreal-team fixes it in source the same day.

## Who to ping

- Rules or balance questions → prism-shard-dev (Python is the authority; unreal-team re-ports on change).
- Cabinet behaviour, saves, input map, this document → unreal-team.
- Placement anchor, realm id confirmation → Buffffff / Richey.
