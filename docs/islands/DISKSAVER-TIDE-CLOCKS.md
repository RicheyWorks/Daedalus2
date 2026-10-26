# Tide Clocks (contest G166, DiskSaver Island)

Quest `q_tide_clocks`, NPC **Clockwright Odile**. Code: `tools/streaming/tide_clocks.py`,
tests `tools/streaming/tide_clocks_test.py`, data `data/islands/disk-saver/tide-clocks-v1.json`,
CI job `Tide Clocks`.

## Rules
- Islands and save keys come from G86 Compaction Shoals (`compaction-shoals-v1.json`, read-only; a test checks the
  bytes are unchanged): the first 5 islands, 8 saves.
- 600 seeded steps. Each step either one island edits one save (45%) or the ferry carries one island's saves to
  another and they merge. Every island's wall clock has a seeded skew of up to 6 ticks. Then a final all-to-all sync.
- Clocks: `wall` (last-writer-wins by skewed wall time), `lamport` (last-writer-wins by Lamport time), `vector`
  (keep every version no other version dominates; concurrent siblings go to the Merge Keeper, and the next local edit
  supersedes them all).
- An edit is **lost** if a merge drops it in favour of a version that never saw it. Win: zero lost edits.

## Shipped outcome (seed 166)
| clock | edits | lost | conflicts detected / oracle | result |
|---|---|---|---|---|
| wall | 270 | 117 | 0 / 142 | fail |
| lamport | 270 | 118 | 0 / 143 | fail |
| vector | 270 | 0 | 169 / 169 | win |

## Science (pinned in tests, seeds 166, 1, 2, 3, 4)
- `vc_lt(a, b)` holds exactly when `a` happened before `b`, checked against a brute-force causal-history oracle on
  every pair of versions.
- Lamport clocks are consistent with causality (`a -> b` implies `L(a) < L(b)`) but not complete: there are
  concurrent pairs with `L(a) < L(b)`, which is why Lamport last-writer-wins still drops rival edits silently.
- The conflicts the vector clock detects at merges equal the oracle's concurrent pairs among the causally maximal
  versions meeting there, and no edit is lost.
- With skew, the wall clock can stamp a causally later edit earlier than the edit it replaced (causal inversion);
  with zero skew it never does.
