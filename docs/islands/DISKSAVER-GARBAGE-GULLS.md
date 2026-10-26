# Garbage Gulls (contest G120, DiskSaver Island)

Quest `q_garbage_gulls`, NPC **Gullmother Brine**. Code: `tools/streaming/garbage_gulls.py`,
tests `tools/streaming/garbage_gulls_test.py`, data `data/islands/disk-saver/garbage-gulls-v1.json`,
CI job `Garbage Gulls`.

## Rules
- The heap starts with the G86 Compaction Shoals saves (islands x keys_per_island, read-only); each island is a
  root holding its saves, and each save's `fragments_per_save` fragments link back to it (a loop).
- Every window storms cut `replaced_per_window` saves loose and the tide washes in new ones. A cut save and its
  fragments drift as an unreachable loop.
- Mark-and-sweep gulls: mark every object reachable from the islands, then sweep the heap.
  Work = marked + heap size, from a season `work_budget`. The keeper picks `sweep_every` windows (0 = never).
- Win: heap never above `heap_cap`, total work within budget, and no reachable save is ever freed.

## Intervals (shipped data, seed 1, cap 2900 objects, budget 45000 work)
| Scheme | peak heap | work | Result |
|---|---|---|---|
| sweep every 6 windows | 2800 | 31680 | won 40/40 |
| sweep every 5 or 7 | 2720 / 2880 | 41600 / 26800 | won 40/40 |
| sweep every window | 2400 | 195200 | fails: gulls worn out (work) |
| sweep every 4 | 2640 | 51200 | fails: work |
| sweep every 8 | 2960 | 27200 | fails: heap overflow |
| never sweep | 5600 | 0 | fails: heap overflow |
| reference counting | 5600 | 0 | fails: every loop leaks |

## Run
`python tools/streaming/garbage_gulls.py data/islands/disk-saver/garbage-gulls-v1.json [--sweep-every N] [--refcount]`
