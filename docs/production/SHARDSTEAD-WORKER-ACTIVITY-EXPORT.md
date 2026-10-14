# Shardstead worker activity export — 14 October 2026

Six existing worker models were actually exported from the existing owned
`tools/blender/shardstead_workers.py` at source head `2cfb952d` using headless
Blender 4.3.1. The original exports are retained unchanged. New files and a GLB
readback receipt are in `engines/unreal/art/shardstead-worker-activities-v1/`.

Workers: Twaker Prospector, Cachekeeper and Trader; Shardstead Farmer, Energywright
and Rescuer. Every exported GLB contains one 14-joint skin and the seven named
clips Idle, Walk, Attack, Hurt, Mine, Trade and Repair. This delivers the 18 missing
activity clips (three across six workers) at export stage, not six new characters.
The receipt records exact file lengths and SHA256 hashes from actual GLB bytes.

The Blender process completed in one observed 3.77-second tool interval, including
hub send/startup; it is not a per-stage benchmark. Editable scene is retained at
`C:/Users/730ri/Documents/Codex/2026-10-14/shardstead-workers-activities-01/shardstead-workers.blend`.

Quality and native delivery remain held. Clip names do not prove expressive motion,
tool contact, blending, grounded feet or Adopt Me appearance. Review actions in
Blender, polish the exemplar, then use the current Unreal owner's normal import
and saved-scene handoff. No source claims of item transfer, mining rewards, repair
effects, inventory mutation or runtime animation binding follow from these clips.
