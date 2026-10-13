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
