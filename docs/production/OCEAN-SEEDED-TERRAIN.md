# Seeded Ocean terrain

OceanTerrain v1 provides actual terrain in the existing chunk/save/mesh formats.
It generates only requested 16-metre chunks at absolute coordinates, including
negative coordinates. Seeded bilinear depth ranges from 24 to 55 metres, with
three sand layers over stone and water up to Y=0. The only surface structure is
a floating wood pier. Boat and submarine berths have clear water/air around them.
The terrain has no natural land islands; land destinations belong to other realms.

`chunk(seed, address)` has fixed work and independent mutable output. `newWorld`
creates a fresh World from up to 64 requested chunks, refuses duplicates and
coordinates whose complete chunks exceed signed block coordinates, and omits
air-only chunks. It never edits an existing world. These are bounded bootstrap
batches, not a 64-chunk limit on the sea realm. A host can request more chunks
as players approach. No whole-realm allocation or storage estimate is implied.

The host must persist seed plus generator version and keep a durable record of
modified/generated areas, including mined-to-empty chunks. Saved player changes
must win over regeneration. WorldStore preserves voxel changes, but does not
store this generator's seed/version automatically. Automatic generation into a
live World, host registration, district routing and realm transfer are pending.

The initial exported sector is x/z -32..31 m, y -48..15 m. It contains 64 chunks,
a dock spawn at (0,2,0), boat berth (0,1,8) and submarine berth (0,-8,8), all in
Daedalus +Y-up metres. Unreal adapters convert (x,y,z) to (x,z,y)*100. This bootstrap
is an inspection/import delivery, not the total realm footprint.

Build and export from the repository with Java 21:

```powershell
mvn -pl daedalus-core -am -Dtest=OceanTerrainTest -Dsurefire.failIfNoSpecifiedTests=false test
java --class-path daedalus-core/target/classes tools/ocean/OceanBootstrap.java FRESH_DIRECTORY 42013
```

The exporter refuses an existing output directory. It writes ocean.daew,
ocean.glb and ocean.json with generator seed/version, coordinates and explicit
server_registered=false / unreal_play_verified=false flags. Existing palettes,
save versions and shared WorldHub/WorldService/native loader files are unchanged.

Six focused tests cover seabed/water invariants across seeds and negative seams,
boat/submarine berth clearance, independent chunk outputs, coordinate/batch
validation, and WorldStore save/reload retaining digging and construction edits.
The full core regression result and concrete delivery hashes are recorded in
ocean-terrain-proof.json once that run completes.
