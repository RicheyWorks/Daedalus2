# Unreal onboarding (for Unreal Epic Boss, `unreal-epic-boss`)

Created 2026-10-19 by Prometheus on Richey's order (relayed by Buffffff). One section per owner; add yours below.

## Prometheus — Island audio + Turing music engine

Repo is RicheyWorks/Daedalus2 unless noted. Status words: ON MAIN = merged; OPEN = not built.

**Java Island Audio core (ON MAIN).** `daedalus-core/src/main/java/com/daedalus/world/audio/` (15 classes: BiomeAmbience, AmbienceState/Layer, Biome, CallSynth, CallSpec, Genome, Species, Herb, HerbChord, JukeboxClient, JukeboxTransport, HttpJukeboxTransport, Rng, Wav). Landed in 3d964b4b, synced to main at b1716c10. Deterministic from seed, JDK only.

**AUD 1 endpoint (ON MAIN, PR41, team-codex).** `POST /api/v1/audio/design` returns text AUD 1: ambience layers + one PCS 1 creature call + jukebox cue. Contract `docs/contracts/aud-v1/README.md`. Auth: `daedalus.audio.host-subject` must equal the engine JWT subject.
**PR44 (PootScoot, DRAFT, not merged).** Native consumer `engines/unreal/DaedalusLink/Source/DaedalusLink/Private/DaedalusIslandAudio.cpp` + portable `DaedalusAudioCore.h`: decodes AUD 1, renders calls off the game thread, binds ambience by layer id. Compiled in an isolated host only; no Play proof; needs an actor binding and looping ambience assets.

**HRB 1 herb-chord endpoint (ON MAIN, 62ca681a).** `POST /api/v1/audio/herb-chord`, herbs -> `chord <root> <quality> <effect> <strength>` + `freq` lines. Same auth/rate limit as AUD 1. Contract + fixture `docs/contracts/hrb-v1/`. AUD 1 unchanged.
**HRB 1 C++ decoder (ON MAIN, 584b40e9).** Header-only `engines/unreal/core-test/hrb1/DaedalusHerbChordCore.h` (no UE deps), 33 checks incl. the Java-pinned fixture; `python engines/unreal/core-test/hrb1/run_hrb1_core.py --compiler cl.exe` (or g++ --sanitize).

**Prometheus Island (UE).** Sublevel `/Game/Prometheus/Maps/PrometheusIsland` in DaedalusWorld, origin (2000000, 2000000, 0) cm (`data/islands/prometheus/ue_transforms.json`). 24 AmbientSound emitters: 18 genome livestock calls (`PI_Call_*`, assets `/Game/Prometheus/Audio/Calls/`) + 6 beds (`PI_Snd_Stream_*`, `PI_Snd_IslandSong`). Demo stills (editor-world SceneCapture, no audio): `data/islands/prometheus/PI_audio_demo_{calls,call_close,ambience}.png` at 9d2c58ff. Known issue: terrain mesh vs heightmap mismatch ~6 m mean abs (shape, not placement; rotation r5 and translation r6 fits both failed). Wild Biomes scripts `engines/unreal/prometheus-island/wild-biomes/` are BLOCKED: target sublevel WildBiomes_* does not exist.

**Jukebox.** Asset `/Game/DaedalusAudio/SW_Jukebox_e00015` (placer `engines/unreal/prometheus-island/wild-biomes/daedalus_audio_quickplace.py`). Music engine: RicheyWorks/rd-music-nft `rd-music-nft/packages/rd-studio/` at 10e9b98 (Python; CC0 VSCO-2 CE samples fetched by `tools/fetch_r4.py`). Java `JukeboxClient` calls Art Master Flex's `/api/v1/jukebox` (client only; retries + breaker).
**Ear rules (keep in UE mixing).** No bright or piercing tones (beds low-passed, calls LP ~2.5 kHz), passing notes light, warm vinyl/headphone target; forest-cave and spacey sounds are never removed, only added to.

**Ecology x audio (agreed with Pythagoras, link 47958 / reply 48008; Java side OPEN, not yet on main).** Planned `AmbienceEcologyAdapter.sample(BattlefieldEcology eco, x, y) -> EcologyAmbience{burning, cover, concealment 0..1}`: burning fades in fire crackle and ducks creature calls; cover/concealment apply a gentle low-pass and volume dip. UE mirror uses the existing `UDaedalusEcology::BurningAt/CoverAt/ConcealmentAt` in `engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusEcology.h` (on main, 8ef8c75b).

**Open for the Unreal lead.** (1) Native HRB 1 consumer in UE (include the decoder, map effect -> gameplay/sound). (2) Audible playback proof (PIE capture with audio) for AUD 1 / calls / beds. (3) Runtime bridge: land PR44, bind PrometheusIsland emitters to it. (4) Terrain re-export to fix the 6 m mismatch. All Unreal writes go through codex-play-guard.
## Pythagoras: Battlefield Ecology + PCG island

Owner: pythagoras. Repo: RicheyWorks/Daedalus2. Relevant main commits: `7daf410d` (Java ecology + CoverField),
`dafbbf00` (C++ core + `UDaedalusEcology`; exception-free fix `f377c3bb`), `8ef8c75b` (battlefield-check module +
offline Java->C++->Java round trip + evidence), `436e73b7` (pcg-ecology/tools).

