# Lantern Commons

A saved 104 x 105 m exploration courtyard for the existing Daedalus project.
It reuses the approved Blender cave-floor/rock meshes, Lantern chart, native Hero,
movement/input and pickup behavior. This is a playable prototype with room to roam.

The existing editor already has the scene open. Open the map listed in
`manifest.json` and press Play. Use WASD and mouse to move/look, and E near the
central chart to collect it. Stopping Play preserves normal Hero progress.

For another compatible Daedalus checkout, copy the two files under this pack's
`Content/` to the same paths under the project's `Content/`, only when those
destinations are vacant. The native classes and three mesh dependencies listed
in the manifest must already exist; this pack is not a standalone project.
Do not put these files under plugin Content, which would change their mount path.

The saved rule Blueprint disables automatic encounter packs on BeginPlay and
restores the previous `daedalus.Encounters` value on EndPlay. This was observed as
1 -> 0 -> 1 with no enemies during Play. It assumes one serialized Play world.
No damage, enemy combat behavior, input defaults or project settings were changed.

Actual checks: save/reload retained 273 floor instances; eight corner/seam traces
hit the continuous physical floor; the Hero walked 4.48 m and collected the chart,
then ran 25.30 m while grounded. Health and shields remained full. Play ended
normally. The temporary overview camera restored its prior pose.

Known limits: the overview is visibly overexposed and needs visual polish. Two
original floor material instances remain dirty in editor memory; their changes
were neither saved nor discarded, and their cause is not established. The scene
and rule Blueprint themselves are saved and clean. General forgiving combat
balance remains a design direction, not a completed feature. See `manifest.json`
for exact paths, hashes and bounded claims.
