# Parcels first cast kit

Thirteen original role representatives use the verified fourteen-bone rest rig
with Idle/Walk/Attack/Hurt prototype clips: courier hero, postmaster, surveyor,
fence smith, seed broker, field elder, helipad chief, cart crew, letter courier,
beekeeper, market crow, weather keeper and boundary dispute role. Gear adds
mail bags, envelope shield, survey rod, honey/seed/milk equipment and pilot kit.
Twins/feud entries represent group roles; full ensembles remain pending.

Fresh GLB validation passes thirteen exports, 13,516 triangles, skin weights,
hashes and animation loops. Geometry/animation remain prototypes; no new quest,
deed authority, auction, farming or helicopter behavior is implemented here.

cast_binding_map.py binds twelve NPC art candidates to the existing Parcels DCS
who names using exact script hash, realm/prefix checks and actual export hashes.
Lost-Letter Ghost maps explicitly to nonHalloween LostLetterCourier art, without
changing or renaming the owned script. The hero is a separate player binding.
Binding metadata does not install meshes or establish working native interaction.

Output: Documents/Codex/2026-10-13/parcels-buildout/cast. Creature/mount/pet and
environment kits, worksheet reconciliation, import and Play remain pending.

The creature kit adds nineteen validated role candidates on the shared eight-bone
rest: field creatures, mailbox/cart/combine constructs, ambient birds, helicopter,
draft ox, gyro goat and four helpful pets. Vehicle geometry does not implement
flight/driving; the Blight Bailiff is a visual boss proposal with no deed powers.
Together, the first Parcels cast has thirty-two role models. Rigid-part anatomy
and locomotion are prototypes pending visual/native acceptance.

realm_creature.py isolates rig/primitives from Portal gameplay-table assertions.
Gallery now extracts the exact existing rig function without executing the Portal
table initializer. A refactor experiment changed normal/index export bytes, so
the verified Gallery delivery was restored from its owned archive; published
Gallery hashes/worksheet data remain unchanged. No equivalence claim is made.