### What it is
Reactive Battlefield Ecology (ADR-061, `docs/adr/ADR-061-battlefield-ecology.md`): a grid of vegetation that gives
cover and concealment, burns and spreads fire with wind, and regrows by succession. It is deterministic from seed +
events. Java is the authority; Unreal reads snapshots and sends combat events back.

### Source map
| Part | Path |
| --- | --- |
| Java package | `daedalus-core/src/main/java/com/daedalus/world/battlefield/` (`BattlefieldEcology.java`, `Vegetation.java`, `Dbe.java`, `BattlefieldDemo.java`, `BattlefieldBench.java`) |
| Director wiring | `daedalus-core/src/main/java/com/daedalus/world/tactics/SquadDirector.java`: `SquadDirector.CoverField` has the same shape as `BattlefieldEcology::bestCover(ux, uy, thx, thy, radiusCm)`, so the ecology passes in as a method reference; the director never sends a squad into a burning cell |
| Java tests | `daedalus-core/src/test/java/com/daedalus/world/battlefield/` (`BattlefieldEcologyTest`, `BattlefieldDemoTest`, `DirectorCoverIntegrationTest`, `EcologyRoundTripTest`); `daedalus-core/src/test/java/com/daedalus/world/tactics/CoverAwareDirectorTest.java` |
| C++ core (plain C++17, no UObject, no exceptions) | `engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusEcologyCore.h` (namespace `daedalus::ecology`: `ReadSnapshot`, `Field::CoverAt/ConcealmentAt/BurningAt`, `WriteEvents`) |
| Unreal wrapper | `engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusEcology.h` and `engines/unreal/DaedalusLink/Source/DaedalusLink/Private/DaedalusEcology.cpp`: `UDaedalusEcology : UWorldSubsystem`, Blueprint-callable `LoadSnapshot`, `LoadSnapshotText`, `CoverAt`, `ConcealmentAt`, `BurningAt`, `QueueEvent`, `FlushEvents`, `LastError`, `Stats`, `GetEcology`. Default files `Saved/Daedalus/ecology.dbe` (in) and `Saved/Daedalus/ecology_events.dbe` (out) |
| C++ test (no Unreal) | `engines/unreal/core-test/ecology_core_test.cpp` (21/21; CI step in `.github/workflows/engines.yml`, gcc ASan/UBSan). Fixtures: `engines/unreal/core-test/ecology_roundtrip.dbe` (Java `BattlefieldDemo.scene(7)`), `engines/unreal/core-test/ecology_roundtrip_events.txt` (C++-written IGNITE; regenerate with `ecology_core_test --write`) |
| In-editor check | `engines/unreal/battlefield-check/` (`README.md`, `BattlefieldCheck.java` snap/apply, `battlefield_check_ue.py`) |
| PCG island + Wild Biomes | `engines/unreal/pcg-ecology/` (ecology rules, live PCG, island flora, succession sim, quests; pytest 28/28; `ISLAND.md`, `MECHANIC.md`, `ADVENTURE.md`, `README_WildBiomes.md`; bridge client `ue_send.py`; `tools/` probes; `evidence/` screenshots) |

### DBE 1 / DBE-E 1 contract (plain text, all or nothing)
```
DBE 1                                       snapshot, Java -> Unreal
grid <w> <h> <cellCm> <originX> <originY> <seed>
tick <n>
row <j> <w vegetation codes>                exactly h rows, j = 0..h-1 in order
fire <i> <j> <ticksLeft>                    zero or more, after the rows; ticksLeft 1..64; bare/wetland cannot burn

DBE-E 1                                     combat events, Unreal -> Java
event <IGNITE|BLAST|DOUSE> <x> <y> <z> <radiusCm>      at most 256 events (Dbe.MAX_EVENTS / MaxEvents); radius <= 100000
```
Vegetation codes (cover / concealment): `.` bare 0.00/0.00, `m` meadow 0.05/0.35, `s` scrub 0.25/0.65, `p` pine
0.55/0.70, `o` oak 0.80/0.60, `w` wetland 0.10/0.40. World X/Y map to cells by `floor((x - originX) / cellCm)`,
clamped to the grid (same in Java and C++). Errors: one bad line refuses the whole spec with `DBE line <n>: <reason>`
(Java throws; C++ returns `Result{Ok=false, Error}`; `UDaedalusEcology` keeps the old field and exposes `LastError()`).
CRLF is accepted.

### Status and the pending in-editor check
- `BOARD/ARCHITECTURE.md` (bot-team), row "Reactive Battlefield Ecology": **BUILDING**. Everything off-editor is on main and
  tested; the plugin compiled with RunUAT BuildPlugin (UnrealEditor + UnrealGame Win64).
- Not yet in the running editor: the plugin copy the editor loads, `C:\Unreal\DaedalusRealm\Plugins\DaedalusLink` on
  BLACKBEARD, is stale (no `DaedalusEcology*`, and no Streamer/Tactics/Homestead from main). It needs codex-play-guard
  (sole native writer) to sync it from main, rebuild, and restart the editor at a safe point with everyone's work saved.
- Then run ONE read-only check per `engines/unreal/battlefield-check/README.md`: `BattlefieldCheck snap` ->
  `battlefield_check_ue.py` via `engines/unreal/pcg-ecology/ue_send.py` (load, 5 queries, 1 IGNITE flushed) ->
  `BattlefieldCheck apply` (oak at 2000,1500 burning). No import, save, place or bind. When it passes the row moves off BUILDING.
