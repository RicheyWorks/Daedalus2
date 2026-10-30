# pcg-ecology/tools

Early Unreal-bridge helpers from the 2026-10-12 PCG ecology work, moved off the box so nothing lives only there.

- `probe_pcg.py`: run inside the editor (via `../ue_send.py probe_pcg.py`). Lists which PCG classes and graph/component
  methods the installed UE build exposes to Python, and writes `probe.json` (path hard-coded to the
  `Daedalus2-pcg-ecology` checkout). Read-only.
- `ue_send2.py`: the variant of `../ue_send.py` that first sent `unattended: False`, so replies stay tied to our job id
  when two bots run code at once. `../ue_send.py` is the maintained client; keep this one for history and comparison.