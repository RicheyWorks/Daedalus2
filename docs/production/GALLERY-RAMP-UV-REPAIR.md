# Gallery ramp UV repair candidate

Claude reported a degenerate tangent-basis import warning for Prop_Gallery_Ramp in hub29138.
The delivered source GLB has POSITION and NORMAL attributes but no UV map. Its custom
`from_pydata` ramp bypassed the primitive UV creation used by the rest of the kit.

The isolated Blender 4.3.1 repair adds a smart-projected UV map, calculates tangents and exports
TEXCOORD_0/TANGENT data. Reimporting the delivered GLB confirms its 12 triangles preserve the
original geometric triangle coordinates, with finite unit tangents. The original file is intact.
`gallery_environment.py` now applies the same helper to the ramp on future generation. Existing
UV maps are left untouched. This is not a blanket UV repair for the whole asset library.

Original SHA256: `06d35c586d5026e5aeb5c9efe4883530763b1333c99fd26758f99fdcb8ae437a`.
Candidate SHA256: `800ba89538f01f90708fd9eab2cb777c881b5ab29d08a65b6efe67e789bace02`.
Candidate: `data/art/gallery/repairs/Prop_Gallery_Ramp.glb`. This replaces one asset, not an
additional model toward the population target. Existing manifests remain tied to their original
delivery until the Unreal owner accepts the replacement.

The sole Unreal operator must preserve the existing package, verify its current import path,
reimport this candidate and check the editor log before marking the warning resolved. No shared
Unreal package, map or import queue was changed by the producer. Geometry/UV/tangent validation
does not prove an Unreal importer accepts the candidate without warnings.

## Reproduction and lesson

Run `blender --background --factory-startup --python-exit-code 1 --python
tools/blender/test_static_uv_blender.py` for the regression. It proves the missing-UV baseline
refuses tangent calculation, then verifies repair, geometry preservation, idempotence and invalid
object refusal. For an existing single static GLB, run `repair_static_uv.py -- <source> <new-output>`
with the same Blender flags. The repair refuses an existing output or source/output alias.

Custom meshes do not inherit primitive UVs. Validate UVs and tangents after export/reimport rather
than counting triangles alone. Blender's default process exit can remain successful after Python
exceptions: require `--python-exit-code 1` and inspect the terminal proof marker and report.
