# ADR-040: The Daedalus hero in Unreal

Status: accepted, 2026-10-11

## Why

The capability walk (connector harness) proved Play In Editor works, but Play spawned a `DefaultPawn`: a camera
that flies around. ADR-036's game needs a hero who walks the islands and fights. A Blueprint's input logic
can't be written from Python, so the hero is C++, in the DaedalusLink plugin.

## Decision

- **`ADaedalusHero`** (an `ACharacter`) is built entirely in code, so it needs no assets:
  - A blocky body that matches the realm avatar (ADR-034), with a shield and a sword on a pivoting arm.
  - A spring-arm camera.
  - A walk cycle (legs and the free arm swing with speed).
- **Controls** use Enhanced Input, with the actions and mapping made at runtime:

  | Action | Keyboard / mouse | Gamepad |
  |---|---|---|
  | Move | WASD | left stick |
  | Look | mouse | right stick |
  | Jump | Space | A |
  | Dash | Shift | B |
  | Sword | left mouse or J | X |

- **Zelda II down-thrust.** Swinging in the air drives the hero down, and landing bounces him back up.
  `Swings` and `Bounces` are counted so the harness can check them.
- **`ADaedalusGameMode`** makes the hero the default pawn.
- **`daedalus.hero_setup`** is a bridge command. It sets the level's GameMode Override, then traces down onto
  the island cubes and places "Daedalus Hero Start" on the ground.

## Proven live (UE 5.8.3, 2026-10-12)

- **Build.** The C++ compiled first time.
- **Play.** It spawns a `DaedalusHero` built from 12 blocks, standing on the island at the hero start.
- **Driving.** Walking, jumping and sword swings work (`Swings` counted). The down-thrust (a swing in the air)
  lands and bounces (`Bounces` counted).
- **Respawn.** The first drive walked him off an island, with nothing to stop the fall. After that, the hero
  remembers his last ground and returns to it when he falls `FallLimit` (2,500 cm) below it. A 40,000 cm/s
  launch into the void came back with `Respawns` = 1.
- **Fixes found on the way:**
  - `daedalus_worlds()` counted scenery folders (Atmosphere, Lamps, Show) as worlds. Only folders that hold
    chunks count now.
  - `hero_setup` needed the UClass for the GameMode Override.
  - The setup's build check skipped the build when a background helper ran in the VS Installer folder. Only a
    windowed installer blocks it now.
  - The startup "rebuild modules?" dialog is answered by `dialog-watch.ps1`.

## Held

- Enemies and hit detection on the sword.
- Side-view (Zelda II) battle scenes, and the overworld map camera.
- A mesh from the Blender pipeline to replace the blocks.
