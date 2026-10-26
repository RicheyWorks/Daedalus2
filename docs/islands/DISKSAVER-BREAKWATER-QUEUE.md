# Breakwater Queue (contest G126, DiskSaver Island)

Quest `q_breakwater_queue`, NPC **Cranemaster Odo**. Code: `tools/streaming/breakwater_queue.py`,
tests `tools/streaming/breakwater_queue_test.py`, data `data/islands/disk-saver/breakwater-queue-v1.json`,
CI job `Breakwater Queue`.

## Rules
- Save writes (keys from G86 Compaction Shoals, read-only) arrive each tick: 0..`calm_max` plus a swell of
  `swell_size` with chance `swell_permille` (`storm_swell_permille` during the storm season).
- The crane lands `drain_per_tick` writes a tick, oldest first. Waiting writes sit in a breakwater queue of
  `capacity` slots; a write that arrives at a full queue is dropped.
- Win: at most `max_dropped` dropped writes and no landed write waited more than `max_wait` ticks.
  Every write is accounted for (landed, dropped or still queued).

## Capacities (shipped data, seed 1, drop budget 700, wait budget 25 ticks)
| Capacity | dropped | worst wait | Result |
|---|---|---|---|
| 140 | 607 | 23 | won |
| 130 / 150 | 681 / 547 | 21 / 24 | won |
| 40 | 2494 | 6 | fails: dropped |
| 120 | 761 | 19 | fails: dropped |
| 160 | 496 | 26 | fails: wait (bufferbloat) |
| 1000 | 0 | 99 | fails: wait (bufferbloat) |

## Run
`python tools/streaming/breakwater_queue.py data/islands/disk-saver/breakwater-queue-v1.json [--capacity N]`
