# DiskSaver Island: Defrag Tide (contest G63, quest `q_defrag_tide`)

## Story
After the vault was kept (G59), the islands still stream in with a stutter. Below the
Byte Spring (G39), the cache shelf is a strip of tide-worn blocks, and every island cache
lies scattered across it. Tidewright Seek asks the player to pack the caches into clean
runs before the season's tides crumble the shelf.

## Mechanics (code: `tools/streaming/defrag_tide.py`)
- The disk has `blocks` slots. Each cache is a list of blocks, and a seeded Fisher-Yates
  shuffle scatters them at the start.
- `runs(cache)` counts the contiguous runs, and each break is one seek. The score to beat
  is **weighted seeks** = sum of priority x (runs - 1).
- Each tide:
  1. The player makes up to `moves_per_tide` moves. Each move puts one block into a free slot.
  2. If weighted seeks <= `seek_target`, the game is **won**.
  3. The tide erodes one seeded free slot into a **bad block**, which can never be used again.
  4. After `tides` tides, the game is **failed: tides_out**.
- Erosion only eats free space, so waiting makes every later pack harder.
- The reference keeper (`keeper_policy`) packs the largest cache first into the cheapest
  window. It evicts blocks of still-fragmented caches, never touches packed caches, and
  finishes a window over several tides when needed.
- Score on a win = tides left, in permille.

## Daedalus tie-in
- The caches are the G39 Byte Spring islands. `files_from_byte_spring(spring, block_kib)`
  builds each cache as ceil(cost_kib / block_kib) blocks with priority + 1, and the
  shipped `defrag-tide-v1.json` equals that (block_kib 20).
- KiB is the DSB 1 streaming cost unit (ADR-063). Seeks are the stream-in stutter.
- It uses the same 32-bit LCG as G39 and G59, and `receipt()` returns a G12-style
  activity receipt.

## Checks
`python -m unittest tools/streaming/defrag_tide_test.py -v` covers validation, the scatter,
runs and seeks, move errors, erosion, idle failing on seeds 1-20, the keeper winning on
seeds 1-40, determinism, the LCG golden, the receipt, the G39 tie-in and the CLI. The CI
job is `Defrag Tide`. Source only, with no editor work.
