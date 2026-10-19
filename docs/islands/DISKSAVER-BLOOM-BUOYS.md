# Bloom Buoys (contest G99, DiskSaver Island)

Quest `q_bloom_buoys`, NPC **Buoykeeper Fennick**. Code: `tools/streaming/bloom_buoys.py`,
tests `tools/streaming/bloom_buoys_test.py`, data `data/islands/disk-saver/bloom-buoys-v1.json`,
CI job `Bloom Buoys`.

## Rules
- Each reef (G86 Compaction Shoals islands, keys_per_island saves each, read-only) has a buoy: a Bloom filter
  of `bits_per_key` x keys bits holding every save on that reef. The buoys float over the G90 mangrove replicas.
- The keeper picks the hash count (`hashes`, 1..32). Probes use double hashing over zlib.crc32.
- Each window brings `lookups` requests; `absent_permille` of them are for saves that were never sunk there.
- "Not here" (any probe bit clear) skips the dive. "Maybe" costs a dive; a dive that finds nothing is wasted.
- Win: every window wastes at most `max_wasted` dives, and no buoy ever says "not here" for a save that is there.

## Hash counts (shipped data, seed 1, 10 bits per key)
| Buoy | worst window (budget 8) | total wasted | Result |
|---|---|---|---|
| 7 hashes (10 x ln 2) | 7 | 81 | won 30/30 |
| 5, 6 or 8 hashes | 4-7 | 52-67 | won 30/30 |
| 1 hash | 37 | 726 | fails: wasted dives |
| 20 hashes | 20 | 438 | fails: wasted dives |
| no buoy | 268 | 7300 | fails: wasted dives |

## Run
`python tools/streaming/bloom_buoys.py data/islands/disk-saver/bloom-buoys-v1.json [--hashes N] [--no-buoys]`
