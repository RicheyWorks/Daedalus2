# ADR-026: Island ownership

**Status:** Accepted
**Date:** 2026-10-10
**Deciders:** RicheyWorks
**Prompted by:** the metaverse plan, "land ownership" in the ADR-018 graft map, built on the
parcels World Zero already has, before any token touches it.

## Question

Every island is open: anyone can change any cube. A Sandbox-style world needs land that is
yours. What does owning an island mean, who decides who you are, and how do others get to build
on it?

## Decision

**1. A claim is a World Zero parcel.** Claiming slot *k* registers one parcel over
`IslandOps.claimBounds(k)`: the column of sky the island can reach, 47 cubes either side of the
slot centre (one short of halfway to each neighbour) and from 48 below the lane to 47 above. Every
cube of the largest island (radius 28) fits; `IslandClaimTest` checks four seeds cube by cube. No
cube is placed and the terrain is untouched. `World.claimParcel` refuses overlap atomically, as
`applyStamp` does. The DAEW file already stores parcels and their ACLs, so claims and builders
survive a restart with no new sidecar.

**2. The existing gate does the work.** Block place and remove already pass through
`World.may(actor, BLOCK_PLACE, at)`. Open ground allows anyone. Inside a parcel, the owner is
allowed, a listed deny wins, and others need a grant. An anonymous write counts as the `system`
owner, so it is refused on a claimed island. `system` itself cannot claim.

**3. Who you are.** On a secured server, the signed-in user is the actor for claims and block
writes, and a body `actorId` is ignored. Before this slice, an authenticated caller could write
`"actorId":"alice"` and act as alice. With land at stake, that stops here. An open dev server
still takes the caller's word, as it always has, and the realm gives a dev player a name field.

**4. Routes.**

| Route | Prod | Results |
|---|---|---|
| `POST /islands/{slot}/claim` | required | CLAIMED, ALREADY_CLAIMED, BLOCKED, BAD_OWNER, NO_SUCH_ISLAND |
| `POST /islands/{slot}/abandon` | required | ABANDONED, NOT_OWNER, NOT_CLAIMED, NO_SUCH_ISLAND |
| `POST /islands/{slot}/builders` | required | GRANTED, REVOKED, NOT_OWNER, NOT_CLAIMED, BAD_BUILDER, NO_SUCH_ISLAND |
| `GET /islands` | public | each row gains `owner` ("" when open) and `builders` |

Each change emits one `WORLD_REVISION_CHANGED` frame typed `CLAIM`, and every page re-reads the
lane. Abandoning drops the parcel together with its grants, so a later owner inherits no builders.

**5. The realm.** A name field (locked to your account when signed in). Each island shows "open —
anyone may build", "yours" or "owned by alice". **Claim** appears on open islands. On your own
island there is a builder field, **Let build**, a chip per builder to revoke them, and **Give up**.
A refused cube rolls back with "Isle 1 belongs to alice".

## What the slice found

- **The generic parcel ACL routes would have undone ownership.** `/parcels/grant`, `deny`,
  `revoke` and `forgive` act on whatever parcel sits under a coordinate and never ask who is
  calling. With island claims, anyone could have granted themselves the owner's rights, denied the
  owner (a deny beats even the owner), or revoked the owner's builders. Inside a claimed island they
  now answer `NO_PARCEL`; islands answer to their own routes, which check the owner. A test tries
  all four back doors. For World Zero's own plots these routes stay as they were. **Held, with a
  trigger:** giving them a caller check is the next slice that touches World Zero's well.
- **Creatures could be placed into half-loaded terrain.** `loadWorld` set the revision before its
  chunks arrived, so a landing frame mid-load could scan and cache an island under the final
  revision with chunks missing. One run of 5 put a body inside terrain. Creature placement now
  waits for world loads and redraws when one finishes. The cause is inferred from the code; the
  flake did not recur in 6 runs before or after.
- World Zero's fixtures do not overlap any lane box: slot 0 claims cleanly in every test.

## Held

- Tokens: an ERC-721 per island whose metadata is the seed (ADR-027), and a wallet sign-in
  provider (ADR-028), which would make `owner` an address the chain agrees on.
- Selling, renting and transferring islands: the parcel lease fields exist, and a market provider
  plugs in on top of them.
