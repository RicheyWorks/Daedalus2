# Lantern Commons: presentation and pickup feedback

The saved 104 x 105 m peaceful scene uses the existing Daedalus Hero/input and
approved Blender floor, rocks, Willow trunk/canopy and Lantern chart. Follow the
amber route through Shade Grove and the stepped Stone Overlook to the chart
garden, then press E. Thirty-two paired trees, twelve new planted pockets,
arrival pads and grouped rocks give the three destinations stronger identities.
Continuous ground collision and generous roaming space remain intact.

All four scene lights are movable. Unreal's actual diagnostic reported zero
unbuilt light and primitive interactions, without a lighting bake or global
render-setting changes. The saved scene clean-reloaded with 141 actors and 273
floor instances; eight sampled route/edge collision rays passed.

One actual Play traversed 37.62 m across the three stops, all grounded and within
37 cm of the targets, at full health/shields with zero enemies. E removed the
owned chart child at 2.18 m. Its native EventDestroyed -> PrintString graph logged
`LANTERN CHART COLLECTED!` and requests 18 seconds on screen. Two game-viewport
captures were written immediately and 2.61 seconds after the interaction.
This is development-only PrintString feedback; a shipping UMG/HUD is not claimed.
Normal Play stop restored encounters from 0 to 1 and left all packages clean.
Current player progress was not rolled back; originals were not edited or saved.

Current captures are under `images/presentation-r2/`: matched before/after
player-height, route and overview images, plus both gameplay-success PNGs.
Their bytes/hashes are verified, but independent pixel review is PENDING because
the local image reader closed the executor transport. Do not equate the log or
PNG existence with accepted readability. The parent can inspect these repository
images directly. Earlier images/native-proof.json remain historical R1 evidence.

Use the existing map at the manifest world path. On a compatible Daedalus checkout,
copy only this pack's Content files to their matching project Content paths under
normal ownership/preservation; do not overwrite other work or mount under plugin
Content. Listed native classes/imported meshes must already exist. This is not a
standalone project. The new child Blueprint and editable `feedback-graph.dsl`
reuse Epic BlueprintTools; no C++/plugin/framework or installation was needed.

Reusable recipe: use BlueprintTools.create with native DaedalusStarChart parent;
add ReceiveDestroyed; discover PrintString and its actual pins; write the supplied
DSL, compile/save and place only in the owned map. Set the scene's single formerly
stationary destination light to Movable, preserve the other three movable lights,
then save/reload and inspect DumpUnbuiltLightInteractions. Verify actual E pickup
through input, retain screenshots and normally stop Play with encounter restoration.

The established 17-image benchmark board and Adopt Me minimum remain the quality
bar to exceed over iteration. Final style is undecided. Visual finish, repetition,
destination clarity and message readability await review; this is not reference-
quality, production visual/performance acceptance or prebuilt game-jam content.
