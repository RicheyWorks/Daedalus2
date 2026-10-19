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