# Bricks Skyline Workshop — edition 1, 25 October 2026

## Context, ownership and preservation

An original tower-blueprint practice for the Brick Realm. Set heights on a 4×4
model, use each height 1–4 once in each row/column, and satisfy the side-view
clues. `REALM-CASTS.md:75–92` gives the realm building knowledge and Foreman
Kip's proposed bridge/tower blueprints; ADR-034 supplies the sandbox context.
The exact visibility rules and three plans are new creative practice, separate
from canonical quests, actual world building, physics, inventory and rewards.

Base: `907c173008bf00d7a6b366003de60c1ca299f35a`.
Branch: `codex/bricks-skyline-workshop-20261025-r1`.
Deadline: **2026-10-26 06:56:50 UTC**.
Six additive paths only: Skyline Core, Workshop header/cpp, focused core test,
runner and this handoff. All six preceding checkpoint bundles remain intact.
No Sudoku/arcade/BRK01, shared input/dialogue, Hero, Obby, Bridge, world build,
Build.cs, live source/assets or board edits occur.

Focused ownership/source reads found no height/visibility puzzle or named
Skyline claim. Gallery's decorative skyline is unrelated. Exact guidance read:
own `AGENTS.md`, `C:/Users/730ri/projects/bot-team/BOARD/ARCHITECTURE.md`
(current 24 October standing plan/philosophy) and `LANES-UNREAL-CODEX.md`.
Saved Stencil/Obby/Bridge and limited minigame handoffs were checked for scope.
Existing Sudoku/Minesweeper/arcade owners remain reserved. This cannot exclude
unannounced worker code; the new Skyline-prefixed paths avoid their interfaces.
No guessed worker worktrees or denied targets were read.

The standing philosophy directs understandable saved creations and learning,
stable identities/lineage, preserved originals and one editor writer. Native
source/portable proof is kept separate from activation and runtime acceptance.
Production geometry remains a separate Blender/native pipeline responsibility;
these owned procedural shapes are functional original blockout.

## Rules and player loop

Choose Height 1/2/3/4 or Erase, then use a pad through existing E/X. A side
number counts record-high towers from that direction: a taller tower hides
shorter ones behind it. Empty height zero is ignored. A zero clue is an open
view with no required count. Gold-marked fixed entries cannot be edited.

| Blueprint | Left | Right | Top | Bottom | Fixed cells, 0-based | Valid skylines |
| --- | --- | --- | --- | --- | --- | --- |
| First Towers | 4,3,2,1 | 1,2,2,2 | 4,3,2,1 | 1,2,2,2 | 0=1;15=3 | 1 |
| Courtyard View | 2,2,1,3 | 2,2,3,1 | 3,1,2,2 | 2,2,3,1 | 5=1;10=3 | 2 |
| Open Skyline | 2,1,3,2 | open | 2,4,1,2 | open | none | 3 |

Every rules-valid skyline is accepted, including alternate solutions. Editing
may introduce a contradiction; all positive repeats are marked rather than
refusing the move or punishing the player. Fixed/no-op/invalid edits preserve
Undo/Redo. Side clues claim a match only when their own line is full and unique;
partial lines show BUILD, even if their current count happens to equal WANT.
Global cell-conflict marks stay separate from each clue's own-line judgement.

Hints find the nearest valid completion by cell Hamming distance, with
lexicographic completion ties. They first suggest a wrong nonzero entry's
repair, then an empty entry. One correct-height assignment reduces the nearest
distance by one; the clue never edits for the player. The chosen-height brush
stays outside drawing history, and selecting it keeps a shown hint visible.
An actual grid edit or blueprint change clears the old hint.

Each blueprint retains its own grid and latest 64 Undo/Redo entries while
browsing. Confirmed Restart restores only the current plan's givens/history.
Other plans and actor-life first-study notes remain. Current completion is
reversible; first-study events are informational, not canonical rewards or
durable profile updates. Actor-life practice does not promise a world save.

## Portable implementation

The core enumerates the 576 Latin4 grids using cell-wise row/column bit masks
and filters them by side clues/givens. Cached grids plus solution indices use
about 13 KiB, with a 100 KiB compile-time bound. No random seed, file format,
network, external solver, inventory or persistence framework is introduced.
Existing Sudoku/arcade engines, menus and application factories are untouched.

