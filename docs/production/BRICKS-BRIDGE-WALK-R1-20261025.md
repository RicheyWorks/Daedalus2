# Bricks Walk Your Blueprint — edition 1, 25 October 2026

## Player slice and scope

Turn a solved tabletop Bridge blueprint into a separate low walkable model.
The original local builder can inspect its branches at avatar scale and visit
all nine numbered pads. This extends the building/play theme of ADR-034 and
Foreman Kip's bridge/tower context in REALM-CASTS.md. Its precise dimensions and
pad acknowledgements are original local creative practice, not a canonical
quest, structural test, reward or saved progress contract.

Base: `1b5ec52ec654ab82c9b391de9632c60162f124bf`.
Branch: `codex/bricks-bridge-walk-20261025-r1`.
Campaign deadline: **2026-10-26 06:56:50 UTC**.
Six new paths only: BridgeWalkCore.h, BridgeWalk.h/cpp, portable test/runner and
this handoff. Module Public/Private filenames begin `DaedalusBricksBridgeWalk`.
No existing source, Core, Workshop, Hero, movement, Obby, shared dispatch,
dialogue, inventory, Java, Build.cs, production source/assets or board change.
All earlier variants, commits, packets and originals remain intact.

## Explicit capture and usable model

SourceWorkshop defaults null/inactive. Bind a ready Bridge Workshop explicitly.
At a lectern on existing safe flat ground, a real standalone LocalPlayer uses
E/X to capture its CURRENT rule/mask. The existing core must report Complete:
all9 pads linked within the exact minimum-length allowance. An old first-study
flag is insufficient. Snapshot capture does not spend, reset, edit or claim the
source. A new actor is needed for a different capture; no hidden rebuild/reset.

The captured rule/mask/geometry is copied by value. Later source Undo, rule
selection, retargeting, destruction or streaming cannot retract or modify this
model. There is no source-readiness dependency after capture, no new file I/O,
profile/save system, multiplayer identity or economy behavior. Every pad visit
is actor-life information, with once-per-pad and once-all informational events.

Place the lectern upright at unit scale; yaw is allowed. The root must be the
exact native owned registered unattached WalkRoot. Provide clear safe ground
for the model, outside the protected obby/runway. It starts700cm ahead and200cm
to the left of the lectern.100cm represents one blueprint unit. Depending on
the plan, the footprint is590x490cm or490x590cm; the union of all possible R1
placements is local X[655,1245],Y[-245,345]. The lectern stays beyond normal E/X
reach of the deck; there are no new controls inside its walking footprint.

Nine90x90cm pads and only selected90cm-wide spans form the model. Beams are
trimmed exactly to pad faces. Some authored pad centres are100cm apart, so
those spans are10cm long;120cm pads would incorrectly overlap. All blocking
tops are coplanar at35cm, bottoms0. Decorative studs rise2cm without collision.
This is a low model on existing ground, with no pit, hazard, rescue hook, pawn
teleport, floor creation or movement/step-height changes. Safe placement and
actual step-up are native acceptance requirements, not a portable guarantee.

Twenty-one built-in simple BoxComponents are created once (9pads+12possible
spans); only captured selected pieces enable collision. There is no procedural
collision cook or navigation rebuild. The rendered procedural mesh has no
collision. New collision blocks Pawn only by default, generates no overlap
events and begins disabled. BeginPlay does not capture, enable a deck or sample
a player; null bindings remain inactive.

Before enabling collision, queries reject any pawn in each intended active-box
footprint. Configuration occurs with actor collision off. Exact box parent,
pose, dimensions and collision configuration are checked before and after the
final clearance query, then participant/readiness/physics state after enable.
Both clearance and actual geometry use the same frozen frame. No pawn is
nudged/teleported and no actor is removed to clear space.

After commitment, a0.05-second post-physics sampler checks the original actual
local controller/pawn, ground movement and CurrentFloor support on an exact
active owned box. Capsule feet must be finite, within4cm of decktop and within
35cm of a pad's centre on both axes. Ground below, airborne/foreign support,
beam centres and pad fringes cannot acknowledge a pad. Counter/labels/colour
update once per pad; all9 turns sampling off before its informational event.
Text is primary, colour supplementary. The original source remains editable.

**Nine pads visited does not prove the selected spans were traversed.** Safe
ground permits walking around, and short gaps can be bridged by a capsule. No
engineering safety, graph traversal, course speed or canonical completion claim
follows from visits. The core already validated the graph before model creation.

## Failure and preservation boundaries

