# ADR-035: Gallery City — streets, parcels, and galleries of maze art

**Status:** Accepted
**Date:** 2026-10-11
**Deciders:** RicheyWorks
**Charter:** ADR-029, slice 6
**Prompted by:** "… and also portal how Cryptovoxels' world looks …" · later, about the art: "they use
this to help them make it through the 3D mazes we make in each world."

## Question

Cryptovoxels is a city: a street grid, parcels of different sizes and heights, and above all
galleries, with art on the walls. What does a Gallery City need here? And what art does it hang, given
that nothing in it may come from outside the server?

## Decision

**1. The city, the same in every Gallery City.**
`GalleryOps` (core) lays out:
- 5 × 5 blocks of 24 × 24 cubes, with 6-wide streets between them, so 156 × 156 cubes in all
- The middle block is **the Origin**: a plaza with a drone pad on gate 0's line and a crystal spire.
- Each of the other 24 blocks is cut by a fixed pattern into four squares, two wide halves or two deep
  halves. That gives **68 parcels**, each with an **address on its nearest street** ("1 Ash Lane").
- Twelve named streets: avenues run north–south (Ash Lane, Pixel Street, Origin Way, Gallery Row,
  Voxel Avenue, Frame Road), streets run east–west (North Rim … South Rim). Their names float over the
  roads.
- **Height limits fall away from downtown:** the inner ring of blocks builds to y 32, the outskirts to
  y 20. The gates' rainbows start at y 55, so they stay a flight away.

**2. Parcels work like Parcels' plots (ADR-033).**
Same claim routes and code. `WorldService`'s claim box, slot list and build rule now switch on the
world's style. Parcels and Gallery City both build only inside a claimed parcel; an unknown parcel
answers `NO_SUCH_PARCEL`.

**3. Galleries, and the art in them.**
- **Galleries.** The seed opens about two parcels in five as a white gallery: a glass roof, a glass
  front facing the street with a door, and a frame on each of the other three inner walls.
- **The art is Daedalus' own mazes.** `MazeArt` takes a seed and from it picks one of nine generators
  (Prim's, Kruskal's, Wilson's, Eller's, Sidewinder, Binary Tree, Hunt-and-Kill, Aldous–Broder,
  recursive backtracker) and a palette. It draws the maze, and runs its solution through it as a
  rainbow from start to goal.
- **A seed is a picture.** The same seed gives the same PNG, byte for byte, so a frame stores only its
  seed. The title reads like a numbered print: "Kruskal's (randomized) No. 80282555".
- **Seeds run 0..999,999,999.** That is a number a person can read off a frame, and it stays exact in
  JavaScript (see below).
- **Nothing comes from outside.** The realm only ever loads `/api/v1/art/maze/{seed}.png` from its own
  server: no third-party images, no tracking pixels, nothing to moderate.

**4. Hanging your own.**
On a parcel you hold, or can build on, choose a seed (with a live preview), a size (2 × 2 to 5 × 4)
and a title, press **Hang art**, and tap a wall.
- **The server checks** that:
  - every wall cube is on one parcel you may build on
  - the wall is solid and opaque behind the frame, with open air in front
  - no other frame covers that face
  - the parcel has fewer than 16 frames
- **Results:** `HUNG`, `NOT_YOURS`, `NO_WALL`, `OVERLAP`, `FULL`.
- **Storage.** Frames persist in `<world>.daew.art`. A frame whose wall is broken, or whose front is
  built over, is not shown, and it comes back if the wall does.
- **Taking a frame down.** Whoever hung it can, and so can whoever now holds its parcel. The galleries'
  own art stays.

**5. Looking.**
- **Tap a frame** in Look mode: the viewer opens with the picture, its generator, seed, size, address
  and who hung it, plus Take down if it is yours.
- **Tap the ground:** the parcel under it is selected, with its address, size, height limit, owner and
  claim actions.
- **STOMP.** An `ART` frame redraws the walls on every page.

**6. The drone (the Gallery mount).** `drone-0` rests on the Origin pad: a white quadcopter of boxes,
with four rotors that spin in opposite directions and a camera. It flies to the gates like the other
aircraft. `Mount.DRONE` and `WorldStyle.GALLERY` are now `ready`, so only the Labyrinth is still to come.

**7. Engines.** The World Package manifest gains `art`: every frame's wall corner, facing, size, seed,
title and image. Gallery parcels go into `plots`, marked GALLERY or OPEN. Unreal can hang the same
frames.

## What it found

- **Seeds bigger than JavaScript can hold.** The first galleries used `rng.nextLong()` seeds such as
  -2392556344624324169. JSON delivers that number to a page, and the page rounds it, because a JS number
  is exact only to 2^53. A frame hung "with the same seed" from the browser would have shown a different
  maze. Seeds are now 0..999,999,999, enforced by `HangArtRequest` (`@Max`).
- **A claim the panel didn't see.** The realm read the parcel list once, at load. A claim from the panel
  succeeded on the server, but the panel still said "open", and the browser check caught it. The panel
  now reads `/gallery` again on every claim frame.
- **Taps on a busy page.** In the full run, with six pages open, a tap sometimes landed on a camera view
  that had not been drawn yet. The page's `lookAt` and `project` helpers now refresh the camera's
  matrices themselves, and the harness brings the page forward and re-taps (at most three times) the way
  a person would. One run in four had failed this way; the next six sections were clean.
- **SpotBugs, twice.** First, `x % 2 == 1` is wrong for negative numbers; tile indices are never
  negative, but it now reads `!= 0`. Second, the cached parcel list was returned directly; it is
  immutable, and is now passed through `List.copyOf`.

## Numbers

- **City:** 156 × 156 cubes, 68 parcels on 12 streets, about 40% galleries (between 30% and 50%
  across 12 seeds × 68 parcels).
- **Art:** 90 frames in a seed-3 city. Every gallery frame really hangs on a wall with air in front of
  it, inside its parcel, across 12 seeds. All 9 generators appear within 120 seeds, and every solution
  crosses the maze (at least 29 cells).
- **Java tests:**
  - `GalleryOpsTest`: 4
  - `MazeArtTest`: 3
  - `GalleryCityTest`: 4 (born with streets, parcels, art and a drone, with the PNG matching
    `MazeArt`; only holders build, under their height; hanging, refusals, overlap, the other face,
    taking down; surviving a restart, and vanishing then returning with the wall)
  - Updated: `WorldsControllerTest` (LABYRINTH is the last not-ready style), `GateOpsTest`
  - The posture test now covers 5 more routes.
- **Browser harness: a new "Gallery City" section.**
  - a city made from the form: 90 frames, all 90 textures loaded, 68 parcels, 12 streets, the drone
    and its rotors, the white palette
  - a tap on a frame opens the viewer with the right title and no Take down
  - a tap on the ground picks the parcel, and Claim makes it dora's
  - building a wall, then Hang art and a tap on the wall, hangs seed 77 there for everyone

  Two consecutive full runs on fresh servers: 92/92 and 92/92.

## Held

- **Cropping non-square frames.** A 3 × 2 frame stretches the square picture. Held until frames show
  more than mazes, which will need their own aspect ratios.
- **Art on chain** (ADR-045), and **a frame's maze as a walkable maze.** In ADR-039 the same seed builds
  the 3D maze whose solution the picture shows, so a gallery's art is the map to a dungeon, as
  RicheyWorks described.
