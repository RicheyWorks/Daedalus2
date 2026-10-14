# Codex harbor contest batch

Three original additive entries: Copper Beacon, Blossom Harbor and Stormwatch Cove.
The source is `tools/blender/codex_harbor_islands.py`. Run with Blender 4.3 in an
explicitly released, claimed background export window and a fresh output directory.
It reuses the existing owned primitive/material helpers, preserving previous exports.

Each 92 m island includes layered stone, a lighthouse, dock, boathouse, dry-docked
boat prop, flowers, clustered trees, lagoon and waterfall. Role-named mesh objects
remain separate for Unreal material, collision and replacement work. The source
creates GLB, editable Blender files and hash manifests. No export or native import
is claimed until those actions are actually performed.

Integration: place these on available Codex deeds without replacing current islands.
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
