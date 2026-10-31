# Shardstead worker animation binding

Team Codex source preparation, 14 October 2026. New portable header:
`engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusShardsteadWorkerActivity.h`.
This uses the existing six-worker cast and exported Idle, Walk, Attack, Hurt,
Mine, Trade and Repair clip names. It creates no new realm or persistence layer.

The host supplies the worker role, committed job, confirmation state, worksite
proximity, speed in metres per second and monotonic hurt/defence event sequences.
Use one selector per worker. Convert Unreal centimetres to metres at the adapter.
Read the committed snapshot; pending storage writes must not assert JobConfirmed.
Disabling presentation consumes event sequences without replaying them on enable.
Reset when rebinding to another worker or a new event-sequence session.

Priority is disabled idle, hurt reaction, defence reaction, walking, confirmed
supported work at the site, then idle. Walking uses separate start/stop thresholds
and bounded playback rate. Repeated snapshots do not restart reactions. Invalid
speed and elapsed time are handled as zero. Animation events never grant ore,
complete trade, repair equipment or award rescue credit: those remain existing
authoritative transactions. Missing crop and stationary escort clips use Idle;
do not relabel mining as farming or claim new animation coverage.

The Unreal owner can bind ClipName to the imported animation assets, apply
Changed for clip transitions, and use Loop for reaction versus repeating motion.
Output::ReactionStarted is an additive one-Advance pulse: start or restart the
selected one-shot when true, including when Changed is false because a distinct
accepted event selected the same clip. Handle `Changed || ReactionStarted` once
per update (not twice when both are true), using BlendSeconds as appropriate.
Do not infer a restart merely from a non-looping clip remaining selected.
Replica hosts consume replicated committed
state rather than inventing jobs locally. No component or transport is modified.

Source is uncompiled and not installed. No tests, builds, editor calls or Blender
process were run for this step. Native binding and Adopt Me quality acceptance
remain pending: review feet, tool contact, expressions and blended motion before
world placement. The earlier export receipt proves clip names and rig contents,
not this runtime integration.

Lesson: separate confirmed gameplay state from cosmetic motion selection, and
document missing clips explicitly instead of giving unrelated motions new names.

## Accepted reaction pulse — Team Codex, 15 October 2026

Changed retains its original meaning: the selected clip enum differs from the
previous update. ReactionStarted is true only when an enabled, newly increasing
event actually enters the existing hurt or permitted defence branch. A second
distinct HurtEvent during Hurt or DefenceEvent during Attack refreshes the timer
and pulses; repeating or decreasing sequences do neither. Hurt wins simultaneous
events. Defence received during active Hurt is consumed but emits no pulse and
is not queued for later. Disabled updates consume sequences without a pulse;
re-enabling the same snapshot does not replay them. Reset still clears sequence
history for a new worker/session. Timers, locomotion, job selection, six-worker
cast and seven clip names are unchanged.

This minimal source correction was reviewed by reading its acceptance branches
and adapter contract only. It remains uncompiled, unexecuted and uninstalled;
no tests, builds, Blender, editor, Play or runtime calls were performed. Native
binding and visible restart/quality acceptance remain with the existing operator.
