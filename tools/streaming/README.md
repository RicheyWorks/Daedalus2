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
- BlenderBoss original R1 pin (2026-10-18): disk 16,348 KiB = ceil(16,739,484 bytes), the 67 BIP1 packets in the original `data/islands/blenderboss/flagship.bip.json` (sha256 a00fb9ca...09a9). File-only, with blender-team consent (47979, receipt 47991).
- BlenderBoss current R2 pin (reconciled 2026-10-26): disk 18,460 KiB = ceil(18,902,836 bytes), the accepted 67-packet manifest at `45f1f1a882fed09e9380562616962703867afba4` (sha256 b188f1b41c87f0fbecda439eea21cddfbb0455285b3a8058eee2138c0a580a2c). Blender-team READY 50054/50055 and buffffff acceptance 50079 identify that source revision. `test_dsb.py` checks the exact manifest hash, packet-byte sum, KiB rounding and generated BlenderBoss row. The generated `streaming.dsb` follows this pin; RAM remains the placement-count ESTIMATE. No packet re-export or native measurement is implied.

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

## Breakwater Queue (contest G126, quest q_breakwater_queue)
- `breakwater_queue.py`: DiskSaver Island bounded-queue minigame. Save writes arrive in calm trickles and storm swells; the crane lands a fixed number per tick and the rest wait behind a bounded breakwater, where a full queue drops arrivals. A tuned capacity keeps drops and waits in budget through the storm season; a short breakwater drops every swell and a long one bloats until writes wait for ages. Every write is accounted for. Keys come from G86 Compaction Shoals (`breakwater_queue_test.py`; CI `Breakwater Queue`). Rules: `docs/islands/DISKSAVER-BREAKWATER-QUEUE.md`.

## Lighthouse Backoff (contest G134, quest q_lighthouse_backoff)
- `lighthouse_backoff.py`: DiskSaver Island retry-policy minigame. The archive lighthouse goes dark and every save-write boat is turned away; once lit, the keeper berths a fixed number per tick. Fixed retries hammer the dark tower and blow the retry budget; exponential backoff without jitter keeps the fleet in lockstep so each wave overruns the berths and misses the deadline; full jitter spreads the fleet and wins. Every write is accounted for. Keys come from G86 Compaction Shoals (`lighthouse_backoff_test.py`; CI `Lighthouse Backoff`). Rules: `docs/islands/DISKSAVER-LIGHTHOUSE-BACKOFF.md`.

