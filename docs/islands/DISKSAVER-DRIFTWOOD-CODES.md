# DiskSaver Island: Driftwood Codes (contest G76, quest `q_driftwood_codes`)

## Story
Caches that ride out to the Reef (G67) must fit its slots. The Driftwood Carver packs each
cache into a bit stream by tying its chunk kinds into a raft. The quest is to tie the raft
so the packed cache fits the reef slot.

## Mechanics (code: `tools/streaming/driftwood_codes.py`)
- Each chunk kind starts as a bundle weighted by its frequency. Each turn the keeper ties
  two bundles into one (weight = sum) until a single raft remains.
- A kind's code length is its depth in the raft. Packed size = sum(freq x depth) bits.
  If that is <= `bit_budget`, the game is **won**; otherwise it is **failed: over_bit_budget**.
- `lightest_pair` is Huffman's rule and always reaches the optimum (`optimal_bits`, 259
  bits for the shipped data). `in_order_pair` is the trap: tying in carving order costs
  315 bits, over the 280 budget.
- `codes()` gives canonical prefix codes. They satisfy Kraft's equality and round-trip
  through `encode` and `decode`.
- Score on a win = 1000 at the optimum, falling toward the budget.

## Daedalus tie-in
- `freqs_from_tide_chart()` turns the G70 Tide Chart request stream (G39 islands) into
  kind frequencies, so island ids in the stream manifest get Huffman codes. The test shows
  this beats fixed 2-bit ids.
- Pure integer and deterministic (ties broken by bundle id). `receipt()` returns a
  G12-style activity receipt.

## Checks
`python -m unittest tools/streaming/driftwood_codes_test.py -v`; the CI job is
`Driftwood Codes`. Source only, with no editor work.
