# Codex harbor contest batch

Three original additive dressing presets: Copper Beacon, Blossom Harbor and Stormwatch Cove.
The source is `tools/blender/codex_harbor_islands.py`. Run with Blender 4.3 in an
explicitly released, claimed background export window and a fresh output directory.
It reuses the existing owned primitive/material helpers, preserving previous exports.
Default exports contain props only, supporting the seeded terrain owned by
codex-play-guard. Optional `--with-terrain` retains the original shell for a standalone
assembly; it is not the team's seeded voxel terrain implementation.

For the first bounded turn, append `--preset CopperBeacon` to export just one complete
kit. Selecting a preset retains its original index and seeds; it does not renumber
the remaining presets. The manifest hashes this generator and both reused helper
files, so the receiving owner can identify which exact sources produced a batch.

Each preset targets a 92 m island with a lighthouse, dock, boathouse, dry-docked
boat prop, flowers, clustered trees, lagoon and waterfall. Role-named mesh objects
remain separate for Unreal material, collision and replacement work. The source
creates GLB, editable Blender files and hash manifests. No export or native import
is claimed until those actions are actually performed.

It also exports one FBX StaticMesh per role using temporary joined copies with a
common origin. This connects dressing to the existing FBX import format while
retaining separate editable props in the Blender scene. Manifest records contain
actual export elapsed seconds, bytes and hashes only after execution. FBX files
carry per-solid-part UCX convex hulls for blocking roles; water and foliage carry
none. Separating solid parts avoids one convex bridge over the cave arch opening.
This is source-authored collision, pending actual export and native verification.
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

Actual Blender review on 14 October: Copper Beacon exported and two rendered
revisions were visually inspected. It remains a prototype below the Adopt Me bar.
Latest source raises the T-dock landing 12 cm to remove overlapping coplanar deck
surfaces and reserves crown clearance around the boathouse and dry-docked boat.
These corrections were subsequently viewed in preview revision 3: the dock surface
artifacts and cottage/crown overlap are resolved in that review image. Overall
terrain and water finish remain below the quality bar; no new delivery export or
native placement is claimed. The source
lane does not own the separately claimed sky-harbor machinery modules.

Use `--preview-only --render --preset CopperBeacon --with-terrain` for composition
iterations. This saves an editable scene and a consistent CPU-rendered review image,
without generating FBX/GLB or UCX. The actual revision-3 folder contains only those
two artifacts and a manifest marked preview-only/quality-not-ready. Observed render
time was 7.46 seconds; it is a single loaded-PC observation, not a speed guarantee.
Final delivery export uses the existing mode after visible quality issues are fixed.

Revision 5 now has a carved lagoon basin, limestone shoreline, a beacon rise and
an outlet whose waterfall location is derived from the actual rim intersection.
Path, flower and tree placement uses the terrain height. Aerial and player-distance
views were both rendered and personally inspected; the dock and boathouse read
clearly together. Remaining defects: triangular shoreline artifacts, thin waterfall
appearance, repetitive trees and insufficient variation in terrain/materials.
It remains below the final bar and is held from delivery.

Evidence: local `Documents/Codex/2026-10-14/harbor-copper-preview-05/`, editable
scene plus two review PNGs and preview-only manifest; 369 mesh objects. Observed
generation 9.91 seconds, combined two-view rendering 19.54 seconds on the loaded
PC; not a benchmark. The newly concave terrain deliberately exports no single
UCX hull: the Unreal owner must review triangle collision separately before use.
Prop UCX pieces remain independent. Original previews and teammate assets retained.

Continuous creation resumed after user correction30639 while ingestion proceeds
separately. Revision6 softens the lagoon/channel height transition and replaces
the straight waterfall box with curved static sheet geometry, lip foam and a few
flow highlights. Water roughness and review lighting are refined. Both saved
views were inspected: contact/shoreline reads more clearly, but bank faceting,
sparse terrain and repetitive groves remain below the Adopt Me bar. This is static
art review, not fluid simulation, animation or native approval.

Retained output: `Documents/Codex/2026-10-14/harbor-copper-preview-06/`, 381 meshes,
generation7.13s, combined two-view render18.99s (one loaded-PC observation), CPU
four threads. No FBX/GLB was created in preview mode. The render process ended
normally. Other-team report30652 of near-full RAM/commit means subsequent source
refinement can continue while another render waits for actual available capacity;
no app termination, resource setting change or editor takeover is implied.

## team-codex | 2026-10-14 | Contest dressing and current connector observation
Read existing ownership/connector lessons before work. Named Epic SceneTools.get_current_level failed at HTTP send to http://127.0.0.1:8000/mcp this turn; no current-map readback, native mutation, restart or transport-cause claim. Feedback to Poot separates expected current-level response from observed send failure and impact: native placement cannot be dispatched through that connection now.
Hub30431/30435 assigns seeded terrain to codex-play-guard. Harbor source therefore defaults to additive role-separated props, with optional shell retained rather than deleted. Send exact footprint92m/native9200cm and scale1 contracts before reuse; arbitrary heightfields require fitting dock/shore geometry. Avoid duplicate generators, and count islands only after native import, placement and save evidence. Existing importer reuses fingerprint/import_snapshot and batches save_assets; its exact18/6-ID contract does not establish general contest import support or an unchanged-payload skip guarantee.
