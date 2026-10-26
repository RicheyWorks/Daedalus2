# Native NPC integration — 24 October 2026

Twin Doors and Keeper Oriel are integrated into the existing UE 5.8.4 project.
The source cut is based on `b684100d8ac725e10cb6d23290e6a119989f3b61`, selecting the
Twin Doors/Oriel files from NPC tip `a552ba3f7d48819df2872e1ef3bf9fe725bf8b4a`.
Shared Hero, dialogue/Slate, story cores and reward policy are unchanged.

## Saved scene

`/Game/Daedalus/Integration/NPC/20261024/R1/L_NPCConversationCourt`

This owned private scene has a 60 × 60 m collision floor, boundaries, safe spawn,
Twin Doors facing the approach, Oriel's gramophone and two named song springs.
`BP_NPCConversationRules` uses the already proven native Blueprint recipe to
store the encounter setting, disable automatic encounters during Play and restore
the prior setting on EndPlay. It is compiled/saved here; its lifecycle was not
repeated in Play during this tranche. Existing materials are reused unchanged.

Open the scene, Play, walk to a named station and press **E** for its existing
native interaction. Follow the dialogue choices. The fresh Oriel chapter has no
fabricated restoration progress or herbs: spring pointing appears only when an
actual clean, loaded same-level spring is eligible. Inventory-to-kettle loading
remains deferred. Primitive NPC bodies are existing native fallbacks, not final
character art. This scene is separate from protected R9 and the Commons.

## Actual native acceptance

- Native editor builds passed, including UHT and both new actor/fixture files.
- `Daedalus.NPC.TwinDoors.GuideChoices` passed: cancel, displayed-question
  snapshot, clue/replay, explicit correct/wrong choices and reset/stale cleanup.
- `Daedalus.NPC.SeedSong.CleanSpringGuidance` passed: eligibility/refusal,
  read-only dialogue browsing/cancel, separate reviewed camera confirmation,
  one-shot action, unchanged location, herbs and event/progress ledgers.
- Final focused two-test run at **02:33:36 UTC** passed both with **zero warnings,
  zero errors and zero missing-world-context messages** in its retained interval.
- Final acceptance checks the owned court clean/idle, outside Play and automation,
  with no dirty temporary maps. Protected R9, original sources/materials, saved
  player files and all 392 ingested islands remain pinned.

The fixtures use transient worlds that never begin play, avoiding Hero's real
save/load lifecycle and a real game viewport. Oriel's read-only Listen page uses
the fixture friend seam to avoid the deliberate Talk quest action. This proves
native actor/dialogue behavior; it does not claim a human-reviewed live HUD,
final character presentation or complete production-world placement.

## Concrete corrections

The first Oriel fixture failed before camera confirmation because its temporary
controller lacked native local-controller designation. `SetAsLocalPlayerController`
fixes that fixture setup; production eligibility remains strict. Actual dialogue
checks were added without queuing a read-only page behind an open Home page.

The user-reported `UWorld::DestroyActor: World has no context` warning came from
destroying a temporary spring in a fixture world created without an engine world
context. Both owned fixtures now register their own Game context, keep it alive
through actor/world destruction, then remove only that context. They clear only
their own unsaved temporary package dirty flag. No warning was suppressed.

The native build legitimately changed source and the plugin DLL. Versioned parity
receipts advance only exact reviewed before/after pairs; historical packaging
source copies remain immutable and all unrelated pins retain their checks.

## Recovery and evidence

Operator receipts, original binaries/source/config backup, failed first results,
successful reruns and local captures are retained under:

`C:/Users/730ri/Documents/Codex/2026-10-14/task-2/npc-integration-20261024/TrancheR1/`

- `recoverable-live-baseline.json`
- `WorldContextRepairR3/native-context-fixed-result-r3.json`
- `WorldContextRepairR3/native-context-fixed-run-r3.log`
- `ConversationCourtR1/npc-overview-r1.png`, `npc-twin-doors-r1.png`, `npc-oriel-r1.png`
- `ConversationCourtR1/ReadNPCFinalCleanTeardownR3-terminal.json`

Ingestion remains paused: **392 whole island designs and 101 supporting designs**
saved/native Valid, next untouched seed **10392**. Its stop flag remains retained.
Do not launch an old importer or replay completed sources during integration.

Wren tonic, Forge/Ark player bindings, First Words, inventory consumption/transfer,
Mail settlement, production-world NPC placement and arbitrary external
same-speaker dialogue coordination remain deferred. No minting, wallet activity,
security change, remote publication or PR merge occurred.
