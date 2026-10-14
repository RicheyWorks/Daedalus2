# Labyrinth starter terrain

The Labyrinth style previously could not be mounted: `WorldStyle.LABYRINTH` was
not ready and `WorldHub.create` returned `STYLE_NOT_READY`. This change enables
an actual persistent starter volume through the existing world API and renderer.
It does not declare the whole realm complete.
`WorldStyle.ready` describes terrain generation/rendering. The separate
`Mount.SKY_STRIDER.ready` remains false: enabling a walkable host does not
pretend that Labyrinth flight or sky-gate travel is implemented.

## Build and preservation

`LabyrinthTerrain` reuses `RecursiveBacktrackerGenerator` and `StampOps` rather
than adding a second maze or terrain implementation. A 31 by 31 logical maze
becomes a 189 by 189 metre stone volume. Each maze tile covers three by three
voxel metres, so passages have three metres of horizontal clearance. The floor
occupies Y=0; walls occupy Y=0 through Y=3 (their top surface is Y=4).
The north entrance and south exit are open at the boundary.

Five-argument `StampRequest` callers retain scale one. The additional scale is
bounded to 1..4, and scaled bound arithmetic rejects overflow. The host generates
only at explicit world creation, under its existing mutation lock, and refuses
to replace any existing chunks or parcels. Registry reload reads the existing
DAEW volume; it does not regenerate over saved edits. Existing worlds and
existing Unreal art are not automatically changed.

Example existing API request, subject to the server's normal authentication:

```json
{"id":"labyrinth","style":"LABYRINTH","seed":42,"title":"The Labyrinth"}
```

POST this body to `/api/v1/worlds`. Blocks, chunks, saves and world exports use
their existing routes and formats. No alternate network protocol is introduced.

## Reproducible operator delivery

After compiling the core, run from the repository root with Java 21:

```powershell
java --class-path daedalus-core/target/classes tools/realms/ExportLabyrinth.java C:/deliveries/labyrinth-starter 42
```

The exporter refuses to overwrite its three output files:

- `Labyrinth_Starter.glb`: existing greedy mesher and binary glTF writer.
- `labyrinth.daew`: the same persistent volume used by the server.
- `labyrinth-starter.json`: seed string, hash, dimensions and feet anchors.

The seed-42 delivery sent to Poot is at
`C:/Users/730ri/Documents/Codex/2026-10-13/labyrinth-starter`.
GLB size is 779,252 bytes; SHA-256 is
`b5c78b90f1a5e51c41bb10c9a5207dfa9b22aa0a08c3a1e54ba53b42f5f40f1c`.
The volume contains 144 chunks, not 144 separately counted gameplay assets.

Coordinates are right-handed glTF Y-up metres. Entrance feet are
`(-90, 1, -93)` and exit feet are `(90, 1, 93)`. Import through the established
glTF conversion, then apply the operator's realm placement transform. Add the
pawn's capsule half-height when positioning its centre. The material uses vertex
colours; preserve them. Collision must be configured and tested by the Unreal
operator. Chunk meshes are terrain surfaces, not decoration copies.

## Acceptance and remaining work

Core checks flood-fill actual walkable voxels for five seeds, including signed
long extremes; require floor and headroom; reach the exit and every walkable
position; verify deterministic DAEW bytes and preservation of existing edits;
and exercise the existing GLB exporter. Server checks create/reload the host,
reject duplicate creation and wrong styles, and read actual floor/air through
the existing HTTP controller. Shared stamp regression tests retain scale-one
behaviour.

This is a bounded starter terrain, not the 10,000-land layout or final artwork.
It has no new NPC populations, vehicle systems, Halloween decoration, quests or
rewards. Those existing assets/systems must be integrated without replacing
them. Unreal import, capsule collision, entrance alignment, saved level and a
visible in-game walkthrough remain explicit operator acceptance work.
