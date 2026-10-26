# Twin Doors guard interaction

Code-only NPC worker, 2026-10-23. Base: `b684100d8` on the read-only Epic integration reference. Isolated branch:
`codex/island-npc-conversations-20261023` in `C:/Users/730ri/Documents/Codex/2026-10-23/task-5/npc-island`.

## Player-facing slice

The existing Twin Doors guards now use the existing Hero dialogue interface. Interact opens a readable question;
the player explicitly asks it, then chooses the left or right door, asks for a clue, or leaves. A clue offers a bell
replay and a return to the doors. Every menu ends with **Not now**, matching native B/Escape behavior. The heard
tone is also written as low/high text. A proven clue uses the existing deduction rules; an inconclusive answer
does not reveal the hidden safe door. Leaving after asking preserves that answer for the next conversation.

Previously the actor showed a five-second debug message and the next Interact selected the nearest door. Player
position no longer chooses a door. Existing public Ask/Choose/ResetRiddle, bell/door delegates, seed progression,
door swing, lore and reward policy remain the source contract. A wrong choice still resets only this puzzle.

This follows `docs/realms/LABYRINTH-BUILDOUT.md` (Listen before choosing) and the established Twin Doors role in
`docs/realms/REALM-CASTS.md`. No new characters, story chapter, inventory reward or AI framework was introduced.

## Owned source

- `engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusTwinDoors.h`
- `engines/unreal/DaedalusLink/Source/DaedalusLink/Private/DaedalusTwinDoors.cpp`
- `engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusTwinDoorsGuide.h`
- `engines/unreal/core-test/twin_doors_guide_test.cpp`
- `engines/unreal/core-test/run_twin_doors_guide.cmd`
- `engines/unreal/DaedalusLink/Source/DaedalusLink/Private/Tests/DaedalusTwinDoorsGuideTest.cpp`
- This handoff.

The guide header holds only actor-specific words and choice intents, allowing low-memory offline checks. Puzzle
rules remain in the unchanged `DaedalusTwinDoorsCore.h`. Hero, shared dialogue/Slate, Orrery, minigames, RPG demo,
Portal, ingestion and board files are untouched.

## Validation stage

**Coded and offline-checked; not Unreal-compiled, integrated or runtime-tested.** No editor, Blender, UHT, engine
build or live project operation was used. The two focused C++ files compile serially with MSVC C++17, exceptions
off and `/W4 /WX`:

```
engines\unreal\core-test\run_twin_doors_guide.cmd <absolute-output-folder>
```

Latest result: guide **11/11**; existing plugin puzzle parity/session **9/9**. The guide covers menu limits and
leave-last behavior, closed/invalid inputs, actual native B/A input semantics, explicit door intents, question and
low/high observation text, honest clues across 2,080 seeded questions, and replay preserving the one-question
session, plus per-attempt result text. Existing checks cover fixture byte parity, the embedded solution over 2,000 seeds, refusal semantics,
one question/one door and unchanged bell frequencies. `git diff --check` passed.

Follow-up source review hardened the native lifecycle: the displayed question is snapshotted, riddle revisions and
realm identity reject stale menus, and Reset/Choose/EndPlay or an interrupted listener detach the callback. Door
results reacquire a weak hero after synchronous events and use immutable per-attempt text. `OnBell` and
`OnDoorPicked` now fire after the corresponding message/state is applied, so listeners can safely inspect or reset
it. Existing delegate signatures and puzzle decisions are unchanged. This event ordering is intentional and should
be checked against any Blueprint listeners during integration.

`Daedalus.NPC.TwinDoors.GuideChoices` is an additional **authored but uncompiled/unrun** Unreal automation fixture.
It uses a transient world and an unpossessed Hero's actual DialogueInput for cancellation, displayed-question
snapshot, clue/replay, reset invalidation, explicit door choice, wrong-door reset, result closure and destruction.
It is provided for the editor owner; its presence is not runtime evidence.

## Editor-owner acceptance after exclusive ingestion window

Ingestion owns the sole editor until 2026-10-24 18:50 UTC. Do not integrate or launch the editor before the owner
permits it. When the source is accepted and resources allow:

1. Apply this branch's owned files to the integration source; compile through the normal Unreal workflow.
2. Place/use an existing `ADaedalusTwinDoors` in the Labyrinth review lane with a Hero using the Labyrinth theme.
   This patch changes the existing class; it does not place new NPCs or import art.
3. Open then leave before asking: seed, asked and solved state must remain unchanged. Opening over another menu
   must refuse without spending the question. Skip text with B; confirm that B then A selects Not now.
4. Ask once, leave, return, request a clue, replay the bell and return to the door menu. Verify the same observed
   tone, no second question, and both audio delegation and readable low/high text.
5. Stand nearer each physical door and explicitly select the opposite label. Confirm the requested door is chosen
   regardless of hero position, labels match the doors as viewed from the intended approach, and the safe door
   swings once. A wrong choice increments the existing seed and closes both doors without health/inventory loss.
6. Reset/destroy the actor while a menu is visible and close the old menu; no stale choice may mutate a new puzzle.
   Verify existing Blueprint/console Ask/Choose, OnBell and OnDoorPicked still operate, including listeners which
   reset, solve, destroy a participant, or transition realms. Run `Daedalus.NPC.TwinDoors.GuideChoices` after native
   compilation if the editor owner approves the focused transient fixture.

## Lessons and environment note

- Native dialogue broadcasts outcomes before removing its widget; synchronous Speak from the actor callback is
  supported. Its pointer remains valid during that callback, so continuation must not reject it as an open box.
- B/Escape highlights the final choice. Leave must remain last on every guard menu.
- OnBell/OnDoorPicked are synchronous extension points. Session cleanup must tolerate resets during callbacks.
- The reference's `git status` failed with `fatal: this operation must be run in a work tree`; an explicit work-tree
  diagnostic reported `cannot come back to cwd: Permission denied`. Initial local clone startup also failed on the
  sandboxed Git MSYS named-object creation (`0xC0000022`). An approved elevated **local/shared, no-checkout clone**
  succeeded in the allocated workspace; no security/settings changes or source-repository writes were made.
- The local clone reads the original Git object store through its alternates file. Preserve the source object store
  until handoff, or use a self-contained Git patch/bundle when transferring the commits.
