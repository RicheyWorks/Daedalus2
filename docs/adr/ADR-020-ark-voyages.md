# ADR-020: Ark voyages

**Status:** Accepted
**Date:** 2026-10-10
**Deciders:** RicheyWorks

## Question

ADR-019 moored an ark at every island. The story needs them to fly: after the Shattering, arks carry
animals between islands. What is the smallest honest model of a voyage that every client agrees on,
survives a restart, and that the ecology (ADR-021+) can hook an arrival to?

## Decision

**A voyage is two timestamps, not a stream of positions.** `Voyage(arkId, fromSlot, toSlot, departAt,
arriveAt)` in server epoch milliseconds. Duration = `HARBOUR_MS` (4 s to cast off and tie up) + berth
distance ÷ `SPEED` (12 cubes/s) — a neighbour 96 cubes away is about 12 s. The server never ticks a
position; a client places the ark from `progress(now)` on its own curve: a smoothstep along the line
between the two moorings plus `sin(πt)·16` cubes of climb, turning to face the destination while
casting off and back to the berth heading while tying up. `GET /arks` returns the server clock (`now`)
so every client animates on server time, not its own.

**`ArkFleet` is pure and clock-free** (core). Every method takes `now`; a test drives time, the
server passes its clock. Only arks that have left home are rows. Orders are named, never silent:
`SAILING`, `ALREADY_THERE`, `UNDERWAY` (one voyage at a time), `NO_SUCH_ISLAND`.

**Arrival is announced by the harbour, not by the next reader.** `ArkHarbor` is one daemon thread on a
250 ms delay that calls `WorldService.settleArrivals` — so the `ARRIVED` frame leaves when the ark
arrives. Reads also settle first, so a stopped harbour can never make the API lie.

**Events go on their own topic.** `ArkVoyageEvent` (plugin API, `DEPARTED`/`ARRIVED`) →
`/topic/world/{id}/arks` as `ArkFrame`. The cube-shaped world frame is untouched. Plugins may listen:
an arrival is the moment colonists land (ADR-023).

**The fleet persists beside the lane.** `world-zero.daew.arks`: `arkId slot [from to depart arrive]`,
written atomically on every departure and arrival. A voyage in the air during a restart is still in
the air after it, and lands on time.

**`POST /world/{id}/arks/{arkId}/voyage`** (authenticated, `VoyageRequest{toSlot}`; unknown ark → 404
`ark`). README table, `ProdAuthPostureTest` together.

**Realm.** Each ark row has a destination picker, Sail and Ride. Ride makes the ark own the camera: the
camera snaps to a chase view once, then moves only by the ark's motion, so the rider can still orbit it.

## What it found

- **A late fly-to stranded the rider.** Raising an island ends with a fly-to; the island's STOMP frame
  reloads the lane faster than the raise's own request returns. The harness saw the island via the
  frame, sailed, rode — and then the raise's fly-to landed 101 cubes away and the follow kept the
  offset. Fix: while riding, fly-to is a no-op; every fly-to carries a flight number so a stale one
  stops itself; the island Go button ends a ride first.
- **A background tab gets no animation frames.** The harness's ride check first failed because page A
  was not the front tab; that was the harness, not the realm. It now brings A forward.
- **The break tap grazed a cube edge again** after the scene changed. The harness now aims at the
  projected centre of the cube it means (`state.project`), as a player would.

## Verified

Core `ArkFleetTest` (sail, settle once, named refusals, restart mid-voyage, bad rows). Server: a full
voyage on an injected clock (DEPARTED then exactly one ARRIVED, UNDERWAY mid-flight, ALREADY_THERE
after), restart mid-voyage then arrival, named and 400/404 refusals. Browser: A raises a second island,
sails ark-0, B hears DEPARTED, B's model moves toward the destination, A's ride camera stays on the
ark (0.00 cubes), B hears ARRIVED and moors the model off Isle 1's pier, the server agrees, and a fresh
page knows where every ark is.

## Held

- Cargo: arrivals carry nothing yet. ADR-023 (stowaways) makes them carry colonists.
- One voyage per ark at a time; no queued itineraries.
