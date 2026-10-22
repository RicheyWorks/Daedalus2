# Lantern Commons exploration loop

A saved 104 x 105 m peaceful scene for the existing Daedalus project. Follow the
amber trail through Shade Grove and Stone Overlook to the Lantern chart. WASD
and mouse use the existing Hero controls; press E near the chart to collect it.
The native pickup/quest feedback is reused. No enemies, wallet, external service
or new gameplay framework was added.

This scene reuses the approved cave floor, rocks and chart plus the existing
Willow trunk/canopy pair, reviewed separately before assembly. Seventeen trees,
three landmark groups and eighteen low pavers provide a route while retaining
generous open running space. Five material copies live in the owned namespace;
original assets were not edited or saved. Exposure/bloom controls are map-local.

Actual Play covered 37.66 m across all three stops in MOVE_WALKING, with each stop
within 35 cm of its target, full health/shields and zero enemies. E removed the
chart. Map save/reload retained 273 floor instances and the owned material
bindings. Eight ground rays passed. Normal stop restored encounters from 0 to 1;
current Hero progress was not rolled back.

Use the existing editor map at the manifest's world path, then press Play.
For a compatible Daedalus checkout, copy this pack's `Content/` files to the same
project `Content/` paths only under the normal ownership/preservation workflow;
do not overwrite another user's work. Do not mount these files under plugin
Content. The native classes and imported meshes listed in the manifest must
already exist; this is not a standalone project.

Evidence: `images/before-player.png`, `images/after-player.png`, before/after
overview and the two native gameplay screenshots. Camera poses match, although
the before views include editor sprites and the after views use Game View.
The native gameplay PNGs have verified identities but await pixel inspection:
the image reader closed the execution transport twice. Do not claim visually
accepted pickup feedback from file existence alone.

The existing competitor board sets Adopt Me as the minimum to exceed over
iteration. Final style remains undecided. Current floor repetition, sparse
distant composition and utility-shaped pavers/gate still need finish; the slice
does not claim reference-level art or production readiness.

Two original cave-floor material instances remain dirty in editor memory from
the engine's automatic instancing-usage flags. They were neither saved nor
discarded. The editor must preserve that state; never blanket-save or force-close
it. The scene's encounter rule assumes one serialized Play world. General
kid-friendly combat balance remains design-only. This is independent Daedalus
work, not game-jam content.
