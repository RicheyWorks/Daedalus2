# Prismheart title recovery r1 — source-only job

Status: **AUTHORED_AND_SOURCE_REVIEWED; NOT EXECUTED.** This narrows the missing input identified in visual-r3. It does not authorize generation, builds or browser use.

Entry point: `tools/rpg_demo/recover_title.py`. Prepared invocation from the primary repository:

```powershell
python tools/rpg_demo/recover_title.py
```

The command accepts no arguments. It reserves the new directory `artifacts/prismheart-visual-r3/title-recovery-r1/` atomically and refuses an existing directory. It verifies the five original917 recipe files against `data/assets/prismheart-visual-r3-title-recipe-pins.json` before importing them.

Only the original `title_backdrop("prism", frame)` for frames0–7, horizontal concatenation and original PNG writer are called. Expected output is `TitleBg_1x.png`,2560×224RGBA8, directly inside that directory. No original CLI/build, second realm, party loader or canonical JSON writer is called. The only external dependency is NumPy; its local availability remains unprobed.

The new directory also receives an exclusive `recovery-receipt.json` containing the last actual stage, source hashes, output hash/size when present, elapsed time, and success/error state. Failures and partial outputs remain for inspection. A generated/header-verified file still has visual/build acceptance pending. Receipt creation is ordinary file output, not a certified crash-durability guarantee.

A later permitted run must record actual process/argv/resource/start/terminal evidence and inspect the real file. If a prior attempt or output exists, hold and reconcile it; do not delete, overwrite or automatically retry. The helper has not been imported, syntax-checked or executed. No bitmap, tests, build, browser capture, Blender or native operation occurred in this source step.

Preserved v10/r2 input roots and595art/audio files are unchanged. The source-only recovery plan is separate from any future grant and from the existing published v10 artifact.
