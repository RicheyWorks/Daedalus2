# Gallery creature kit

Nineteen original creature/mount/pet role models complement the thirteen cast
exports. Shared eight-bone rest and four prototype clips enable modular import;
silhouettes include canvas wings, tile hound, living frame, tripod easel, marble
bust, drone fans, pack mule and colour prism. LightProjection replaces the spooky
wraith proposal to respect the user's Halloween-only-in-Labyrinth direction.

Creature abilities, drone flight, pet interaction and boss effects remain proposals
pending native bindings. Rigid-part animation is a prototype, not final anatomy
or locomotion. This kit does not implement colour theft, reforms, fog or flight.

The first validation rejected extra neutral joints caused by humanoid primitive
defaults referencing spine instead of creature body. The corrected generator sets
creature defaults explicitly; shared export now rejects vertex groups absent from
the rig before writing a GLB. Strict exported joint-count validation stays intact.

Blender CLI should use --python-exit-code 1 and shell callers must check native
exit codes before announcing validation. A chained PowerShell command continued
after the first validator failure; the premature hub claim was corrected in28809.

Corrected export validation passes all nineteen assets: 32,112 triangles total,
eight joints per skin, normalized weights, finite geometry and four clip loops.
Together with thirteen humanoid role representatives, the first Gallery cast kit
has thirty-two roles. This is exported art evidence, not live gameplay acceptance.

The environment kit adds twenty-four static exports, 5,652 triangles, on a two
metre module grid. Floor/wall/frame/door/ramp/rail pieces, workshop stations,
drone dock, concert platform, rainbow frame and underwater arrival airlock use
single joined meshes. There are no detached top fragments. Floor preview
z-fighting was corrected by lowering only the preview ground plane one millimetre.

Complete first package: fifty-six exports, 51,460 triangles, thirty-two roles.
validate_gallery_package.py revalidates both rigs and static geometry, verifies
unique IDs, and produces production-data.json plus additive catalog CSV. No
shared MASTER workbook is overwritten. Full Codex tracker becomes 227 unique
exports. Import, collision, navigation, interactions and actual behaviors remain
pending. Existing Curator found-choice reward gating has been flagged to Claude;
the script was not changed in this art scope.
