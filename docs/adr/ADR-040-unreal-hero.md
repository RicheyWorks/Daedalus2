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

## Held

- Enemies and hit detection on the sword.
- Side-view (Zelda II) battle scenes, and the overworld map camera.
- A mesh from the Blender pipeline to replace the blocks.
