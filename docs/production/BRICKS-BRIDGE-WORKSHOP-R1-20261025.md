# Bricks Bridge Workshop — edition 1, 25 October 2026

## Purpose and authored context

An original, finishable connection puzzle for Bricks: connect nine studded pads
to HOME using a limited total beam length, then study two more blueprints.
`docs/realms/REALM-CASTS.md:75–92` gives the Brick Realm building knowledge,
the Builder form and Foreman Kip's proposed bridge/tower blueprints. ADR-034
establishes the Bricks sandbox and protected obby/runway. These support the
theme; this workshop's precise graph, dimensions and rules are new creative
practice under the campaign authorization, not canonical quest conditions.

Base: `7f8fa1b28dde3e0d5b62981f93d4d37ad91e3a9c`.
Branch: `codex/bricks-bridge-workshop-20261025-r1`.
Deadline: **2026-10-26 06:56:50 UTC**.
Own six additive files: Bricks Bridge Core, Workshop header/cpp, focused core
test, runner and this handoff. No Bricks Obby/Stencil, world build rules,
Java engine, inventory, Hero, shared input/dialogue, island, arcade-owner,
Build.cs, live source or assets change. All predecessor packets remain intact.

## Player rules

The blueprint has nine pads in a 3×3 grid and twelve possible neighbouring
spans. Pads are numbered 1..9; pad 1 is HOME. Select a span to add/remove its
beam. Each label shows span number, length and IN/OUT; a closed span has an X
and CLOSED text. Connected pads also say LINKED. Colour is supplementary.

Every beam uses its integer Manhattan length between the drawn pad coordinates.
The allowance is the least total length that can connect the whole blueprint.
This is a local model allowance, not player stock, currency, shared inventory,
structural engineering, physical bridge safety or world collision. No material
is debited or granted, and no world bridge/block is built by solving the table.

| Blueprint | Column coordinates | Row coordinates | Closed span indices, 0-based | Allowance | Winning networks |
| --- | --- | --- | --- | --- | --- |
| Open Spans | 0,2,5 | 0,1,4 | none | 16 | 24 |
| Side Repair | 0,2,5 | 0,1,4 | 2,10 | 16 | 7 |
| Long Crossing | 0,1,4 | 0,2,5 | 0,8 | 18 | 7 |

Link order is horizontal row-major first, then vertical row-major: `(0,1)`,
`(1,2)`, `(3,4)`, `(4,5)`, `(6,7)`, `(7,8)`, `(0,3)`, `(1,4)`, `(2,5)`,
`(3,6)`, `(4,7)`, `(5,8)`. The native UI displays indices plus one.
All three blueprints begin empty. Over-length additions and closed spans refuse
without changing beams or Undo/Redo. Removing a selected beam remains legal.
Loops can consume allowance without linking a new pad, teaching why a useful
network avoids redundant connections.

Each blueprint retains its own work and latest 64 Undo/Redo entries while
browsing. Restart requires confirmation, resets only the current plan/history
and retains the other plans and once-per-blueprint finished note. Current
completion remains reversible; the first-study informational event is not an
award or durable player-profile update. Any other action cancels Restart.

Hints consider the complete bounded state space and choose the fewest changes
to a winning network, with numeric-state tie breaking. They remove the first
extra selected beam before adding the first missing beam. Thus a full allowance
does not produce an impossible add instruction: removal makes room first.
Remaining edits include the suggested step; a helpful removal may temporarily
reduce HOME's connected pad count. A clue never performs an edit for the player.

## Existing implementation reuse

The portable core adapts the project's union-find pattern from
`daedalus-core/src/main/java/com/daedalus/util/DSU.java` and the spanning-network
approach in `engine/generators/KruskalsGenerator.java`. Original Java sources
remain read-only. This is not a port of maze generation, its random shuffle,
seed mapping, world geometry or balance rules.

A fixed bounded cache enumerates 4,096 subsets per blueprint once, retaining
minimum-length winners in roughly 25 KiB. Evaluation supports all 6,144 allowed
subsets across the three layouts, including over-length candidates for inspection;
such candidates cannot complete and Session refuses to install them. Invalid
indices/closed masks retain caller outputs. Hints use cached winners rather than
rebuilding the graph every frame. There is no Tick, heap-sized world inventory,
network call, file format or persistence framework.

## Native opt-in assembly

Place the new actor deliberately on existing safe ground. All owned components
and controls are noncolliding; it never moves a pawn, opens a world door or
changes obby physics. The +X-facing board is 650×600 cm. Pad coordinates render
at local `(-75,250-100*column,35+100*row)`, so each model unit has the same
100 cm scale in both board axes. Nine four-stud pads, selected/ghost spans,
length marks and text show actual model state. Geometry is original functional
blockout, separate from production Blender art and native asset acceptance.

Twelve span controls use X=320/440/560, Y=180/60/-60/-180, Z=65. Five utility
controls use X=720, Y=240/120/0/-120/-240, Z=65. The actual local Hero, exact
owned slot/binding/pose and all required views/controls gate model writes.
Reconfigured foreign controls cannot operate another workshop. Deferred spawn
tracks staged and returned actors; failure removes callbacks and cleans only
new exact-owned effects, preserving earlier and foreign actors. EndPlay guards
notifications and removes callbacks before owned cleanup.

## Evidence and native acceptance

An independent design calculation enumerated eight-edge combinations using
BFS and coordinate lengths, finding the allowances/counts above and first
numeric winners 1011/1011/766. This was a tiny offline design check, not native
execution or Java-engine parity. Focused portable tests and final source review
results are recorded after the guarded run in the immutable packet.

Final evidence: one serial MSVC C++17 `/W4 /WX` run passed **19 checks, 0 failed**,
including all 6,144 allowed subsets against independent BFS/cost evaluation,
recursive eight-edge minimum-network combinations, legal-state multi-source
hint distances and exact 73-edit/latest-64 history states. Fresh guard reported
**10.94 GiB free physical memory and 37.98 GiB free commit**. Root and bounded
portable/native peers found no remaining source blocker. Focused preflight
reported **0 errors in two native files**. No other realm suite was rerun.

Native UHT/module compilation, actual 17-control E/X, labels, stud rendering,
reach, spawn/lifetime behavior and cooking remain **uncompiled/unexecuted**.
No editor, live staging, engine/full-repository build, push or merge occurs.
The existing **Bricks Obby landing/rescue ordering hold is unchanged**; this
noncolliding workshop does not establish any movement/health acceptance.

Minimal queued acceptance for the sole Unreal writer:

1. Place a fresh workshop on safe ground; verify all 17 controls, +X orientation,
   source lengths, labels and HOME/LINKED/IN/OUT/CLOSED cues at normal reach.
2. Complete each blueprint, browse partial plans, Undo/Redo a finish, reject
   over-length/closed edits and confirm/cancel current-only Restart. Finished
   notes/events occur once per blueprint; no inventory or world-build changes.
3. Fill the allowance with an unhelpful loop; follow a legal removal-first clue
   to a winning network. Verify remaining-edit wording and temporary connection
   loss without changing another plan's history.
4. Retarget/remove controls or views and end actors during spawning/events;
   refuse edits and preserve earlier/foreign actors. Check control-bank label
   occlusion, reload/duplication and cooked behavior separately.

## Lesson and next task

An exact small graph search can teach economical construction without inventing
an inventory or a physics engine. Hints must respect intermediate constraints,
not just final distance; remove extra pieces before adding when allowance is
full. Native acceptance remains with the sole writer; continue useful source
work in the authorized lane until the campaign deadline.
