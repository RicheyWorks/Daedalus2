# Compaction Shoals (contest G86, DiskSaver Island)

Quest `q_compaction_shoals`, NPC **Sorter Merge**. Code: `tools/streaming/compaction_shoals.py`,
tests `tools/streaming/compaction_shoals_test.py`, data `data/islands/disk-saver/compaction-shoals-v1.json`,
CI job `Compaction Shoals`.

## Rules
- Writes recovered from the G79 Journal Tide (same islands and weights, read-only) settle as an LSM tree.
- Puts and deletes fill a memtable of `memtable` keys. A full memtable flushes into a sorted run on level 0.
- A lookup checks the memtable, then probes runs newest first until it finds the key; a tombstone means deleted.
  Average runs probed per lookup is the **read amplification**.
- Compacting level i merges all its runs with level i+1 into one run on level i+1. Rows written (flushes plus
  compactions) are the **write amplification**, paid from `io_budget`. Tombstones drop only at the deepest level.
- Win: `io <= io_budget` and `probes_x100 <= max_probes_x100` at season end.
- Every lookup is checked against a plain dict, so the tree never returns a wrong value.

## Policies (shipped data, seed 1)
| Policy | io (budget 30000) | probes x100 (cap 300) | Result |
|---|---|---|---|
| leveled (L0 trigger 4, ratio 10) | 17363 | 223 | won |
| never compact | 3488 | 1683 | fails: read amplification |
| compact every flush | 58645 | 96 | fails: io budget |

## Run
`python tools/streaming/compaction_shoals.py data/islands/disk-saver/compaction-shoals-v1.json [--policy leveled|never|every_flush]`
