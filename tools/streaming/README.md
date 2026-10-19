# tools/streaming: DSB 1 island streaming budget tooling (disk-saver, ADR-063)

- `dsb.py`: Python port of the DSB 1 parser/writer/picker. `test_dsb.py` replays
  `engines/unreal/core-test/streaming_budget_parity.txt`, so Python = Java = C++ byte for byte.
- `dsb_manifest.py`: builds `data/islands/streaming.dsb` from every `data/islands/*/layout.json`
  (`origin_cm`, placement count) plus `data/islands/streaming_extra.json`. Costs are ESTIMATES
  (RAM 16 MiB + 24 KiB/placement, disk 4 MiB + 96 KiB/placement) until an island pins measured numbers with a
  `"streaming": {"ram_kib": N, "disk_kib": N}` block. The output is re-parsed before writing.

```
python tools/streaming/dsb_manifest.py -o data/islands/streaming.dsb     # regenerate
python tools/streaming/dsb_manifest.py --check data/islands/streaming.dsb # exit 1 if stale
python -m unittest tools/streaming/test_dsb.py                            # offline tests
```

The Unreal side (a subsystem that reads `streaming.dsb`, calls `Pick` as the player moves and loads/unloads
sublevels) belongs to unreal-team / codex-play-guard (sole Unreal writer); the plain-C++ header
`DaedalusStreamingBudgetCore.h` is ready for it.

## Measured costs (2026-10-18)
- `dsb_measure.py --content C:/Unreal/DaedalusRealm/Content -o data/islands/streaming_measured.json` sums package sizes in the folders listed in `data/islands/streaming_sources.json` (read-only; no editor needed). disk_kib is measured; ram_kib is the uncooked payload, an upper-bound proxy until an in-game memreport.
- Priority in `dsb_manifest.py`: a layout's own `streaming` pin, then the measurement, then the placement-count estimate.
- First run (23:24 PT Oct 18): DiskSaver 25,470 KiB disk / 25,015 KiB RAM proxy (341 files); (OddsReaper 140,682 / 139,310 was measured too, then dropped at 23:3x because disk-saver does not own it). BlenderBoss, Hephaestus and OddsReaper keep estimates until their owners list their asset folders.


## Owner-consented pins
- `data/islands/streaming_sources.json` rows may carry `"pin": {"disk_kib": N, ...}` with provenance; priority is layout `streaming` block, then pin, then measurement, then estimate.
- BlenderBoss (2026-10-18): disk 16,348 KiB = ceil(16,739,484 bytes), the 67 BIP1 packets in `data/islands/blenderboss/flagship.bip.json` (sha256 a00fb9ca...09a9, checked by test_dsb.py). File-only, with blender-team consent (47979, receipt 47991). RAM stays an ESTIMATE.

