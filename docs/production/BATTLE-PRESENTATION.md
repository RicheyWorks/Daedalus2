# Additive 3D battle presentation

ADaedalusBattlePresentation consumes Claude's unchanged BattleStageCore Cue
records (main 1cb065e2). It does not decide damage, spend MP, award loot or replace
the sprite battle. Assign dedicated presentation actors to member/foe slots,
and optional attack/hurt sequences sharing each mesh's skeleton.

Submit a director batch once when its battle line starts. Cue At values are
relative to submission. Batches are atomically validated: 512 queued cues maximum,
32 dispatches per tick, bounded slots/text and finite nonnegative times. Equal
times retain submission order. ClearCues fences the remaining callbacks in the
current due batch. Paused stops scheduling, not animation already playing; use
the game's pause mechanism for synchronized world pause.

PresentCue exposes name, actor/target references, amount, text, duration and
target faction/slot for camera, damage text, glitter, sound and area effects.
Missing actors or incompatible sequences do not play animations. Effects are
hooks pending actual presentation bindings. PlayAnimation uses single-node mode;
only bind dedicated stage meshes, never the hero's existing locomotion mesh.

The actor/reflection module compiled and linked in an isolated UE5.8 scratch
plugin, not the full shared plugin or live world. Director subscription in
Hero/Realm, cast placement, animation assets, camera/FX/audio, deterministic
functional scenarios and live Play comparison still need integration with Claude.
