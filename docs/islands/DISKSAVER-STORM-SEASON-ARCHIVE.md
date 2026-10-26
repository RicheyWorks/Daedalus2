# The Storm Season Archive (contest G136, DiskSaver Island story chapter)

Quest `q_storm_season_archive`, NPC **Archivist Maren**. Code: `tools/streaming/storm_season_archive.py`,
tests `tools/streaming/storm_season_archive_test.py`, data `data/islands/disk-saver/storm-season-archive-v1.json`,
CI job `Storm Season Archive`. Requested by buffffff (team link 49977).

## The arc
One storm season, seven stations. Each act imports a landed DiskSaver game and runs it **read-only** on its own
shipped data (no module or data file is changed; a test hashes them before and after):

| Act | Gap | Tuned choice | Trap |
|---|---|---|---|
| bloom_buoys | G99 Bloom Buoys | shipped hash count | dive without buoys |
| hash_ring_atolls | G105 Hash Ring Atolls | shipped vnodes | re-shard by hash mod N |
| quorum_quays | G110 Quorum Quays | shipped R/W | R=W=1 |
| snapshot_shells | G113 Snapshot Shells | copy-on-write shells | full copies |
| garbage_gulls | G120 Garbage Gulls | mark-and-sweep | reference counting |
| prefetch_pelicans | G123 Prefetch Pelicans | shipped depth | depth 1 |
| breakwater_queue | G126 Breakwater Queue | capacity 140 | capacity 40 |

## New mechanic: the end-of-season archive audit
- Every G86 Compaction Shoals save (6 islands x 200 keys = 1200) is dealt by a seeded shuffle to exactly one act's
  stake (180/180/180/180/160/160/160), any rest to the safe harbour. A lost act loses its stake.
- Each act record (act, gap, quest, choice, status, reason, full result) is chained:
  `entry = sha256(prev + canonical(record))`, starting from 64 zeros. The audit recomputes the chain; an edited,
  swapped or missing record breaks it, and a broken chain or an unaccounted save fails the audit outright.
- Grade: **gold** every act won; **pass** survived permille >= `pass_permille` (800); otherwise **fail**.
  Shipped data: all tuned = gold (1200/1200); one trap = pass (1020 or 1040); two traps = fail (e.g. 860, 716 permille).

## G12 receipt
`g12_receipt` returns the chapter result in the activity-result-v1 wire order (`docs/contracts/activity-result-v1`):
activity `disksaver.storm-season-archive`, mode AUTHORITATIVE, outcome COMPLETED for gold/pass and FAILED for fail,
the keeper as one LIFE participant, measures `acts_won`, `saves_lost`, `saves_survived`, `survived_permille`, one
source event ref per act, `resultId` and `verificationRef` from the chain head. `receipt_digest` is SHA-256 of the
compact JSON.

## Run
`python tools/streaming/storm_season_archive.py data/islands/disk-saver/storm-season-archive-v1.json [--trap ACT ...]`
