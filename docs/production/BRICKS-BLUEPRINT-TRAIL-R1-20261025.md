# Bricks Blueprint Trail — edition 1, 25 October 2026

## Purpose and scope

Connect the existing Bridge and Skyline practices into one opt-in teaching
course. A deliberate E/X setup creates the two stations, ground wayfinding and
visit progress for their six blueprints. This turns the existing building
exercises into a walkable local learning loop without inventing Foreman Kip's
canonical quest, item cost, reward, inventory, profile or world-save contracts.
Both stations remain available for free exploration.

Base: `a05fed265496c3bed2d0695440d6c2219560e902`.
Branch: `codex/bricks-blueprint-trail-20261025-r1`.
Deadline: **2026-10-26 06:56:50 UTC**.
Five paths only: new Trail header/cpp, read-only readiness/first-study getters
in the two owned Workshop headers, and this handoff. Core rules/tests, existing
Workshop cpp, Obby, shared input/dialogue, Hero, arcade/Sudoku/BRK01, Build.cs,
live source/assets and shared board remain untouched. Every previous packet
and original identity remains preserved.

## Course contract

The new Trail actor begins unprepared. BeginPlay does not create either station.
First deliberate use by an actual standalone LocalPlayer attempts setup once.
The Bridge station is at local `(-900,-1300,0)` and Skyline at
`(-900,1300,0)`, on existing safe ground. Their existing controls and rules
remain unchanged. Paths and signs point to the two stations; the Trail origin
stays separate from their controls to avoid E/X selection theft.
Placement is upright at unit scale, with yaw allowed. Children are owned but
not attached: moving the Trail cannot drag an existing workshop. Readiness
rejects an externally attached child without detaching or reconfiguring it.

After setup, E/X at the Trail refreshes progress/directions, without resetting
or spawning another station. Each station keeps its own three grids/networks
and histories. The course observes actor-life first-study information through
read-only getters, including a snapshot after setup; it does not mistake
current Undo state for loss of the earlier study. All six first studies can
produce one informational course event. No quest, unlock, item, currency,
cross-realm capability or canonical persistent progress follows.

The added `IsWorkshopReady` and `WasBlueprintStudied` getters expose existing
read-only facts. They do not change either rules core, history, reset behavior,
input, geometry, existing completion events or source player data. Root checks
readiness before observing a node. Lost/moved/reowned nodes or a changed Trail
placement latch unavailability; cached progress and existing actors remain,
without silently substituting a new node or claiming active completion.

## Setup effects and preservation

Setup uses exact native classes and new actors owned by the Trail. Staged and
returned identities are reconciled across world callbacks. A null return does
not prove that no staged actor exists. Exact class/owner/world/pose, parent
epoch, participant/controller lifetime and node readiness precede commitment.
Pending effects remain tracked before normal callbacks and after partial failure.

One failed attempt stops automatic setup retries. Partially prepared stations
and their practice state are retained for review until normal actor teardown.
The course must not duplicate, replace, move, reconfigure or delete an earlier
or foreign actor to make a later attempt succeed. If the Trail ends mid-spawn,
returned/staged effects are reconciled and only new exact-owned effects may be
cleaned. Teardown removes its callbacks before destroying owned ephemeral nodes;
foreign actors are preserved.

All course geometry is noncolliding original wayfinding. There is no new floor
collision, Tick, pawn/camera move, physical light, world gate, auto-reset, file
I/O, network call, host authority or persistence framework. Existing native
interfaces and procedural mesh support are reused. Production art and actual
native activation remain separate work for their owners.

## Evidence and integration queue

This is native assembly/observation only. The unchanged Bridge **19/0** and
Skyline **25/0** portable results are reused rather than rerun or presented as
Trail runtime coverage. Focused source reviews/preflight are recorded in the
packet. They do not execute actor creation, input or native component behavior.

Final source evidence: root and bounded peers found no remaining blocker.
Review tightened the post-reach lifetime fence, attachment rejection and own
view-readiness gate before snapshot/event publication. Focused preflight
reported **0 errors across four changed native paths**. The unchanged portable
cores were not rerun; no spawning, E/X or renderer execution occurred.

Functional prerequisites: Bridge
`907c173008bf00d7a6b366003de60c1ca299f35a`, then Skyline
`a05fed265496c3bed2d0695440d6c2219560e902`, then this patch. The two original
workshops themselves are independent; the Trail consumes both. Earlier Gallery
and other campaign objects in a bundle preserve transfer history and are not
functional dependencies. Do not blanket-replay old backlog or mural work.

Native UHT/module compilation, course setup, paths/text, station reach,
callbacks/lifetime, actual six-plan progress and cooking remain
**uncompiled/unexecuted**. No editor, live staging, heavy build, push or merge
occurs. Bricks Obby landing/rescue/health acceptance remains separately held.

Minimal queued acceptance for the sole native writer:

1. Place a fresh Trail on safe ground outside protected obby/runway areas.
   Confirm no automatic station creation, then one E/X setup creates exactly
   one of each station and all their existing controls; repeated E/X adds none.
2. Follow both marked paths, work on different plans and return to the course
   board. Finish a plan, Undo it, and verify the visit's first-study note stays.
   All six studies produce one course event; no canonical progress/reward writes.
3. Remove/retarget/move a node or end the Trail/performer during setup/events.
   Preserve cached facts, partial stations and foreign actors; no hidden retry
   or replacement. Exercise staged-versus-returned failure cases separately.
4. Inspect path/label/route scale, all E/X reach, fresh duplication/reload,
   component readiness and cooked behavior. Source evidence is not native proof.

## Lesson and next task

Reuse complete exercises in an understandable course before adding more
unconnected props. Observe existing first-study facts through small read-only
interfaces, distinguish history from current completion, and retain uncertain
setup effects rather than spawning duplicates. Native acceptance stays queued;
continue substantial source work within the campaign deadline.
