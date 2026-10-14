# Labyrinth route lesson v1 — UNVALIDATED, source only

Source baseline: `origin/main e8d9aac382731bd02965e150aa821ace3b7420cb`.
This implements the first-route mechanic in
[`LABYRINTH-BUILDOUT.md`](../../realms/LABYRINTH-BUILDOUT.md): mark three
deliberate turns, return to the lectern, and keep earned credit when a Chalk
Eater erases a mark. It preserves the existing `ChalkTrail` expenditure order.
The wider Broken Survey story, folding walls and friendly plants are unchanged.

## Java authority and save extension

`LabyrinthRouteSession` is one player in one specific maze instance. Bind the
authenticated player ID and canonical realm `LABYRINTH`; catalog `labyrinth`
and server storage world IDs are separate namespaces. The instance ID must
identify the actual maze generation, not merely a reusable level name.

Each host command carries an event ID and expected revision. Only applied
events advance revision. Exact retries remain harmless after later events or
restoration; an ID with a changed action, point or expected revision is refused.
Identity is checked before replay lookup. Refusals spend nothing. Applied IDs
are never evicted, and the 512-event cap reserves space for remaining lesson
turns, any erasures needed to free a small trail, and the return, so optional
exploration cannot exhaust completion space.

The host verifies a real deliberate turn before `markTurn`, an approved world
erasure before `erase`, and the actual lectern interaction before
`returnToLectern`. A coordinate alone does not prove any of these facts.
Re-marking an erased point spends chalk again but never creates another
distinct lesson turn. Completion requires a separate return event, not merely
the third mark. Completed lessons still permit bounded route marking.

`LabyrinthRouteSnapshot` is immutable schema 1 data for the existing host save
transaction. It retains original supply and all applied events; restore
replays them once to recover remaining charges, live marks and lesson credit.
It validates schema, identity, bounds, event uniqueness/order and transitions.
Restore a temporary session and publish it only after successful validation.
The snapshot is not signed: only trusted host saves may supply it.

The initial charge batch must be reserved/debited through existing authoritative
inventory transaction code exactly once, or marks must be debited in the same
save transaction as each accepted mark. Do not combine both models. A view is
not an inventory balance. This source provides no new inventory ledger,
top-ups, reward award, filesystem store or HTTP endpoint. The host must
acknowledge only after the save/inventory transaction commits. Keep the prior
session/save on failure and reuse the original event ID for a retry.

## Opt-in native boundary

`UDaedalusLabyrinthRouteComponent` belongs on an explicitly selected owned,
replicated pawn. Existing Hero/Realm/Inventory/DCS files are untouched. On the
authority, bind the player/instance and grid frame, then apply committed Java
views. The component refuses wrong identities, old revisions, conflicting
same-revision views, increasing charges and regressing lesson credit. Clear
the binding on realm departure or unpossession before mounting another maze;
this clears presentation, not the host save.

The component emits `MARK_TURN`/`RETURN_TO_LECTERN` intentions through
`OnRouteIntent`. It adds no client mutation RPC or Java network transport.
Connect intents to the existing authenticated host action seam, validate
ownership and observations there, then send back the committed view.
Preserve the original intent on retry. The existing generic inventory `USE`
path subtracts immediately; do not route chalk through it and debit again here.

Native `FIntPoint.X/Y` represent Java `x/z`. The host defines origin/yaw and cell
size; the 400 cm default follows the delivered 4 m maze modules. Input radius
and marker scale/lift are proposed usability/presentation choices, not approved
balance. Marks use an optional existing mesh/material, remain anchored to the
grid rather than the moving pawn, and do not collide or alter navigation.
Only the locally controlled owner draws its marks. Owner-only replication
requires the existing pawn ownership/replication setup. Marker meshes also use
per-view owner visibility for split-screen. Controller changes refresh local
presentation and clear old ownership; bind the host after possession changes.

## Deferred verification and adoption

No tests, builds, CI run, editor actions, native deployment or service activation
were performed for this source sprint. Source review is not runtime proof.
The agreed sole-operator editor slot is the later production validation: bind a
real committed host session, place three observed turns, erase one, return,
save/reload, leave/re-enter, and observe owner-only replication and markers.
Actual inventory atomicity, transport binding, actor lifecycle, reflection/
compilation, cue appearance and multiplayer delivery remain unvalidated.
No claim of a playable or completed Labyrinth follows from this PR.
