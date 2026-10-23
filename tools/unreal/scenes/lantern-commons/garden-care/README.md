# Garden-care variants R11

Four Blender designs are now imported, saved, admitted and placed: compact rain
barrel, open compost bin, filled apple crate and roofed bird feeder. Their native
triangle counts44/52/72/60, flat RGBA palettes and dimensions30x30x50,
50x50x30,40x40x30 and50x50x80cm match the exact source oracles. All use actor
scale1 and the existing vertex-colour material; authored pivot offsets remain.

Used native AssetImportTask with InterchangeGenericAssetsPipeline/stack override:
IVCIO_REPLACE, bake_meshes=false, build scale1, materials/Nanite/lightmap UV/auto
collision off. Initial replace_existing=false; each destination was checked fresh.
No full-corpus wrapper, inventory repair, engine/plugin install or custom importer.
One subsequent native validation checked all4:4Valid,0warnings/errors/skips/unable,
return0,acceptedtrue. The canonical payload/flags are retained unchanged in build.json.

The four props sit at authored scale on the existing visible ground beside the
gardenkeeper, at least2.9m from kiosk/seed/planter pivots. New components are
NoCollision. The owned map is saved cleanly with753actors. Existing ground/routes,
activity assets and Hero/garden-slot files remain intact. Compute was released.
Actual editor image: ../images/garden-care-r11-station.png. Lighting still washes
out pale wood; native palette correctness is not visual benchmark acceptance.

The user permits different designs in the same category. An Orr rain barrel or
generic crate does not prove these designs duplicate it. Revision2 superseded
the earlier role/category exclusions before any editor import ran. Exact current
name/hash-tag searches found no matches, and fresh SHA-suffixed destinations
preserve older assets. Different FBX/GLB hashes alone do not prove visual
uniqueness, and no complete historical source-hash deduplication is claimed.

This is a decorative care station, not bird AI/feeding, crafting, economy, rewards
or another activity. No Play/reload/test loop ran. Eight exact FBX/sidecar files,
four saved packages and source/provenance hashes accompany this receipt.
