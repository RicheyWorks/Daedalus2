# Native Ocean sector scene

OceanSectorView consumes decoded OceanChunkView snapshots and reuses the existing
MeshCore greedy mesher. Its bounded chunk map defaults to 64, configurable up to
256 before streaming. Full maps refuse new chunks without discarding old data.
Consumers remove out-of-range chunks explicitly. This actor is not the network
request scheduler or a replicated player visibility policy.

The palette helper is generated from Java BlockType/BlockColors, including colour,
translucency and see-through semantics. generate_palette.py --check detects drift;
it refuses silently changed Java semantic expressions. Unknown palette entries,
duplicate names, out-of-range ordinals, malformed payloads and palette changes
within a populated view refuse without replacing the previous scene. Revision
regressions refuse; an equal revision must have identical blocks. Equal snapshots
are idempotent. Clear the view explicitly when switching realm/seed/session.

Each chunk meshes at local coordinates 0..16 metres with its six resident
neighbours translated into adjacent local keys. Chunk components use double
relative offsets (x,z,y)*1600 cm. This avoids the mesher's global float precision
and signed-boundary arithmetic at distant plots. Loading/removing a neighbour
rebuilds shared boundaries; emptied chunks remove geometry while retaining their
loaded state. Only the opaque section creates collision. Water/translucent
sections do not block boats or submarines.

OpaqueMaterial and WaterMaterial are scene-owner assignments and should be set
before chunks arrive. Missing assignments use the existing engine vertex-colour
fallback for inspection. That fallback is not final water shading or polished
art. Water fog, waves, buoyancy, lighting/composition and material assets remain
visual/gameplay integration work. No existing world art is replaced.

Complete 135-file plugin compilation/link passed 48 actions in 202.42 seconds. All four native Ocean tests passed with zero test errors/warnings, including seams, capacity, collision flags, old revisions, clear/remove and far-coordinate geometry. The real packaged Java/native HTTP fixture passed in 20.766 seconds including startups: procedural geometry creation, water collision disabled, and persisted cleared-chunk revision removing a previously populated mesh. The Java store now keeps empty chunk revisions and rejects regressing/conflicting replacements; all 719 core tests passed. See ocean-view-build-proof.json, ocean-view-runtime-proof.json and ocean-view-http-proof.json.
NullRHI geometry proof will not be called a rendered gameplay screenshot.
The shared WorldActor/loader/Hero/Orrery and shared editor remain untouched.
