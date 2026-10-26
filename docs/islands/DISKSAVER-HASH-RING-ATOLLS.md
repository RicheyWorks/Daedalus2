# Hash Ring Atolls (contest G105, DiskSaver Island)

Quest `q_hash_ring_atolls`, NPC **Ringwarden Tamsin**. Code: `tools/streaming/hash_ring_atolls.py`,
tests `tools/streaming/hash_ring_atolls_test.py`, data `data/islands/disk-saver/hash-ring-atolls-v1.json`,
CI job `Hash Ring Atolls`.

## Rules
- Saves are the G86 Compaction Shoals islands x keys_per_island (read-only), 1200 in the shipped data.
  The atolls hold the cold archives (G59).
- Each live atoll plants `vnodes` markers on a 32-bit ring (crc32 + fmix32). A save belongs to the first marker
  clockwise from its hash.
- `events` seeded rise (join) and sink (leave) events; between 4 and 10 atolls stay above water.
- After each event every save whose owner changed is ferried. An event may ferry at most `max_moved_permille`
  of all saves, and the busiest atoll may hold at most `load_cap_permille` of the average load.
- Every save is checked to sit on exactly the atoll the ring names after every event.

## Schemes (shipped data, seed 1, cap 360 moved / 1600 permille load)
| Scheme | worst moved | total moved | worst load | Result |
|---|---|---|---|---|
| ring, 64 markers per atoll | 286 | 4991 | 1365 | won 24/24 |
| ring, 32 or 128 markers | 306 / 267 | 4823 / 5088 | 1383 / 1318 | won 24/24 |
| ring, 1 marker | 536 | 5502 | 3805 | fails: overloaded atoll |
| ring, 8 markers | 283 | 4971 | 1758 | fails: overloaded atoll |
| mod-N re-shard | 1036 | 23508 | 1172 | fails: ferries swamped |

## Run
`python tools/streaming/hash_ring_atolls.py data/islands/disk-saver/hash-ring-atolls-v1.json [--vnodes N] [--mod-n]`