Evaluation reports all four view directions, full-line flags, repeat/given
conflicts, filled counts and matched specified clues. `LatinPossible` means
positive duplicate-free, not proof that a partial board can satisfy all clues.
Hints can repair such an incompatible partial board. Invalid-height/rule data
preserves caller output; missing/wrong givens cannot receive an impossible
locked-cell hint. Session owns only local fixed-rule practice state.

## Native assembly and feedback

The Workshop is an AActor rather than a centre Usable, avoiding selection
theft from its 16 floor cells. It owns 26 exact-mapped controls: 16 pads,
five height/erase choices and five utilities. All meshes/controls are
noncolliding; there is no Tick, pawn movement, camera takeover, world bridge,
door, canonical build edit, physical light or file I/O.

Cell centres are `((row-1.5)*180,-(column-1.5)*180,0)` cm, with 80 cm tower
footprints and 52 cm storey spacing. Numbered cell labels, storey shapes,
fixed markers, repeat borders and matching text supplement colour. Six box
faces carry outward normals/winding. Height controls use X=650 and utilities
X=830, each at Y=240/120/0/-120/-240, Z=65. Side cards face outward from
Y=±430 (Left/Right) and X=±430 (Top/Bottom), matching the logical row/column
order. This is an idealized blueprint visibility model, not pixel occlusion
from a specific player camera position.

Real standalone LocalPlayer/reach, exact owned slot/owner/binding/pose and all
critical view/control readiness gate edits. Deferred spawning reconciles staged
and returned effects; failure cleans only new exact-owned controls, preserving
earlier or foreign actors. Reentry and EndPlay are guarded, and callbacks are
removed before owned cleanup. No shared interaction dispatch is changed.

## Evidence and native acceptance queue

One guarded serial MSVC C++17 `/W4 /WX` run passed **25 checks, 0 failed**.
Independent whole-row permutations found all 576 Latin grids and 1/2/3 valid
skylines. Checks include 625 pairwise visibility lines, all 1,728 Latin/plan
reports, partial/duplicate/given distinctions, all alternatives, nearest repair
and lex ties, atomic outputs, fixed/no-op Redo retention and every intermediate
73-edit/latest-64 history snapshot. Fresh guard: **10.39 GiB free physical,
37.63 GiB free commit**. No other realm suite was rerun.

Root and bounded portable/native peers found no remaining source blocker.
Review fixed a native feedback mismatch where a crossing-line repeat could
incorrectly reject this line's valid clue. Focused native source preflight
reported **0 errors in two files**. The pattern check does not compile or
execute the native adapter.

Native UHT/module compilation, actual 26-control E/X, 3D/camera/text readability,
collision/reach, spawn/lifetime and cooking remain **uncompiled/unexecuted**.
No editor, live staging, heavy build, push or merge occurs. Bricks Obby
landing/rescue/health ordering remains a separate acceptance hold.

Minimal acceptance queued for the sole writer after current production:

1. Place on existing safe ground, outside protected obby/runway areas. Check
   all 26 controls, corridors, cell selection, 1–4/Erase, fixed markers and
   side-card directions/numbers. Inspect tower and label occlusion at player view.
2. Build a repeated row/column, repair it via Hint, and check that a correct row
   clue stays correct when only its crossing column conflicts. Partial matches
   must remain BUILD. Choosing a hinted height must retain the target marker.
3. Complete all valid alternatives, Undo a finish, browse partial plans and
   confirm/cancel Restart. Other grids/history and first-study notes remain;
   no inventory, quest, save or world-build mutation follows.
4. Retarget/remove controls/views or end actors during spawning/notifications.
   Refuse edits and preserve earlier/foreign actors; check fresh duplication,
   reload and cooking separately. Portable proof is not native acceptance.

## Lesson and next task

Judge each view clue by its own line while marking cell conflicts globally.
Accept alternate valid constructions, keep hints visible through the required
brush choice, and offer repair without erasing the player's whole board.
Next prioritize a coherent opt-in Bridge/Skyline teaching course using these
existing modules, with no canonical quest/reward or shared interface changes.