Invalid/incomplete source, bad placement or occupied footprint before effects
refuses capture, preserving source and allowing a later deliberate attempt.
Once configuration begins, one attempt is fenced. Partial geometry/collision
effects remain visible for review on failure; no automatic retry, replacement
or rollback deletes them. Wording after collision enable acknowledges its
possible effect. Normal actor/component teardown touches no source or pawn.

Moved/reparented/reconfigured roots, boxes or model mesh, unavailable views,
changed builder/controller or missing physics state pause acknowledgements.
Existing captured data, geometry and visit bits remain. External movement of
the whole actor is not silently undone; the old frozen observation frame is
refused. Parent/pose guards prevent clearing one footprint then activating a
different one. Default component-reference arrays are Transient so an older
saved instance cannot override the current constructor's component list.

State commits before events, with lifetime/epoch checks around virtual player
and movement calls, collision activation and event publication. No reentrant
event can recapture/reset this model. Receipt/profile/commerce/land-ownership
interfaces are absent. No UHT/native build, editor or live staging was performed.

## Focused evidence

One guarded serial MSVC C++17 /W4 /WX run passed **13 groups,0failed** with
10.58GiB physical/36.94GiB commit headroom. It checks the three known complete
plans1011/1011/766; literal100cm coordinates;21stored/17active pieces; positive
extents, exact seams and no interior overlap; both short-span orientations;
capture refusal/atomicity; actual source-session scope ending without losing
the copied model; finite foot/edge/height/support bounds; and sticky9-bit visits.
The existing4096-subset Bridge solver oracle was not repeated.

Bounded native review corrected root and box attachment/geometry checks before
activation, so clearance tests and actual colliders cannot use different frames.
The source preflight initially found two constructor-array Transient omissions;
both were fixed, and a fresh final pass reported **0 errors in two native paths**.
Failure and final logs remain separate. No unaffected portable test was rerun.
One brief environment outage interrupted neither saved writes nor the completed
test; branch/files/log were reconciled after access returned, with no duplicate job.

A final API concern was resolved by bounded reads of installed UE5.8 source,
not by starting Unreal. `PrimitiveComponentPhysics.cpp:1569-1578` confirms the
component collision getter returns NoCollision when its actor is disabled.
Pre-activation therefore checks its exact own BodyInstance's configured mode
with the owner check disabled (`BodyInstance.h:1274`), including inactive links;
post-activation also checks effective mode and physics state. The exact public
GetBodyInstance API and CurrentFloor/physics-state predicates were inspected.
This avoids an always-refuse gate without allowing an uncleared inactive link
to activate. Final source-r3 preflight is0errors; peer delta found no remainder.
The packet keeps a concise API-source record and every earlier check log.

Native UHT/module compilation, actual Box physics creation, pawn overlap queries,
step-up, floor support timing, render/text/input, duplication/load and cooking
remain **UNCOMPILED / UNEXECUTED**. Portable geometry/visit predicates do not
execute those systems. Bricks Obby landing/rescue/health ordering remains a
separate **HOLD** and is neither modified nor proven by this slice.

Functional dependencies: Bridge `907c173008bf00d7a6b366003de60c1ca299f35a`
and the snapshot getter added by Print Press
`553e1dc3eaba25f08d97e4ad437189448f653003`. Skyline/Trail/Print ancestors may
be needed to apply their header patches cleanly; the Walker itself does not
use those actors or the print writer. Apply explicit patches/dependencies,
never blanket-replay the historical bundle or integrated mural changes.

Minimal acceptance for the sole native writer:

1. Isolated flat safe fixture outside obby/runway; bind solved/unsolved sources.
   Confirm null/startup inactive, current-completion gating and pawn occupancy
   refusal. Move a root/box during callbacks before activation: queries must
   not certify a different collision footprint. Partial effects stay on failure.
2. Capture once and verify exact pad/span dimensions,35cm blocking top, no extra
   collision/nav update, clear lectern approach, text/mesh matching collision,
   actual Hero step-up and seams for both100cm-spacing directions.
3. Walk all9 pads; test ground below, airborne, foreign floor and pad fringe.
   Check immutable visits and one-time events. Undo/change/end the source and
   confirm the captured geometry and visits stay. No reward/save changes.
4. Test controller/pawn/mesh/box/actor changes and teardown while standing on the
   low deck. Preserve captured facts; do not move the pawn or invoke rescue.
   Confirm duplicate/reload construction arrays, physics readiness and cooking.

## Lesson and next task

A tabletop graph can become a tangible player creation with a small opt-in
adapter. Keep collider extents and clearance in the exact same frame, check
ownership before activation, distinguish configured from effective engine
properties, and say what physical observations actually prove.
Next: continue a substantial non-island player feature within the campaign;
keep these focused native acceptance steps queued for their sole owner.
