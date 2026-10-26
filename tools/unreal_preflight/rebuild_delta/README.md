# rebuild_delta

Engine-free helper for the batched rebuild: lists every first-parent merge after the last
rebuilt sha that touches plugin build inputs (`.h`, `.cpp`, `.cs`, `.uplugin` under `engines/unreal/`).

    python tools/unreal_preflight/rebuild_delta/rebuild_delta.py d209f50a origin/main

Read-only git. It refuses when the rebuilt sha is not an ancestor of the target. It doesn't touch the editor, locks or UBT.
