# Prefetch Pelicans (contest G123, DiskSaver Island)

Quest `q_prefetch_pelicans`, NPC **Flockwarden Pim**. Code: `tools/streaming/prefetch_pelicans.py`,
tests `tools/streaming/prefetch_pelicans_test.py`, data `data/islands/disk-saver/prefetch-pelicans-v1.json`,
CI job `Prefetch Pelicans`.

## Rules
- The path is the G86 Compaction Shoals saves in order (islands x keys_per_island, read-only), wrapping around.
- Pelicans (prefetches) take `latency` ticks to land; at most `flights_per_tick` leave per tick.
  The keeper picks `depth`: how many chunks ahead are kept in flight or landed.
- Each tick the traveller steps onto the next chunk if it has landed, else stalls.
- With chance `jump_permille` per tick the traveller ferries to the start of a random island; every chunk
  in flight or landed outside the new readahead window is wasted.
- Win: at most `max_stalls` stalled ticks and at most `max_wasted` wasted flights over the season.

## Depths (shipped data, seed 1, latency 4, 2 flights/tick, 52 ferries)
| Depth | stalls (max 420) | wasted (max 260) | Result |
|---|---|---|---|
| 5 (latency + 1) | 207 | 206 | won |
| 6 | 207 | 256 | won |
| 4 | 744 | 163 | fails: stalls |
| 1 | 2419 | 42 | fails: stalls |
| 7 | 207 | 305 | fails: waste |
| 32 | 207 | 1359 | fails: waste |

## Run
`python tools/streaming/prefetch_pelicans.py data/islands/disk-saver/prefetch-pelicans-v1.json [--depth N]`