## The Storm Season Archive (contest G136, quest q_storm_season_archive)
- `storm_season_archive.py`: DiskSaver Island story chapter. Seven acts run the landed G99 Bloom Buoys, G105 Hash Ring Atolls, G110 Quorum Quays, G113 Snapshot Shells, G120 Garbage Gulls, G123 Prefetch Pelicans and G126 Breakwater Queue games read-only on their shipped data (tuned choice or that game's trap). New mechanic: the end-of-season archive audit deals every G86 save to one act's storm, accounts for every save, checks a SHA-256 chain over the act records (tampering is caught) and grades gold / pass / fail; the result goes out as a G12 activity-result-v1 receipt (`storm_season_archive_test.py`; CI `Storm Season Archive`). Rules: `docs/islands/DISKSAVER-STORM-SEASON-ARCHIVE.md`.

## Two-Bell Commit (contest G144, quest q_two_bell_commit)
- `two_bell_commit.py`: DiskSaver Island atomic-commit minigame. Each save move between islands is one transaction (source deletes, destination writes); participants can refuse and the coordinator can crash mid-decision. One-phase commit tears moves into lost or doubled saves; two-phase commit without a decision log presumes abort after a crash and still loses saves; two-phase with the decision logged before it is rung recovers every move within the lock budget. Every save ends on exactly one island. Keys come from G86 Compaction Shoals (`two_bell_commit_test.py`; CI `Two-Bell Commit`). Rules: `docs/islands/DISKSAVER-TWO-BELL-COMMIT.md`.

## Barnacle Scrub (contest G151, quest q_barnacle_scrub)
- `barnacle_scrub.py`: DiskSaver Island silent-corruption minigame. Each save is kept as two copies and barnacles rot random copies; a scrub diver reads both copies round robin. Checksums plus a tuned scrub rate keep losses and reads in budget; too slow a diver lets both copies rot between visits, too fast a diver blows the read budget, and scrubbing without checksums copies rot over good copies. Keys come from G86 Compaction Shoals (`barnacle_scrub_test.py`; CI `Barnacle Scrub`). Rules: `docs/islands/DISKSAVER-BARNACLE-SCRUB.md`.

## Toll Bridge Tokens (contest G158, quest q_toll_bridge_tokens)
- `toll_bridge_tokens.py`: DiskSaver Island rate-limiting minigame over the G126 Breakwater Queue harbour waves (read-only). The archive bridge sways if too many writes cross in any window; an open gate and a fixed-window counter (2x the limit at a block edge) both sway it, and a token bucket wins when the jar is sized right. Envelope burst + (t-1) x rate pinned and tight under saturation; largest safe jar equals brute force (`toll_bridge_tokens_test.py`; CI `Toll Bridge Tokens`). Rules: `docs/islands/DISKSAVER-TOLL-BRIDGE-TOKENS.md`.

## Tide Clocks (contest G166, quest q_tide_clocks)
- `tide_clocks.py`: DiskSaver Island causality minigame over G86 islands and keys (read-only). Islands edit the same saves between ferry syncs; wall-clock and Lamport last-writer-wins silently drop concurrent edits, while vector clocks keep concurrent siblings for the Merge Keeper and lose nothing. Vector order equals a brute-force happens-before oracle, Lamport is consistent but not complete, detected conflicts equal the oracle (`tide_clocks_test.py`; CI `Tide Clocks`). Rules: `docs/islands/DISKSAVER-TIDE-CLOCKS.md`.

## Lighthouse Leases (contest G171, quest q_lighthouse_leases)
- `lighthouse_leases.py`: DiskSaver Island leader-lease minigame over the G86 islands as keepers (read-only). One keeper may write the save log per epoch; no lease splits the brain, a naive lease on a drifting clock overruns, a drift guard still loses to a pause between check and write, and fencing tokens make the store reject every stale write. Smallest safe guard equals brute force, stale count equals an oracle, seeded replay is deterministic (`lighthouse_leases_test.py`; CI `Lighthouse Leases`). Rules: `docs/islands/DISKSAVER-LIGHTHOUSE-LEASES.md`.

## Tidemark Chunks (contest G175, quest q_tidemark_chunks)
- `tidemark_chunks.py`: DiskSaver Island content-defined dedup minigame over the G86 islands' saves (read-only), vault quota = G39 Byte Spring budget cap (read-only). Whole-file storage rewrites every edited save, fixed-size chunks lose all dedup after one inserted byte, and a locked rolling-hash chunker (window 16, 7 mask bits) cuts on content so boundaries resync and the vault fits. Rolling hash = from scratch, exact rebuild, mean chunk vs Monte Carlo, cost = brute-force oracle, golden fixture, seeded replay (`tidemark_chunks_test.py`; CI `Tidemark Chunks`). Rules: `docs/islands/DISKSAVER-TIDEMARK-CHUNKS.md`.

## Bottle Census (contest G179, quest q_bottle_census)
- `bottle_census.py`: DiskSaver Island distributed-snapshot minigame over the G86 islands (read-only). Credits sail between islands in bottles on FIFO lanes while Harbourmaster Tilde counts them; a naive sum of island balances misses credits in transit, and Chandy-Lamport markers record lane state so the census is exact. Marker total exact, consistent cut, lane state = in-transit oracle, non-FIFO breaks, seeded replay (`bottle_census_test.py`; CI `Bottle Census`). Rules: `docs/islands/DISKSAVER-BOTTLE-CENSUS.md`.

## Census Budget Beacons (G206, quest q_census_beacons)
- `census_budget.py`: reads the Codex World Census `census.json` (read-only), prices each island with the DSB 1 estimate (same constants as `dsb_manifest.py`) and flags islands whose RAM or disk breaks the resident-set budget: red (`ram_over`/`disk_over`), amber (within `warn_permille`), green. Per world it reports totals, `fits_all_resident` and `max_resident` (= brute-force oracle). The report's `beacon` field lights each island's lighthouse in game (`census_budget_test.py`; CI `Census Budget Beacons`). Rules: `docs/islands/DISKSAVER-CENSUS-BEACONS.md`.

## Ebb Tide Eviction (G253, quest q_ebb_eviction)
- `ebb_eviction.py`: reads the G206 `census_budget.py` report (read-only) and, for each world over the RAM budget, plans which resident islands to unload first: least total reload weight, then fewest islands, home slot pinned. Exact knapsack DP = brute-force oracle; greedy heaviest-first and lowest-weight-first are reported beside it. The plan's `tide` (`slack`/`ebb`/`stranded`) drives Ebb Warden Marlo in game (`ebb_eviction_test.py`; CI `Ebb Tide Eviction`). Rules: `docs/islands/DISKSAVER-EBB-EVICTION.md`.
