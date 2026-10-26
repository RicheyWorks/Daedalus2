# ADR-031: Sky gates — portals in the clouds past the rainbow

**Status:** Accepted
**Date:** 2026-10-11
**Deciders:** RicheyWorks
**Charter:** ADR-029, slice 2
**Prompted by:** "portals won't be on the islands, you've got to get to them by airship. In the other
worlds they will be up in the sky and you have to take a helicopter or airplane or drone, or get a bird
to fly you, or a creature like that." · "they are in the clouds at the other side of the rainbow."

## Question

ADR-030 mounted many worlds, but you travelled between them by pressing **Visit**. A metaverse wants a
journey. How do worlds connect, so that the crossing is part of the game?

## Decision

**1. Gates are in the sky, out of reach on foot.** Gate *g* of a world stands on a gate row far past
the island lane, centred at `(48 + 96g, 72, −210)`. Its parts, in the order you meet them:
- a **rainbow**: six bands, violet inside and red outside, standing at `z = −170` with its feet in two
  small clouds; you fly through it to reach the gate
- a **cloud bank**
- a **crystal ring** holding a doorway of the new `PORTAL` cube
- a **sky berth**: a cloud shelf below the ring, where a mount ties up

Every cube is outside every island's claim box (those end at `z = −143`), so no one can build, claim
or walk there. The gate is real cubes: one plan, all or nothing like an island, with no randomness, so
every gate g in every world is identical. `RAINBOW_*` and `PORTAL` are appended cube types, and the
save format is unchanged for every existing cube.

**2. Gates come in pairs.** `POST /world/{id}/gates {toWorld}` builds one gate in each world, each
leading to the other, or builds neither. If the second gate fails, the first is taken down again.
Results: OPENED, SAME_WORLD, NO_SUCH_WORLD, ALREADY_LINKED, FULL. A world holds at most 8 gates. Links
persist as `<id>.daew.gates`, and every new gate sends one `GATE` revision frame.

**3. You need something that flies.** Each world style has a **mount** (`Mount.of(style)`):

| Style | Mount |
|---|---|
| Sky Islands | ark (ready) |
| Parcels | helicopter |
| Bricks | plane |
| Gallery City | drone |
| Labyrinth | sky-strider, a great rideable bird that knows the way over the walls |

Each mount is ready when its world's style is. For arks, a gate's cloud berth is just another place to
sail to: arks address it as slot `1000 + g`. Island slots stop at 63, so the fleet, voyages, saved fleet
rows and ark frames needed no new format. `VoyageRequest` takes `toGate` as well as `toSlot`, exactly
one of the two. Nothing lands or boards at a gate: there is no ecology in the clouds, and the hold
crosses intact.

**4. The crossing.** In the realm, every ark's **Sail** list includes "Gate → Isle Two".
1. Ride an ark to the gate. When it ties up at the cloud berth, you go through the doorway and the page
   opens the other world at `?arrive=<its gate>`.
2. On the far side you arrive at that world's gate, in its clouds and past its rainbow, and that world's
   ark is **hailed** up to meet you.
3. When it reaches the gate, it carries you down to its island.

The Worlds panel shows **Open gate** for any world not yet linked, and "gate open" once one exists.

## Verified

- **Core:** 5 tests.
  - The gate has all four parts.
  - The rainbow is between the islands and the ring, red outside and violet in.
  - The berth is open air over cloud.
  - The 8 gates never touch each other or any island's claim box.
  - Building is all or nothing, and each style's mount readiness matches the style's.
- **Server:** 5 tests.
  - A pair opens in both worlds as real `PORTAL` cubes, with one frame each.
  - An ark sails to the gate and ties up at the berth with its hold intact, then sails home.
  - Gates survive a restart.
  - Every bad request is named, including both destinations or none.
  - FULL leaves no half-built pair.
- **Browser, the whole journey:**
  1. On World Zero, **Open gate** to Isle Two draws the doorway and the rainbow.
  2. Ark-0 rides from Isle 1 through the rainbow to the gate.
  3. The page crosses to Isle Two.
  4. Isle Two's Rose Kite is hailed up to its gate, meets you, and sails for its island.

  The harness is 65/65 with the wallet section on a local chain, five runs in a row.

## What the slice found

- **The crossing and the hail fought each other.** On the far side the hailed ark is also the ark you
  ride, so when it reached the gate the crossing rule fired and sent you straight back. The hail is now
  handled first.
- **A check raced a slow page.** "Hailed" was set on arrival and cleared when the ark reached the gate
  about 15 seconds later; a slow first render under software WebGL could miss the window. The page now
  keeps `lastHail` as a record, and the check reads that. The meeting itself never failed.
- **A wallet address overflowed the island panel.** "owned by 0x7099…" ran past the panel's edge in the
  gate screenshot; addresses now show short (`0x7099…79c8`) wherever an owner or builder is named.
  The first version of that helper was called `who`, which `writeBlock` already used for a local
  variable. Inside `writeBlock`, the "Isle 1 belongs to alice" message called a string and threw, so a
  refused cube rolled back without saying why. The harness failed twice in a row on it; the helper is
  now `shortName`.
- **The fresh-page check hard-coded where ark-0 should be** (Isle 1). The gate journey legitimately
  moves it, so the check now compares the page with the server.

## Held

- The other mounts, with their worlds (ADR-033..036). They are modelled in Blender and drawn in the
  realm and in Unreal (ADR-029, Engines).
- Gates on chain: a portal recorded as a link between two deeds when both owners sign (ADR-040).
