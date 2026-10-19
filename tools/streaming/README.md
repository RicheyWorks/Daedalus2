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

## Byte Spring cistern (contest G39, quest q_byte_spring)
- `byte_spring.py`: DiskSaver Island minigame that composes `dsb.py`. DSB rows become islands that drink water, and the DSB 1 picker chooses the start residents. A seeded, integer-only tick sim (`byte_spring_test.py`, 46 tests; CI `Byte Spring cistern`). Rules: `docs/islands/DISKSAVER-BYTE-SPRING.md`.

## Save Vault Keeper (contest G59, quest q_save_vault)
- `save_vault.py`: DiskSaver Island save-state minigame. A quota'd vault of content-addressed (dedupe) snapshot chunks, a bandwidth-limited and hash-verified Reef mirror, the newest snapshot per island pinned, and pruning an unmirrored snapshot = lost work. The quota comes from the G39 Byte Spring budget cap (`save_vault_test.py`; CI `Save Vault Keeper`). Rules: `docs/islands/DISKSAVER-SAVE-VAULT.md`.

## Defrag Tide (contest G63, quest q_defrag_tide)
- `defrag_tide.py`: DiskSaver Island disk-layout minigame. G39 island caches are scattered over a block shelf. The player moves N blocks per tide, the tide erodes free blocks into bad ones, and the goal is to reach the weighted seek target (`defrag_tide_test.py`; CI `Defrag Tide`). Rules: `docs/islands/DISKSAVER-DEFRAG-TIDE.md`.

## Parity Reef (contest G67, quest q_parity_reef)
- `parity_reef.py`: DiskSaver Island redundancy minigame. Caches are striped over reef stones with rotating XOR parity, storms smash a stone, a verified rebuild runs N blocks per tick, and a double loss in a row = data lost. Stripes come from the G63 Defrag Tide caches (`parity_reef_test.py`; CI `Parity Reef`). Rules: `docs/islands/DISKSAVER-PARITY-REEF.md`.

## Tide Chart Cache (contest G70, quest q_tide_chart)
- `tide_chart_cache.py`: DiskSaver Island RAM-pool caching minigame. Seeded island requests come in, each miss stalls for the island's cost, and the keeper evicts by reading the tide chart (Belady over a visible window) or by LRU. The pool and islands are built from G39 Byte Spring (`tide_chart_cache_test.py`; CI `Tide Chart Cache`). Rules: `docs/islands/DISKSAVER-TIDE-CHART.md`.

## Driftwood Codes (contest G76, quest q_driftwood_codes)
- `driftwood_codes.py`: DiskSaver Island packing minigame. Tie chunk-kind bundles into a raft; the code length is the depth; packed bits must fit the reef slot. Huffman's rule (lightest pair) hits the optimum and tying in order is the trap. Canonical prefix codes round-trip, and the frequencies can come from the G70 tide chart (`driftwood_codes_test.py`; CI `Driftwood Codes`). Rules: `docs/islands/DISKSAVER-DRIFTWOOD-CODES.md`.

## Coral Wear (contest G78, quest q_coral_wear)
- `coral_wear.py`: DiskSaver Island wear-leveling minigame. Saves move between flash-like coral cells with seeded endurance, and worn cells retire. Dynamic leveling, plus static relocation of cold archives, keeps the shelf alive. Hot and cold saves come from the G70 tide chart plus G59 archives (`coral_wear_test.py`; CI `Coral Wear`). Rules: `docs/islands/DISKSAVER-CORAL-WEAR.md`.

## Journal Tide (contest G79, quest q_journal_tide)
- `journal_tide.py`: DiskSaver Island write-ahead-journal minigame. Saves are buffered and then committed as CRC32 records, storm surges lose the buffer, and a torn mid-commit record is caught on replay. Paced commits beat the commit-everything and never-commit traps. The saves come from G78 Coral Wear (`journal_tide_test.py`; CI `Journal Tide`). Rules: `docs/islands/DISKSAVER-JOURNAL-TIDE.md`.

## Compaction Shoals (contest G86, quest q_compaction_shoals)
- `compaction_shoals.py`: DiskSaver Island LSM-tree minigame. Writes fill a memtable, flush to sorted runs, and compactions merge levels. Lookups pay read amplification and compactions spend write amplification from an io budget. Tuned leveled compaction beats the never-compact and compact-every-flush traps, and every lookup is checked against a dict. Writes come from G79 Journal Tide (`compaction_shoals_test.py`; CI `Compaction Shoals`). Rules: `docs/islands/DISKSAVER-COMPACTION-SHOALS.md`.

