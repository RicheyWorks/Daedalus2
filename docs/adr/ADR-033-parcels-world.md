# ADR-033: Parcels — a district of plots, and a helicopter to the clouds

**Status:** Accepted
**Date:** 2026-10-11
**Deciders:** RicheyWorks
**Charter:** ADR-029, slice 4
**Prompted by:** "a true metaverse … the Minecraft or Sandbox look, it also will have the Decentraland
look …" · "in the other worlds they [the portals] will be up in the sky and you have to take a helicopter
or airplane or drone …"

## Question

ADR-030 named five world styles, but only Sky Islands could be made. Decentraland's look is a flat,
walkable city cut into square parcels of land that people own and build on, with streets and a plaza
between them. What is the least that makes a real Parcels world here: one you can claim land in, build
on and fly out of, with the same cubes, claims and gates as the islands?

## Decision

**1. One district layout, the same in every Parcels world.**
`DistrictOps` (core) lays out:
- 4 × 4 city blocks, each 2 × 2 plots of 16 × 16 cubes, so 8 × 8 plots in all
- 4-wide streets between the blocks, a ring road around them, and a sidewalk on each street edge
  that faces a plot
- the plaza: the four heart plots plus the crossing between them, 36 × 36 of paving with a helipad at
  its centre

That makes 148 × 148 cubes and **60 claimable plots**, numbered `n = row × 8 + column`. The ground is
three deep with its surface at y = 0: grass, then dirt, then stone. The plaza's centre falls on x = 48,
gate 0's line, so the flight to the clouds goes straight down −Z.

