# ADR-034: Bricks — a studded baseplate, an obby, a plane, and an avatar you play as

**Status:** Accepted
**Date:** 2026-10-11
**Deciders:** RicheyWorks
**Charter:** ADR-029, slice 5
**Prompted by:** "… the Decentraland look and the Roblox look …" · "in the other worlds [the portals]
will be up in the sky and you have to take a helicopter or airplane …"

## Question

A Roblox world is a grey studded baseplate, bright bricks, a spawn pad and an obby: a course of floating
platforms over lava that you run and jump through as a blocky avatar. The realm had no avatar at all;
you only flew the camera. What is the least that makes a Bricks world something you actually play?

## Decision

**1. The ground, the same in every Bricks world.**
`BricksOps` (core) lays out a 128 × 128 baseplate, two cubes thick with its top at y = 0, and puts on it:
- **a spawn pad**
- **a runway** on gate 0's line (white, with a yellow centre line), where the world's plane rests
- **an obby** along the plate's west side: 18 floating bricks of red, blue, green and yellow over a lava
  floor. Every sixth brick is a checkpoint, the last one included. A 6 × 6 gold finish with a trophy
  ends the run.

The seed changes only the obby. Eight cube types are appended: `BASEPLATE`, `BRICK_RED`, `BRICK_BLUE`,
`BRICK_YELLOW`, `BRICK_GREEN`, `BRICK_WHITE`, `SPAWN` and `LAVA`. Every older ordinal stays where it
was, and the ordinal test pins them.

**2. The obby is always beatable, and a test proves it.**
Every jump stays inside the avatar's reach: at most 2 cubes of air straight ahead, or √5 with one step
to the side, and never more than one cube up. Each landing has two cubes of headroom. `BricksOpsTest`
checks this for every platform, finish included, across 200 seeds. The generator also keeps
side-steps short after a long gap, so it cannot drift into an impossible course.

**3. A sandbox with three things kept safe.**
Anyone builds anywhere on the open plate, up to y = 48. These stay as they are:
- the baseplate itself
- the obby corridor, with its spawn
- the runway and the air over it

Off the plate there is nothing to build on, so the gates' rainbows (y ≥ 55) stay a flight away.
`WorldService` now carries the world's **style**, not a Parcels flag. The style decides the build
rule, the home of the world's aircraft and its name.

**4. The plane (the Bricks mount, ADR-031).**
`plane-0` rests on the runway at `Mount.HOME_SLOT`, the slot a world's own aircraft calls home. The
helicopter (ADR-033) now uses the same slot. It is an ark to the fleet, so voyages, `toHome`, STOMP
frames and persistence all come free. `Mount.PLANE` and `WorldStyle.BRICKS` are now `ready`.

**5. Play mode, in every world.**
The realm gains **Play** (P) next to Look, Build and Break, with a blocky R6-style avatar: yellow head
and arms, blue torso, green legs that swing as it runs.
- **Controls.** WASD or the arrows and Space on a keyboard. On a tablet, an on-screen stick and a Jump
  button.
- **Physics.** Fixed steps of 1/120 s, with axis-by-axis collision against the cubes. Water, clouds,
  portals and rainbows don't block you. There is no auto-step: a cube up is a jump.
- **Camera.** It follows the avatar, and the player can still orbit around it.
- **Where you start.** On the spawn in a Bricks world, by the helipad in a Parcels world, and on top of
  the first island elsewhere.
- **The obby is live in a Bricks world.**
  - Lava, or falling off the world, sends you back to your last checkpoint.
  - Reaching a checkpoint says so.
  - The gold finish stops the clock ("Obby complete! 7.0 s, 1 fall in the lava"), and the Obby panel
    keeps your best time.

**6. The look.**
The top faces of baseplate and brick cubes wear a stud. It is drawn once on a canvas and multiplied by
each cube's colour. Only the faces move between meshes, so the realm draws exactly the triangles the
World Package exports, and the harness still checks that. The plane is built from boxes, like the
helicopter, with a spinning propeller.

**7. Engines.** `GET /world/{id}/obby` gives the spawn, the platforms in order, the finish, the lava
level, the build height and the runway. The World Package manifest gains `obby`, so an Unreal level can
rebuild the same run. The Unreal import script reports it.

## What it found

- **A test whose unknown cube became known.** `anUnknownBlockTypeNamesEveryKnownOne` used `"lava"` as
  its example of an unknown cube type. ADR-034 made it a real one, so the test now asks for `plasma`. It
  was right about the error message and wrong about which words would stay unknown.
- **Physics on a starved page.** In a busy harness run, the new page got one animation frame in 0.7 s.
  The walk advanced exactly 0.25 s × 6 = 1.5 cubes, the per-frame cap at the time. The page is now
  brought to the front before play, as the voyage section already did. The cap is 0.5 s, so a stall
  still never teleports anyone.
- **The probe was right the first time.** In a standalone browser probe, walking, the lava death, the
  checkpoint respawn and the running jump onto the finish all worked on the first run. The 200-seed
  beatability test passed on its first run too.

## Numbers

- **Plate:** 128 × 128. **Obby:** 18 bricks, 3 checkpoints, finish at y ≈ 13–20.
  Across 200 seeds: every jump ≤ √5 cubes of air and ≤ 1 up, with two cubes of headroom on every landing.
- **Java tests:**
  - `BricksOpsTest`: 5
  - `BricksWorldTest`: 4 (born with the playground, and the obby endpoint matches the cubes; the
    sandbox and the safe zones; the plane to a gate and home; the rules after a restart)
  - Updated: `WorldsControllerTest` (BRICKS is ready; GALLERY is the not-ready case), `GateOpsTest`,
    `WorldCoordinatesTest` (ordinals 24–31), `WorldRealmControllerTest`
  - The posture test now covers `GET /obby`.
- **Browser harness: a new "Bricks" section.**
  - a Bricks world made from the form: studs, spawn, lava, plane and propeller, brick palette
  - building on the plate is allowed; the obby and anything above the limit refuse, with reasons
  - Play puts the avatar on the spawn and W walks it
  - lava sends it back to the spawn
  - the last checkpoint becomes the respawn point
  - a running jump lands on the gold finish
  - Play again leaves play mode

  Two consecutive runs on fresh servers: 87/87 and 87/87.
- **C++ parity:** 52/52 with the palette regenerated.

## Held

- **Other people's avatars.** ADR-037 (presence) will send each avatar's position over STOMP, the
  SudokuPro way. Until then, play is solo.
- **Server-side best times / leaderboard.** These need presence's identity and an anti-cheat story (a
  time a page reports is a claim). Held for ADR-037.
- **Obby editor and kill bricks you place yourself.** Held until someone asks to build their own obby.
- **Studs in exports.** The GLB stays flat-topped. An engine can add studs the same way the realm does,
  from the palette.
