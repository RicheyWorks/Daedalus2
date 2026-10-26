# Three pond plants: native workflow

Frogbit, PinkLily and WaterLily are imported, saved and admitted for this bounded
static-asset use. Native source geometry has 220 / 544 / 492 triangles, exact flat
RGBA palettes, one existing M_VoxelVertexColour material and no simple collision.
Fresh native validation checked all three: all Valid, no warnings/errors/skips.
They are not yet placed, visually accepted or production ecology/gameplay assets.

Read Epic's installed `EditorToolset/.../static_mesh.py:15` and `asset.py:24` before
using their tools. `StaticMeshTools.import_file` is the first-class entry point;
it uses an automated no-overwrite AssetImportTask and leaves assets unsaved.
Save only the explicit returned paths with AssetTools.save_assets. The current
convenience tool does not expose vertex-colour policy: its FBX default IGNORE
produced white vertices here. Native Valid alone did not detect that visual loss.

For vertex-coloured FBX use Unreal's native AssetImportTask with an explicit
InterchangeGenericAssetsPipeline / InterchangePipelineStackOverride. Set common
vertex colours IVCIO_REPLACE, bake_meshes=false, mesh build scale 1, disable material
imports/Nanite/lightmap UV generation/collision as appropriate for these three
decorative sources, and bind the existing palette material. Fresh imports keep
replace_existing=false. Corrections here targeted only the three assets created
by this batch, after backups and exact source/package binding; ApplyPipelineProperties
was necessary for the native reimport to apply the changed colour options.

Do not use FbxImportUI options to infer Interchange behaviour: the first attempted
correction selected Interchange and kept white colours. Its saved result and full
BridgeError reply were reconciled before the explicit pipeline correction.

Observed native dimensions are Frogbit 75 x 55 x 15 cm, PinkLily 85 x 75 x 40 cm and
WaterLily 85 x 65 x 40 cm. Actor scale1 is appropriate for these native assets; the old
custom unit 100 / actor 0.01 profile is not their contract. Exact locations and
package/source hashes are in build.json; original FBX/sidecars are in sources/.

The custom queue/full-corpus inventory is not a prerequisite for this ordinary
native workflow. This batch used source hashes, targeted native name/tag search,
fresh owned destinations, actual source/colour readback, explicit saves, genuine
native validation and saved-work/resource/sole-writer protection. It does not
claim exhaustive deduplication across unknown historical imports or qualify bulk
unattended ingestion. No custom admission predicate or engine setting was weakened.
