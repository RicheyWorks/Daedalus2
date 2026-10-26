# Battlefield ecology check (ADR-061)

The end-to-end check for Reactive Battlefield Ecology: Java writes a snapshot, Unreal's `UDaedalusEcology` reads it and
answers cover / concealment / burning, Unreal writes an IGNITE event, Java applies it.

| Step | Where | Command |
| --- | --- | --- |
| 1 | BLACKBEARD shell | `java -cp "../../../daedalus-core/target/classes;." BattlefieldCheck snap C:\Unreal\DaedalusRealm\Saved\Daedalus\ecology.dbe` |
| 2 | running editor (editor turn from codex-play-guard) | `python ../pcg-ecology/ue_send.py battlefield_check_ue.py 300` |
| 3 | BLACKBEARD shell | `java ... BattlefieldCheck apply ...\ecology.dbe ...\ecology_events.dbe` (expect `burning_after=true`) |

Pass: `class_loaded=True subsystem=True load=True`, the UE numbers equal the JAVA numbers from step 1, `flush=True`,
and step 3 shows the oak at 2000,1500 burning.

The same round trip runs offline in CI without Unreal: `core-test/ecology_core_test.cpp` reads
`core-test/ecology_roundtrip.dbe` (written by Java) and must produce `core-test/ecology_roundtrip_events.txt` byte for
byte; `daedalus-core` `EcologyRoundTripTest` checks Java still writes that snapshot and applies those C++ events.
Regenerate the events after a format change with `ecology_core_test --write` (run in `core-test`).

## Last in-editor pass (2026-10-19 04:38 PT, link 49531)

unreal-epic-boss ran the read-only check on a transient `UDaedalusEcology` (editor PID 54620; nothing saved, 0 unsaved packages) with
`staging\grok-editor-custody-20261019\hf_ecology_check.py` (bot-team) against `core-test/ecology_roundtrip.dbe`
(1464 bytes, sha256 `34c179ee7181efd5714563d37f3291cfd00bebf26f35a802c7cb3f50fd3c6918`):

| Check | Expected (Java) | UE |
| --- | --- | --- |
| LoadSnapshot / LastError | true / empty | true / empty |
| Stats | `field=40x30 tick=0 queued=0` | same |
| CoverAt / ConcealmentAt (900,1500,0) | 0.05 / 0.35 | 0.05 / 0.35 |
| CoverAt / ConcealmentAt / BurningAt (2000,1500,0) | 0.80 / 0.60 / false | 0.80 / 0.60 / false |
| QueueEvent(IGNITE, (2000,1500,0), 150) + FlushEvents | equals `core-test/ecology_roundtrip_events.txt` | byte for byte (37 bytes) |

Status: VERIFIED (registry row Reactive Battlefield Ecology).
