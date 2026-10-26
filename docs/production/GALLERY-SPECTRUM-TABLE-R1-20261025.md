# Gallery Spectrum Table — edition 1, 25 October 2026

## Purpose and creative boundary

An original, finishable Gallery colour/light practice puzzle: route six coloured
beams into four target windows, then study two more pictures. Gallery City's
knowledge is colour and light (`docs/realms/REALM-CASTS.md`). This puzzle is
new creative work authorized for this campaign, not a previously specified
ADR-035 mechanic or a canonical quest, Heartstone, story or reward contract.

Base: `e49d1007b118d110a08b272d0eec6bc2ad03dd47`.
Branch: `codex/gallery-spectrum-table-20261025-r1`.
Campaign deadline: **2026-10-26 06:56:50 UTC**.
Own six additive files: Spectrum Core, Table header/cpp, one core test, its
runner and this handoff. Every predecessor/variant and packet remains intact.
No shared input, Hero, dialogue, Build.cs, island, live source/asset, saved art,
painting supplies, server, parcel or ownership code changes.

## Playable rules

The six numbered sources are R, G, B, R, G, B. Each switch sends its source to
one of two windows. Channels combine by presence: two red beams are still red,
R+G is yellow, R+B magenta, G+B cyan, RGB white and no channels unlit. This is
a clear discrete channel model, not a claim about physical lighting intensity,
energy conservation, ray tracing, refraction or calibrated display colour.

| Source | Channel | Route A | Route B |
| --- | --- | --- | --- |
| 1 | R | Window 1 | Window 2 |
| 2 | G | Window 1 | Window 3 |
| 3 | B | Window 1 | Window 4 |
| 4 | R | Window 3 | Window 2 |
| 5 | G | Window 2 | Window 4 |
| 6 | B | Window 2 | Window 3 |

Three authored practice pictures have explicit target names and channel marks:

| Picture | Window 1 | Window 2 | Window 3 | Window 4 | Initial routes |
| --- | --- | --- | --- | --- | --- |
| Green Window | Green | Magenta | Red | Cyan | All B |
| Paper Light | White | Cyan | Red | Unlit | All B |
| Sunset Glass | Magenta | Yellow | Cyan | Unlit | All A |

Each picture has one solution. The UI shows targets rather than hidden solution
bits. Static ribbons/arrows, numbered source tags, window identifiers, colour
names and R/G/B presence marks explain the same model without requiring colour
discrimination. The original simple geometry is functional blockout, not an
imported production art or photometric-lighting deliverable.

Six route switches plus Next picture, Hint, Undo, Redo and Restart supply the
whole loop through existing E/X Usables. Each picture retains its own current
routes and latest 64 history entries when browsing the other pictures. Undo
can leave a solved state again. First-study information is separately retained
once per picture for this actor's life; it is not a durable profile or reward.
Restart requires native confirmation, resets only the current picture's
attempt/history, and retains first-study information and the other pictures.
Any other action cancels the armed restart.

Hints search the complete 64-state routing space for the fewest remaining
switch changes. Ties keep the smallest winning state and first differing source.
The clue names one source and A/B direction; it never applies a move for the
player. A useful turn need not immediately increase the number of matched
windows: Green Window's three-turn clue path includes such a plateau. Completion
feedback describes the actual current picture and separately shows pictures
ever studied. No route, clue, reset or completion spends resources or grants
items, currency, ownership or cross-realm capability.

## Opt-in native boundary

The table is a deliberately placed standalone actor using only its own
noncolliding components and 11 owned controls. It does not tick, move a pawn,
operate a world door, create physical light sources, call a server or read/write
any files. Existing real LocalPlayer/reach checks and exact tool bindings gate
input; missing owned views/controls refuse puzzle mutations. Model state is
committed before guarded informational notifications. Reentry, EndPlay and
lost participants must not continue native writes or manufacture completion.

The 680 cm wide backboard faces +X. Six sources rise at local
`(-75,250,110+60*i)`; four window cards rise at `(-75,-200,125+85*w)`.
Router controls use two banks, X=320/405, Y=160/0/-160, Z=65; the five
utilities use X=550, Y=240/120/0/-120/-240, Z=65. Geometry and label reach
remain source-defined placement, with actual readability pending acceptance.

There is no automatic world-placement integration. Native compilation and
activation remain with the sole Unreal writer. This patch has no functional
dependency on the earlier Motif/Study/Bricks/Labyrinth campaign actors; their
objects in the bundle preserve history for transfer, not a request to replay
those patches or previously integrated mural work.

## Evidence and queued native acceptance

A guarded serial MSVC C++17 `/W4 /WX` run passed **19 checks, 0 failed**,
covering all 192 picture states against an independent channel-presence fixture,
all 192 hint cases against independent hypercube BFS, duplicate-red behavior,
exact targets, invalid-output preservation, separate picture/history states,
reversible/current versus retained first completion, restart boundaries and
the exact latest-64 Undo/Redo limit. Fresh guard: **10.90 GiB free physical,
38.54 GiB free commit**. Review strengthened the existing history check to
compare every intermediate state; the affected portable executable was checked
once more and again passed 19/0, with **10.76/38.56 GiB** free at that guard.
No production-core change or other realm suite rerun followed.

Native UHT/module compilation, actor interactions, rendered ribbons/labels,
control reach, lifetime callbacks and cooking remain **uncompiled/unexecuted**.
Source review/preflight results are recorded with the final packet and do not
execute the native adapter. No editor, live activation, engine build, push or
merge occurs in this delivery.

Final source evidence: root and bounded portable/native peers found no remaining
blocker. Review corrected the native entry point to require the actual local
Hero and exact owned control slot/pose before edits; a retargeted control cannot
operate another table. Focused preflight reported **0 errors in two native
files**. The depth-paired router labels still need front-view occlusion/reach
acceptance; source geometry alone does not establish their readability.

Minimal acceptance queued with the sole writer after current production:

1. Place the table on existing safe ground; verify scale, E/X selection, all
   11 unique controls and target/current names plus channel marks. Confirm
   arrows follow A/B choices and all colours agree with the portable model.
2. Complete each picture, switch between partial/solved pictures, Undo/Redo a
   finish and confirm first-study feedback occurs once per picture. No global
   quest, inventory, physics, light settings or saved-art side effects.
3. Check the optimal clue plateau, confirm/cancel Restart, restart only the
   current picture and verify the others and first-study count remain intact.
4. Remove a view/control or end the actor from a notification; refuse further
   edits cleanly. Check standalone/local-player refusal boundaries, label
   readability, duplication/reload and cooked behavior separately.

## Lesson and next task

Use channel presence rather than XOR or matched-count greediness for a light
puzzle. A complete six-switch state space makes helpful exact clues cheap;
preserve each picture's work rather than resetting it on navigation. Keep
original practice rules visibly separate from canonical story/reward policy.
Native acceptance stays queued; continue useful isolated non-island source
work within the campaign deadline.
