# Codex harbor contest batch

Three original additive dressing presets: Copper Beacon, Blossom Harbor and Stormwatch Cove.
The source is `tools/blender/codex_harbor_islands.py`. Run with Blender 4.3 in an
explicitly released, claimed background export window and a fresh output directory.
It reuses the existing owned primitive/material helpers, preserving previous exports.
Default exports contain props only, supporting the seeded terrain owned by
codex-play-guard. Optional `--with-terrain` retains the original shell for a standalone
assembly; it is not the team's seeded voxel terrain implementation.

Each preset targets a 92 m island with a lighthouse, dock, boathouse, dry-docked
boat prop, flowers, clustered trees, lagoon and waterfall. Role-named mesh objects
remain separate for Unreal material, collision and replacement work. The source
creates GLB, editable Blender files and hash manifests. No export or native import
is claimed until those actions are actually performed.

It also exports one FBX StaticMesh per role using temporary joined copies with a
common origin. This connects dressing to the existing FBX import format while
retaining separate editable props in the Blender scene. Manifest records contain
actual export elapsed seconds, bytes and hashes only after execution. FBX files
have no UCX hulls; the native owner must configure role-appropriate collision.
Use scale1 after the metre-to-centimetre import, retain the common local pivot,
and add a parent island transform to place each role together.

Integration: dress the seeded terrain on available Codex deeds without replacing current islands.
Fit water to the actual shore and dock posts to receiving terrain; these local transforms
are starting placements, not a guarantee against intersections on arbitrary heightfields.
Use the existing terrain collision workflow; assign blocking collision to terrain,
buildings and dock, not water or foliage. The cave arch requires separate collision
pieces and an actual opened terrain entrance before being advertised as traversable.
Its current arch is dressing; the underlying island shell is still solid.

Proposed game hooks: the Copper Beacon guides boat arrivals; Blossom Harbor supplies
unicorn rescue arks; Stormwatch Cove hosts mineral traders and wreck-recovery quests.
These are design proposals, not implemented quest or vehicle mechanics. Boarding
should use the established island-to-sea realm handoff, returning to land on docking.

Production lesson: reserve unique asset namespaces before building. The hub revealed
another Codex teammate already owned the cottage generator, so this batch adds harbor
content instead. Separate role meshes let the Unreal owner fix one material or collision
piece without rebuilding a complete island; keep that separation on import.

## team-codex | 2026-10-14 | Contest dressing and current connector observation
Read existing ownership/connector lessons before work. Named Epic SceneTools.get_current_level failed at HTTP send to http://127.0.0.1:8000/mcp this turn; no current-map readback, native mutation, restart or transport-cause claim. Feedback to Poot separates expected current-level response from observed send failure and impact: native placement cannot be dispatched through that connection now.
Hub30431/30435 assigns seeded terrain to codex-play-guard. Harbor source therefore defaults to additive role-separated props, with optional shell retained rather than deleted. Send exact footprint92m/native9200cm and scale1 contracts before reuse; arbitrary heightfields require fitting dock/shore geometry. Avoid duplicate generators, and count islands only after native import, placement and save evidence. Existing importer reuses fingerprint/import_snapshot and batches save_assets; its exact18/6-ID contract does not establish general contest import support or an unchanged-payload skip guarantee.
