# Keeper Oriel's Seed-Song conversation

Code-only NPC slice, 2026-10-23, on `codex/island-npc-conversations-20261023` in the isolated NPC checkout.
This builds on `docs/islands/YOUTUBE_MASTER_ISLAND.md`, the existing Seed-Song actor and the authored
Keeper Oriel lines, record hints and quest in `DaedalusSeedSongCore.h`.

## Behavior

Interact at the existing gramophone opens the existing Hero dialogue UI. The opening shows current progress.
The player can explicitly listen to Keeper Oriel, hear the next record's existing clue, review a mend, or leave.
Only **Listen to Keeper Oriel** calls the existing `Talk()` method, which can complete the original talk quest
step. Opening, hints, Back and Not now produce no talk quest event.

A mend has a separate review page showing the exact record and all loaded herbs in order. Its confirmation
warns that trying the mend uses those herbs even when the record does not mend. This preserves the original
actor's attempted-mend consumption: a confirmed attempt calls the existing `Restore` and clears the loaded
`KettleHerbs`, including failed attempts. No refund, reward, recipe, inventory or quest policy has been added.

The review snapshots the record, herb order and existing event counter. External Restore, Draw or Talk calls,
record progression or herb changes invalidate it. Confirming an old review uses nothing, shows current details
and requires fresh confirmation. Menu choices are saved as displayed, so changing herb availability cannot
reinterpret an old choice index. Every menu ends with **Not now**, matching native B/Escape behavior.

The actor keeps a weak hero and realm identity, removes its dialogue delegate on finish/cancel/EndPlay, and
detaches when its hero disappears, changes realm or no longer has dialogue open. Current page plus exact
presented choices govern callbacks; closed/invalid inputs leave rather than performing a mend. The normal
Hero dialogue contract allows the next line to open synchronously in an outcome callback.

Existing public `Restore`, `Draw`, `Talk`, spring interaction, core rules, authored lines and tune CSV are unchanged.
No new NPC, story chapter, AI framework, economy action or live content placement is introduced.

## Owned files

- `engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusSeedSong.h`
- `engines/unreal/DaedalusLink/Source/DaedalusLink/Private/DaedalusSeedSong.cpp`
- `engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusSeedSongGuide.h`
- `engines/unreal/core-test/seed_song_guide_test.cpp`
- `engines/unreal/core-test/run_seed_song_guide.cmd`
- `engines/unreal/DaedalusLink/Source/DaedalusLink/Private/Tests/DaedalusSeedSongGuidanceTest.cpp`
- This handoff.

Hero, shared dialogue/Slate, Talker, Orrery, Portal, arcade, RPG demo, ingestion and board files are untouched.

## Validation stage

**Coded and offline-checked; not Unreal-compiled, integrated or runtime-tested.** At the first checkpoint the root worker ran the two
focused checks serially after the contributor returned ownership: guide **12/12**, existing Seed-Song core
**10/10**. Both compilations passed with warnings treated as errors. Reproduce with:

```
engines\unreal\core-test\run_seed_song_guide.cmd <absolute-output-folder>
```

The runner builds the focused guide checks and the existing Seed-Song parity/core checks with MSVC C++17,
`/EHs-c- /D_HAS_EXCEPTIONS=0 /W4 /WX`, sequentially; this is not an engine/UHT build. The unchanged parser uses
`std::stoi`, but these sources contain no explicit throw/try/catch and the fixture contains valid note values.
The exception-disabled build passed for the valid authored fixture; malformed parser input is outside this slice.
Guide checks cover every menu availability state, actual native B/A behavior, explicit confirmation, changed
record/herb/progress snapshots, exact ordered review text, authored hints leaving the pending talk step alone,
explicit listening completing the existing step, and existing failed-mend outcomes. Actor/delegate behavior
still requires native acceptance. The existing core test checks the computed 392-line replay count; no Java build
or separate cross-language fixture comparison was run for this slice. `git diff --check` passed.

## Continuation: actionable clean-water advice

After preserved checkpoint `102c6cae3`, the existing Listen page gained **Which springs are clean?**. That read-only
page lists exactly the supplied chapter spring names currently marked clean. If none are clean it refers to these
song springs, not to all water on the island, and explains the unchanged record-to-spring progression. Existing Home,
record clue, mend review and attempted-mend rules remain unchanged; enums were extended at the end.

The const `SpringName` query and spring interaction prompt use those same authored names. Unknown ids or an
unready chapter fall back to the existing id. The directory reads chapter names; the optional camera guidance
below resolves actual placed actors. The existing first-chapter-in-world spring binding remains unchanged.

Fresh continuation checks: guide **16/16**, existing core **10/10**, compiled serially with the same MSVC flags.
New coverage includes the actual partial/none/all twelve clean-name lists, Water cancellation/navigation, unchanged
quest/event ledgers and unchanged draw counts. The native actor/query/prompt are source-reviewed, not compiled or
runtime-tested. During later editor acceptance, compare actual spring prompt names to the directory and verify that
opening/repeating/leaving Water creates no draw or quest event. Physical spring placement and labels still need scene
acceptance; this source query is not a map or proof of in-world placement.

## Continuation: point toward a real clean spring