## Merkle Mangroves (contest G90, quest q_merkle_mangroves)
- `merkle_mangroves.py`: DiskSaver Island anti-entropy minigame. The shore and mangrove replicas drift as storms flip saves. Sync compares Merkle tree hashes, skips matching subtrees and copies only the differing leaves, all within a bandwidth budget. Merkle descent beats the flat leaf-scan and full-copy traps, and the replicas are checked equal after every window. Keys come from G86 Compaction Shoals (`merkle_mangroves_test.py`; CI `Merkle Mangroves`). Rules: `docs/islands/DISKSAVER-MERKLE-MANGROVES.md`.

## Bloom Buoys (contest G99, quest q_bloom_buoys)
- `bloom_buoys.py`: DiskSaver Island Bloom filter minigame. A buoy over each reef holds a Bloom filter of the saves below (G86 Compaction Shoals keys, read-only). "Not here" skips a dive; "maybe" costs one. Under a fixed bit budget per key the keeper picks the hash count: about bits x ln 2 keeps wasted dives in budget, while one hash, too many hashes or no buoy flood the reef. Never a false negative (`bloom_buoys_test.py`; CI `Bloom Buoys`). Rules: `docs/islands/DISKSAVER-BLOOM-BUOYS.md`.

## Hash Ring Atolls (contest G105, quest q_hash_ring_atolls)
- `hash_ring_atolls.py`: DiskSaver Island consistent-hashing minigame. Archive atolls rise and sink through the season; every save belongs to the first atoll marker clockwise from its hash. Each event may ferry only a budget of saves and no atoll may exceed a load cap. Enough virtual markers per atoll wins; one marker per atoll overloads atolls and mod-N re-sharding swamps the ferries. Every save is checked on the right atoll after every event. Keys come from G86 Compaction Shoals (`hash_ring_atolls_test.py`; CI `Hash Ring Atolls`). Rules: `docs/islands/DISKSAVER-HASH-RING-ATOLLS.md`.

## Quorum Quays (contest G110, quest q_quorum_quays)
- `quorum_quays.py`: DiskSaver Island quorum-replication minigame. Every save is kept on five quays with a version tally, and storms close quays each tick. Writes count once W open quays have them; reads ask R quays and trust the highest tally. R + W > quays means no stale read, and the storms decide how large the quorums can be while the harbour stays available. Only the majority quorum wins the shipped season; R=W=1 serves stale saves and write-all stalls. Keys come from G86 Compaction Shoals (`quorum_quays_test.py`; CI `Quorum Quays`). Rules: `docs/islands/DISKSAVER-QUORUM-QUAYS.md`.

## Snapshot Shells (contest G113, quest q_snapshot_shells)
- `snapshot_shells.py`: DiskSaver Island copy-on-write snapshot minigame. Each dusk a shell (snapshot) of every save is pressed; unchanged saves are shared with earlier shells, so only changed versions cost space. Villagers ask for the island as it was up to 8 dusks ago and must get that exact snapshot. Keeping just enough shells wins; too few cannot restore, and keeping every shell or full-copy shells overflow the space budget. Keys come from G86 Compaction Shoals (`snapshot_shells_test.py`; CI `Snapshot Shells`). Rules: `docs/islands/DISKSAVER-SNAPSHOT-SHELLS.md`.

## Garbage Gulls (contest G120, quest q_garbage_gulls)
- `garbage_gulls.py`: DiskSaver Island garbage-collection minigame. Every save carries fragments that loop back to it; storms cut saves loose and the tide brings new ones, so unreachable loops drift on the beach. Mark-and-sweep gulls clear them at a work cost. A tuned sweep interval keeps the heap under its cap within the work budget; sweeping every window wears the gulls out, never sweeping buries the beach, and reference counting leaks every loop. A sweep never frees a reachable save. Keys come from G86 Compaction Shoals (`garbage_gulls_test.py`; CI `Garbage Gulls`). Rules: `docs/islands/DISKSAVER-GARBAGE-GULLS.md`.

## Prefetch Pelicans (contest G123, quest q_prefetch_pelicans)
- `prefetch_pelicans.py`: DiskSaver Island streaming-readahead minigame. A traveller walks the save path chunk by chunk while pelicans prefetch chunks with a fixed latency and a flights-per-tick limit; seeded ferries to other islands waste every chunk flown for the old stretch. A readahead of latency + 1 keeps both stalls and waste in budget; shallower readahead stalls and deeper readahead wastes. Path comes from G86 Compaction Shoals (`prefetch_pelicans_test.py`; CI `Prefetch Pelicans`). Rules: `docs/islands/DISKSAVER-PREFETCH-PELICANS.md`.
