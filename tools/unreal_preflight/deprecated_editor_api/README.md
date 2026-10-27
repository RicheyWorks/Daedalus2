# Deprecated editor Python API scan

Read-only. It lists every `unreal.EditorLevelLibrary` (and related) call, which UE 5.0 deprecated in favour of editor subsystems, together with the subsystem replacement for each call. Calls that save a level are flagged `SAVE` so the owner can check they can't save the persistent `DaedalusWorld`.

    python tools/unreal_preflight/deprecated_editor_api/deprecated_editor_api.py --root . --out deprecated-editor-api.md

The scan never edits a script, so each owning team fixes its own. The exit code is 0 unless you pass `--fail-on-hits`. CI runs only the engine-free unit tests.
