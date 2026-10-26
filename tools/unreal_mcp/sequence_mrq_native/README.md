# Sequence and MRQ delivery checkpoint

This folder contains byte-exact source copies from the sole Codex operator's bounded Unreal 5.8.4 integration. `evidence.json` pins the originals and retained native receipts. It is a local delivery checkpoint for the existing [draft PR410](https://github.com/RicheyWorks/Daedalus2/pull/410); staging this folder made no Git or engine calls.

## Host contract

These `.inc` files are callback bodies, not standalone scripts. The owning host supplies the current editor/process identity, normal custody/resource admission, protected `before`, actual `unreal`, `snapshot()`, `qualify()` and `record()`, unique plans/output paths and retained dispatch journals. Never replay an executed operation entry.

- `public_sequence_key_facts_r2.inc`: compile/exec the definitions before `# ENTRY:` to obtain `public_sequence_facts(actual_loaded_sequence)`. It reads bounded public binding/cut/transform Double and Spawn Bool key/default metadata. It avoids protected Spawnables/templates and does not evaluate motion. Binding resolution may update the MovieScene compiled hierarchy cache. Full opaque binding-space equality is not claimed.
- `sequence_owned_copy_body_r2.inc`: prepend those public definitions; the host supplies the actual prepared `plan` and independently verified `process_generation`. Its function prefix ends before the entry `result = {`. The actual operation duplicates once, edits one existing key, evaluates through the supported Sequencer editor context, saves only the owned copy, and restores protected state.
- `sequence_reopen_body_r1.inc`: prepend both definition prefixes, then supply the same plan and a genuinely fresh generation. This is the exact completed-run readback, bound to its retained operation receipt and saved package hash, not a generic reopen loop.
- `mrq_owned_start_body_r3.inc`: the host supplies the exact one-frame plan and substitutes `__OPERATION_ID__`/`__MRQ_JOURNAL_PATH__`. It retains an owned transient queue/executor and async callbacks; a later guarded call invokes the retained module's `reconcile(snapshot, qualify)`. It does not clear the shared queue. The delivered executed packet is consumed, not permission to resubmit.

## Actual outcome and limits

Original: `/Game/YTM/Seq/WB_Flythrough_YTMIsland.WB_Flythrough_YTMIsland`.
Owned copy: `/Game/CodexToolEvaluation/EpicIntegrationR1/Sequence/WB_Edit_2926878514f6.WB_Edit_2926878514f6`.

The named sequence acceptance passed after a real process reopen: Location.X at display frame 0 changed from 2431.074462890625 to 2531.074462890625 cm, common-frame evaluated camera motion was checked, the saved copy persisted, and original/protected work remained preserved. The named receipt is not general sequence, animation, or all-integration qualification; its `native_runtime_qualified` stays false.

The built-in `MovieRenderPipeline` project plugin was activated by one appended descriptor entry (`Name`, `Enabled:true`), with descriptor SHA256 `83e12b29...` -> `8039a42c...`. The full user project descriptor is deliberately absent from this source checkpoint. Its normal reopen also supplied the sequence persistence generation.

Exactly one MRQ job/submission rendered original WB frame 90 at 320x180, samples 1/1. The executor reported success and the PNG decoded correctly, but actual image review found only sky/background. **Render acceptance is HELD**, not a scene-content pass. No cause is inferred from the PNG; a corrected job needs separately bound level/camera/streaming evidence. Normal compute release and unchanged shared queue/protected files are retained.

Six focused synthetic tests of the public-reader boundary passed previously. They check hidden-field avoidance, proxy/GUID/sequence negatives, defaults and Spawn Bool metadata. They are distinct from the real edit/save/reopen and MRQ evidence. No tests were rerun while copying this folder. Blocked material/UCX publication sources are excluded and their stops remain in force.
