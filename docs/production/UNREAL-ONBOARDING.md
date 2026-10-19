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