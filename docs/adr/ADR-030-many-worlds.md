# ADR-030: Many worlds on one server

**Status:** Accepted
**Date:** 2026-10-11
**Deciders:** RicheyWorks
**Charter:** ADR-029, slice 1

## Question

Every route already said `/world/{id}/…`, but only `world-zero` existed: `WorldService` refused any
other id, and opened only a World Zero file. A multiverse needs worlds you can make, visit and leave.
What is the smallest change that mounts many, without touching how any one of them works?

## Decision

**1. A world is a `WorldService` with an id.** The service took no id; it now takes a `WorldId`
(World Zero by default, so every existing caller is unchanged), opens `<id>.daew`, and answers only
for its own id. Its sidecars (`.islands`, `.arks`, `.ecology`) follow the file name, so each world's
lane, fleet, ecology, claims and deeds are its own. Each world's ecology replays from its own seed;
World Zero keeps the one it always had.

**2. `WorldHub` mounts them.** World Zero is the Spring bean, always first. Every other world is its
own service on the same event stream, so its frames reach `/topic/world/<id>/…` with no change to the
STOMP layer. The registry (id, style, seed, title) is `worlds.registry` beside World Zero's file, and
worlds remount from it at boot. There are at most 16 worlds. The harbour clock now ties up arks and
steps ecology in every world.

**3. Controllers resolve the world from the route.** `WorldController`'s 49 calls go through
`world(id)`. An id that is not mounted resolves to World Zero's service, which answers null for any
id but its own, so every route keeps its exact 404. The old one-world constructors stay (tests and
the wallet use them) and wrap a one-world hub.

**4. Styles are named now, built one by one.** `WorldStyle` lists `SKY_ISLANDS`, `PARCELS`,
`BRICKS`, `GALLERY` and `LABYRINTH`, with a `ready` flag. Only sky islands are ready, and a request
for any other style answers `STYLE_NOT_READY` instead of making an empty world that pretends to be
one. A new sky-islands world is born with one island grown from its seed, so it is never an empty
sky.

| Route | Prod | Results |
|---|---|---|
| `GET /api/v1/worlds` | public | every world (id, style, seed, title, islands, revision) and every style with `ready` |
| `POST /api/v1/worlds` | required | CREATED, EXISTS, BAD_ID, BAD_TITLE, BAD_STYLE, STYLE_NOT_READY, FULL |

**5. The realm.** `realm.html?world=<id>` shows that world, and World Zero is the default. A
**Worlds** panel lists every world with **Visit** and "you are here", and a name plus a seed makes a
new one and moves you into it. The page title and header name the world, and a line lists the styles
still coming.

## Verified

- **Server, 5 tests:**
  - A new world grows its island.
  - Its cubes, lane, arks, claims and files stay apart from World Zero's.
  - Its frames carry its id.
  - It comes back after a restart, without being raised twice.
  - Every bad request is named, up to FULL at 16.
- **Browser:** a page names "Isle Two" with seed 42, lands in it (its own island and ark, "you are
  here"), leaves World Zero's lane unchanged, and visits back. No console errors; 59/59 harness
  checks with the wallet section on a local chain.
- **Gate:** green across all five modules, including the prod posture test probing both new routes.

## What the slice found

- **The harness's own restart left worlds behind.** It deleted `world-zero.daew*` only, so a second
  run found last run's `isle-two` and `worlds.registry`. Create answered EXISTS and the page rightly
  stayed put. The restart now clears every world.
- **A URL check expected the wrong URL.** "Visit" goes to `?world=world-zero`, but the check waited
  for a URL with no `world=` at all.
- The status line said "1 islands · 1 arks" as soon as a world had exactly one of each; it now
  counts properly.

## Held

- **Portals between worlds (ADR-031).** Today you travel with **Visit**; next you walk through a
  portal.
- **Per-world ownership of world creation.** Any signed-in caller may mount a world, up to 16. Who
  owns a world, and whether creating one is a mint, waits for the world registry contract
  (ADR-039).
