# ADR-038: Atmosphere (glow, sky, weather, texture)

Status: accepted, 2026-10-11

## Why

Next to Voxels, Decentraland and The Sandbox, the realm looked unfinished. Those worlds have textured
blocks, soft shadow in the corners, glowing signs, real nights, street lamps, rain, and a settings panel.
Ours had flat colours, the same light at every hour, and nothing that glowed. Gallery City (ADR-035) was a
grid of grey boxes after dark.

## Decision

The change is made in the browser renderer. The world model gets new blocks but no new systems.

- **Blocks that glow.** `BlockType` gains `LAMP`, `NEON_PINK`, `NEON_CYAN` and `WINDOW_LIT`, appended so the
  existing ordinals stay the same (WorldCoordinatesTest pins them). `emissive()` names them.
  BlockColors, the mesh fixture and the C++ parity (55/55) all carry the new rows.
- **Gallery City at night.**
  - Street lamps every 8 blocks along the sidewalks: a road-grey post with a lamp head.
  - A skyline of towers beyond the city's edge, with lit and dark windows (seeded) and a neon crown.
  - Gallery roofs get a neon cyan rim.
- **Renderer (realm.js).**
  - A procedural 4×4 texture atlas, made at load with no image files: stone, grass, grain, windows, water,
    bark and gravel.
  - Per-vertex ambient occlusion; the quad diagonal is flipped where AO would cross it.
  - A glow buffer drawn unlit.
  - ACES tone mapping and UnrealBloomPass.
- **Sky.**
  - The sky follows a keyframe table of sky gradient, sun angle and colour, fog, exposure and bloom.
  - It runs on the live clock, or on an hour the viewer picks.
  - At night, a pool of 10 point lights follows the nearest lamps.
  - Rain is 2,600 instanced streaks.
- **Settings.** A **Sky** button (key `O`) opens the panel:
  - live clock on or off
  - a time-of-day slider
  - rain
  - glow

  The panel's choices are kept in this browser only (try/catch around `localStorage`).

## What it found

- Adding block types breaks the mesh fixture by design, because the fixture lists every type. It was
  regenerated, and the C++ mesher still matches it.
- The atlas and AO cost no extra draw calls. Glow is one extra material for each chunk that has a glowing
  block.

## Held

- **Avatars**: voxel bodies, a third-person camera, name tags, wearables. That is the next slice, built
  through the Blender → Unreal pipeline.
- **Signs and 3D text, half-size voxels.** Held until avatars land.
- **Unreal side.** The glowing blocks import with their colours. Emissive materials on the Unreal side wait
  for the pipeline slice.
