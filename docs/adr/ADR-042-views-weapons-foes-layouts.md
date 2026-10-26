# ADR-042: Camera views, the blaster, foes, and Halo button layouts

Status: accepted, 2026-10-12

## Why

Richmond asked for a Halo Infinite first person with a centred reticle, a Gears of War over-the-shoulder third
person, a way to switch between them, shooting, and the full set of Halo controller layouts ("never know how
someone uses the controller").

## Decision

- **Views** (`CameraView`, Settings → Video, V / d-pad up cycles): 0 First Person (camera at the eyes, the body
  hidden from its owner), 1 Over the Shoulder (default; short boom offset right, C / LB swaps shoulders),
  2 Classic (the ADR-040 chase camera). Field of view and camera distance are settings.
- **Weapons:** 0 sword (ADR-040 swing and down-thrust), 1 blaster. The blaster is hitscan from the camera
  centre, so the reticle is honest in every view: 0.11 s between shots, heat +0.065 per shot, overheat and vent,
  spread that blooms while firing, zoom on Aim. Tracers and impact flashes are short-lived cube actors, so no
  assets are needed. Y / 1 / 2 / wheel switch.
- **HUD** (Slate): a dot-and-ticks reticle that opens with spread and turns red on a hit, the weapon name, a heat
  bar and OVERHEATED, the view name, EXP.
- **Foes:** `ADaedalusTarget`, ADR-037's four kinds (Blight Slime, Shardback, Dust Wisp, Stone Knight) with their
  life, power and EXP. The table is fetched from `GET /api/v1/hero/rules` (`daedalus.Server`) and falls back to the
  built-in copy. A kill credits the hero's Kills and Exp.
- **Layouts:** Button Layout (Default, Bumper Jumper, Bumper Ninja, Boxer, Green Thumb, Recon) and Thumbstick
  Layout (Default, Southpaw, Legacy, Legacy Southpaw) rebuild the mapping context live. Invert Look sits first on
  the Controller tab.

## Proven live (UE 5.8.3, Play in Editor, driven by the harness)

- `SpawnFoes(4)` placed 4 foes; aiming with `AimAt` and firing each frame: 31 shots, 30 hits, 4 kills, 60 EXP
  (2 + 5 + 3 + 50, ADR-037's values exactly), heat 0.52 after.
- `CycleView` went 1 → 2 → 0 → 1.
- `SetSetting("ButtonLayout", 1)` moved Jump from A (`Gamepad_FaceButton_Bottom`) to LB
  (`Gamepad_LeftShoulder`) per `DescribeBindings`; back to Default after. `InvertLookY` stayed 1.

## Held

Enemy AI (foes bob and take hits but do not hunt yet), sound, and per-weapon ammo pickups.
