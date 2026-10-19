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