Three cube types are appended, and every existing ordinal is unchanged:
- `ROAD` (asphalt)
- `PAVING` (sidewalks and plaza)
- `HELIPAD` (the pad's orange)

**2. The seed decides the show plots, and only those.**
About half of the plots open as bare lawn. The rest open with a grove, a glass pavilion, a stone and
glass tower, a crystal sculpture or a pond. Each plot uses its own `SplittableRandom(seed·1000003 + n)`.
A plot's contents never leave its footprint and never pass the **height limit (y = 32)**. The gates'
rainbows start at y = 55, so nothing anyone builds can reach a gate. Every Parcels world has the same
plots in the same places; the seed changes only what stands on them.

**3. Land works like Decentraland: you build only on what you hold.**
`WorldService` runs in district mode for a Parcels world. The hub sets this on every mount, so it
survives a restart.
- **The rule.** A cube may change only inside a claimed plot's parcel. Writes to a street, the plaza,
  an unclaimed plot or anything above y = 32 come back `DENIED`.
- **Claims.** These use the same routes and code as island claims (ADR-026): `/islands/{n}/claim`,
  `/abandon` and `/builders`. Only the claim box changes, to the plot's footprint from the ground to
  the limit. Unknown plots, and the plaza's four numbers, answer `NO_SUCH_PLOT`. Raising an island
  answers `WRONG_STYLE`.
- **`GET /world/{id}/plots`** lists the 60 plots: footprint, height, what each opened with, owner and
  builders. It also gives the plaza and the pad.

**4. The helicopter (the Parcels mount, ADR-031).**
Each Parcels world has one vessel, `heli-0`, whose home is the helipad (`PAD_SLOT = 2000`, past the
islands' 0..63 and the gates' 1000..1007). It is an ark to the fleet, so voyages, clocks, STOMP frames
and persistence all come for free. It just carries no animals. `VoyageRequest` gains `toHome`, which
means "back to your island, or to the pad", alongside `toSlot` and `toGate`. `Mount.HELICOPTER` and
`WorldStyle.PARCELS` are now `ready`.

**5. The realm (`realm.html`).**
- **Worlds panel.** A style picker. Choosing "Parcels" creates a district and lands you on the plaza.
- **Plot map.** "Island lane" becomes an 8 × 8 plot map: plaza cells in pale stone, open plots green,
  others' plots brown, yours in gold. Tap a plot to fly over it and see its owner row
  (Claim / Let build / Give up).
- **Refusals.** A refused cube says why: "Streets and the plaza are for everyone", "Plots are built up
  to 32 high", "Claim Plot 10 to build on it", or "Plot 9 belongs to carol".
- **The helicopter.** Built from boxes like the creatures, with spinning main and tail rotors. It sits
  on the pad and flies with **Fly**, with "Helipad" or a gate as its destination. Ride it through the
  rainbow and you cross into the next world.

**6. Engines.** The World Package manifest (ADR-032) gains `plots`, giving each plot's footprint, show
and owner. The Unreal import script reports plots. The C++ mesher needed no change: the palette is data.

## What it found

- **Every page load in a world with a gate sent an ark to gate 0 (an ADR-031 bug).** The arrival code
  read `Number(params.get("arrive"))`, and `Number(null)` is `0`, so a page with no `?arrive` "arrived
  through gate 0". It hailed an ark up there every time it opened. The new Parcels section exposed it:
  World Zero's two arks both ended up moored at gate 0 when nobody had sent them. The server log showed
  a voyage POST eleven seconds after each plain page load. The fix: only a page with
  `?arrive=<digits>` hails anything. The harness now records every ark's `departAt` before a fresh page
  opens and checks that nothing moved after it.
- **A rider who never got off.** Page A rode ark-0 in the voyage section and never pressed Stop. When
  the Sky gates section later sent ark-0 to the gate, page A went through the gate with it, as a rider
  should. Two pages then arrived in Isle Two at once, both hailed its one ark, and whichever came second
  found none free. In one run of four this made "Isle Two's ark is hailed" fail. The page behaved
  correctly; the harness had left a passenger aboard. The harness now steps off, with a "Stop ends the
  ride" check. The realm also now hails before the creatures load, not after, so a traveller is met
  seconds sooner. The gate view still wins over the default island view.
- **A probe that logged errors.** The page first found out whether it was in a Parcels world by asking
  for `/plots` and treating a 404 as "no". The browser counts that 404 as a console error, so it failed
  the "no console errors" check on every page. The page now reads its style from `/worlds` and asks for
  `/plots` only in a Parcels world.
- **A claim on the plaza was a 400.** `claimView` asked for the plaza's box, and `plotBounds` throws for
  a plaza number. `claimOf` now checks `claimable` first, so the answer is `NO_SUCH_PLOT`.
- **A world created after boot ran on the wall clock.** A test that mounted a world after setup could
  not move that world's clock. This is a fixture lesson rather than a product bug: the test now gives
  the new world the test clock too.
- **`TreeMap(Map)` ignores the source's comparator** and sorts naturally, which `BlockCoordinate` does
  not support. The plan now copies into a `TreeMap` built with the district's own comparator.
- **SpotBugs: a dead array** (`UC_USELESS_OBJECT`). Removed.

## Numbers

- **District:** 148 × 148 cubes, 60 plots, a 36 × 36 plaza and a 10 × 10 pad. Across 20 seeds, every
  cube is within y −2..32, and every cube above ground belongs to a plot. Lawns made up between 40% and
  56% of 1,800 plot draws, and all six show kinds appeared. All 8 gates still fit over a built district.
- **Java tests:**
  - `DistrictOpsTest`: 6
  - `ParcelsWorldTest`: 4 (born with the district; ownership, height, streets and plaza; the
    helicopter to a gate and home; everything after a restart)
  - Updated: `WorldsControllerTest` (PARCELS is ready; BRICKS is the not-ready case), `GateOpsTest`
    (the HELICOPTER mount), `WorldCoordinatesTest` (ordinals 21–23)
  - The posture test now covers `GET /plots`.
- **Browser harness: a new "Parcels" section.**
  - create a Parcels world from the form
  - plot map with 64 cells, 4 of them plaza; pad, road, helicopter and rotor all present
  - claim plot 9 from the map
  - build on it; the street, above the limit and plot 10 each refuse with their reason
  - **Fly** lifts the helicopter off the pad, it carries you through the rainbow to World Zero, and
    World Zero hails an ark to that gate

  Plus the new "opening a page hails no ark" and "Stop ends the ride" checks. Two consecutive runs on
  fresh servers: 79/79 and 79/79.
- **C++ parity:** 52/52 against the new fixture (three new types in the palette).

## Held

- **Smooth low-poly rendering of the Parcels style** (Decentraland's look rather than cubes). The data
  is unchanged: a renderer choice per style. Held until the first Unreal run (ADR-032) shows which
  engine should own the look.
- **Plot deeds on chain.** The deed contract (ADR-028) covers islands. Plots move to the chain with
  ADR-039, when the realm follows the chain and the world registry contract exists.
- **Maze stamps inside plots.** Stamping still uses its own parcel rules. ADR-036 brings mazes to every
  world.
- **More than one district, or estates (adjacent plots under one owner).** Held until someone owns
  20 plots.
