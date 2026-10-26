# DiskSaver Island: Tide Chart Cache (contest G70, quest `q_tide_chart`)

## Story
The Reef is safe (G67), but island visitors still wait at the harbour mouth. The island's
hot pool (RAM) berths only so many caches, and the home cache never leaves. Harbourmaster
Belady posts a tide chart of which islands will ask next. The quest is to read it and clear
the berth that will be needed last, so the season's stalls stay within budget.

## Mechanics (code: `tools/streaming/tide_chart_cache.py`)
- `requests(config)` makes a seeded request list, weighted per island.
- Each tide, the requested island is either a **hit** (free) or a **miss**. A miss stalls
  for the island's `cost_kib`, and residents are evicted until it fits in `capacity_kib`.
- The keeper sees the next `chart_len` requests. `chart_policy` is Belady over the visible
  chart: evict the island needed furthest ahead, with ties going to the larger cache.
  `lru_policy` is the lazy keeper.
- If the total stall goes over `stall_budget_kib`, the game is **failed: stall_over_budget**.
  Surviving all `tides` is a **win**. Score = budget left, in permille.
- With the shipped tuning, reading the chart wins on 39 of seeds 1-40, while LRU wins on
  27. The chart is never worse than LRU on any of those seeds.

## Daedalus tie-in
- `config_from_byte_spring()` builds the shipped data from G39 Byte Spring. The islands are
  its non-keystone islands (cost_kib, weight = priority + 1), and the capacity is its
  budget cap (600) minus the pinned home cache (120) = 480 KiB, in DSB 1 units.
- It uses the same LCG as G39, G59, G63 and G67, and `receipt()` returns a G12-style
  activity receipt.

## Checks
`python -m unittest tools/streaming/tide_chart_cache_test.py -v`; the CI job is
`Tide Chart Cache`. Source only, with no editor work.
