# Additive 3D battle presentation

ADaedalusBattlePresentation consumes Claude's unchanged BattleStageCore Cue
records (main 1cb065e2). It does not decide damage, spend MP, award loot or replace
the sprite battle. Assign dedicated presentation actors to member/foe slots,
and optional attack/hurt sequences sharing each mesh's skeleton.

Imported cast clips are resolved per skeletal mesh under
`/Game/Daedalus/Art/Cast/<Id>/`, including child folders. An exact `Attack`/`Hurt`
name, `_Attack`/`_Hurt` suffix, or exact mesh name plus `Attack`/`Hurt` selects
the role. The last form matches the observed imported
`Mob_Gallery_CuratorVellAttack` and `Mob_Gallery_CuratorVellHurt` filenames.
Only sequences with the exact
mesh skeleton qualify; deterministic asset-path order breaks duplicate ties.
Compatible explicit attack/hurt overrides still take precedence. A mismatched
override falls back to that mesh's imported clips, never another cast's folder.
Missing clips leave the character untouched.

BeginPlay prewarms the stage's first 32 member and foe slots. Call
RefreshCastAnimations after replacing stage meshes or importing/reloading clips.
The GC-tracked cache holds at most 64 mesh bindings; runtime additions can resolve
on their first cue, so prewarm before showing a battle. ResolveCastAnimation is
also callable for integration inspection without playing a clip. Restrict stage
slots to dedicated presentation actors as before.

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

The per-mesh update built the complete 159-file tracked plugin snapshot 36adcecc
in 242.56 seconds. Native Daedalus.Battle.CastAnimations passed in 0.022824
seconds with no test warnings/errors: two synthetic skeletons, folder-local
attack/hurt selection, wrong-skeleton refusal, compatible override retention,
fallback from an incompatible override, and missing/null/component refusal.
See battle-cast-animation-proof.json. The whole native-test editor log had
errors=0 warnings=1 (an editor layout-version notice), distinct from the clean
test result. Later main changes and Java cabinets are outside this snapshot.

A private Python commandlet copied Claude's existing 13 Gallery casts (152 native
art files), verified every copied hash, and resolved all 26 Attack/Hurt clips
through the native stage API. Its editor log had errors=0 warnings=0; the
commandlet body took 0.68 seconds, excluding startup. Art hashes remained intact
afterward. Meshes reside below a repeated cast-ID/SkeletalMeshes subfolder, and
clip names concatenate the mesh name and role without an underscore. The probe
discovers the actual package paths rather than assuming a flat import.
See battle-cast-imported-proof.json for all paths and input hashes. No assets
or maps were saved and the shared editor was not contacted. Director subscription,
other realm casts, animation playback, return to idle, camera/FX/audio, cooking
and rendered battle acceptance remain open.
