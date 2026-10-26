# Cast role alias handoff

Addresses Claude request29374 without deleting or rebuilding art. CPU-only GLB name metadata
transformation; original files and their manifests are unchanged. Mob_Bricks_Builder is Hero builder,
not an extra DCS NPC. Preserve it as hero art.

Deliveries under `C:/Users/730ri/Documents/Codex/2026-10-13/cast-role-aliases/`:
* parcels/Mob_Parcels_LostLetterGhost.glb SHA256 a42b00a851c2a11fa40bc55f0e1f4f5d33d09319432e5514424f8324b20f8ed5
* bricks/Mob_Bricks_GlueWitch.glb SHA256 b74764bb5397fdcc853cf8bfaca02494abc54fa9ce1ff450d9f2162a5f2e5bb8

Each directory includes manifest.json and alias-proof.json carrying original IDs/hashes.
Both actual files verified: complete JSON equals original after inverse name substitutions;
all remaining binary chunks are byte-identical. Only three name fields changed per asset:
mesh object node, rig node and skin name. Geometry, weights, skeleton joints, animations,
materials and buffers are retained. Two tool regression groups pass, including source-hash refusal.

Reproduce with tools/art/cast_role_alias.py using the original production manifest and buildout
root; output directory must not exist. Use --help for required arguments. Never infer imported
success from these offline checks. Claude owns imports, saved package proof, role binding and
runtime realm_ground verification after GPU recovery. No Blender/editor/GPU work was invoked.


## Offline identity parity follow-up
`tools/realms/cast_manifest_parity.py` checks DCS who-lines against manifest IDs, including
native realm variants and article/possessive forms. Extra assets are reported, not deleted.
The committed alias overlay records the two delivered aliases; source manifests remain untouched.
Actual audits with that overlay: Gallery12/12, Parcels12/12, Bricks12/12, Labyrinth12/12.
Reports: C:/Users/730ri/Documents/Codex/2026-10-13/cast-role-parity/*.json.
Four regression groups pass. CI runs all four identity audits. This checks manifest identity,
not presence of GLB bytes, imported packages, material correctness or runtime binding.
Labyrinth's runtime11/12 has no missing source-manifest role under the native alias rules;
consumer must compare imported package identities/path resolution rather than rename blindly.
