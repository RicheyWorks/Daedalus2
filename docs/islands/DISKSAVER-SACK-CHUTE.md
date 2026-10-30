# DiskSaver Island: Sack Chute (G559)

A solitaire sowing game (mancala-style). Hold Master Peregrine sows census sacks down a looping
chute into the hold.

`tools/streaming/sack_chute.py` reads a world census (the `tools/world_census` output,
read-only). Every island is a bin on the chute (up to six), and spare bins pad it to at least
four. A seed fills each bin with one to three sacks, twelve at most in all. The chute runs
bin 1 to bin N, then the hold, then back to bin 1. Python dev tooling only; nothing runs inside
Unreal.

A move tips one bin. Its sacks are sown one at a time into the bins after it. One drops into the
hold each time the sowing passes the hatch, and the rest carry on round the loop. Every move
either banks a sack or pushes sacks towards the hold, so a game always ends.

Par is the fewest moves to empty every bin, found by an exact breadth-first search and checked
in the tests against an independent memoised recursion. `greedy_moves` shows the trap: always
tipping the bin nearest the hold.

```
python tools/streaming/sack_chute.py census.json --seed 7                # the chute and par
python tools/streaming/sack_chute.py census.json --seed 7 --moves 4,3,4
python tools/streaming/sack_chute.py census.json --seed 7 --auto
```

| verdict | meaning |
|---|---|
| `stowed` | every sack in the hold in par moves |
| `slow` | every sack in the hold in more moves than par |
| `loose` | sacks still in the bins |

Exit 2 refuses a bin number off the chute, an empty bin, moves after the chute is clear, or a
census with no islands or more than six. CI (`.github/workflows/sack-chute.yml`) runs the tests,
including the real census fixtures, and plays the seed-7 chute. Hook: `data/islands/disk-saver/sack-chute-v1.json`.