After preserved wave-three checkpoint `780b339b3`, Water can offer **Look toward a clean spring** when a local
player controller and an eligible placed spring are available. It first reviews the spring's authored name and
explains that **Turn my camera** turns the view while the player stays in place. Only that separate confirmation
calls the existing `ADaedalusHero::AimAt` and closes the conversation. Back, Not now, reading and reviewing do not
rotate the camera. There is no movement, navigation route, map marker, water grant, purification, herb consumption
or quest/event action; the player chooses a safe path and uses the original spring interaction there.

Candidates must be loaded, visible, valid same-world/same-level `ADaedalusSeedSpring` actors with an exact clean
ID in this chapter, resolving to this gramophone under the existing `Find` contract. Choose nearest by straight-line
distance, with actor path/ID as stable internal tie breakers. Paths are never shown as player-facing text. The
same-level restriction avoids inferring a destination on a different island; split-level scenes need the owner to
review their placement/binding rather than broadening the search silently. No eligible actor means no pointing
choice, even when the chapter directory contains clean names.

The review snapshots weak actor and controller references, spring ID and position. Confirmation requires the exact
local player controller still possessing this hero, the same realm, the Spring page and a valid active subscription,
plus a still-clean/visible matching destination at the reviewed position. Retargeted, moved, hidden, ended or
unavailable destinations cannot turn the camera. Changed details refresh the review and require another explicit
choice; cleanup invalidates the completed action before AimAt, preventing replay. Native dialogue still lacks an
actor/session token, so arbitrary external same-speaker queues remain a host coordination limitation.

Fresh focused checks passed **28/28 guide** and **10/10 unchanged core**, serial MSVC 14.44.35207 x64 C++17 with
`/EHs-c- /D_HAS_EXCEPTIONS=0 /W4 /WX`. Coverage includes 56 menu states, native B/B/A, separate review/look gating,
unchanged three-argument menus, actual none/partial/all chapter cleanliness, nearest eligible target selection,
missing/dirty/unavailable/unnamed/invalid-distance targets, stable ties and unchanged quest/event/draw state.
Independent source review found no blocker in the actor, helper, tests and native fixture. The runner is unchanged.

`Daedalus.NPC.SeedSong.CleanSpringGuidance` is an authored **uncompiled/unrun** fixture. It tests native scene and
controller binding through a narrow friend seam in an isolated transient world, never calling Speak/Use or
attaching a fixture controller's UI to the real viewport. It checks hidden/unknown/dirty destinations, moved/retargeted
reviews, cancellation, one-shot AimAt and unchanged location/herbs/quest/event/draw state. It does not verify full
dialogue flow, controller replacement, cross-level placement or post-review cleanliness changes. UHT, actor/fixture
compilation and all live acceptance remain pending. No Unreal/Blender launch or live-project change occurred.

## Integration and native acceptance

Ingestion owns the sole Unreal editor through 2026-10-24 18:50 UTC. The editor owner must authorize any later
integration and acceptance. Apply only these owned source files through the normal project workflow.

1. Compile through the normal Unreal workflow when permitted; use an existing `ADaedalusSeedSong` gramophone
   and the existing Hero. This source change does not place or import actors or art.
2. Open and leave with herbs loaded. Verify no herbs, event counter or quest progress changes. Open over another
   overlay and confirm the interaction refuses without leaving a subscription or changing progress.
3. With the talk quest step pending, open, read a clue and go Back: the step must remain pending. Select Listen:
   the authored Keeper line appears and the existing step completes. Test before and after all records are mended.
4. Review the exact herb order. Back and Not now preserve it. B skips text; B then A selects Not now. Confirm an
   unchanged review: exactly one original restoration attempt occurs and its loaded herbs clear, including a
   failed/short-herb attempt. Progress/result lines must reflect the existing core outcome.
5. While a review is open, replace/reorder/clear herbs or call external Restore, Draw or Talk. Select its old
   confirmation: nothing clears and current details require a new confirmation. Recheck missing/all-mended states.
6. Change realm, destroy/end the actor or hero, or close/interleave other dialogue. Old callbacks must not mend
   a record or complete a talk step. Test multiple gramophones sharing the Keeper Oriel speaker label: an old
   conversation must close before another can subscribe through Use.
7. Verify existing Blueprint/console Restore/Draw/Talk and spring interactions retain their original behavior.
8. With a local player and real same-level clean springs, open Water, review a named spring and confirm Turn my
   camera. Verify one view turn toward that actor, dialogue closure, unchanged position/progress/herbs/water, and
   original draw behavior only after walking there and using the spring. Test all cancel paths; moved, hidden,
   re-ID'd, unloaded or destroyed targets; controller replacement; split levels; dirty/no-target cases and realm exit.
   Run the focused native guidance fixture only when permitted. Camera modes and perceived route clarity still
   need manual acceptance; direct pointing does not establish a walkable route.

Remaining source dependency: Oriel kettle loading still needs a host-resolved inventory/source and validated
ordered-herb transfer/consumption contract. Existing melody-bench OnBrewed omits the original herb sequence and
initiating player, so this worker does not copy arrays, infer ownership or manufacture restoration ingredients.

## Lessons

- Reading a keeper line and applying its quest event are distinct: `Talk` changes the original quest at its talk
  step, so only a deliberate listening action may invoke it.
- The loaded herb order matters. Review comparisons preserve every entry and its order instead of normalizing
  names or treating the kettle as an unordered bag.
- Native dialogue reports speaker and choice, without an actor/session token. Exclusive opening, weak listener
  cleanup, displayed-choice snapshots and current review validation protect this actor's flow without changing
  the shared dialogue implementation. Arbitrary externally queued same-speaker menus still need integration review.
