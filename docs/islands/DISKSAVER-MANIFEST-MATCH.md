# DiskSaver Island: Manifest Match (G556)

A memory (Concentration) game. Wharf Clerk Godfrey's paperwork blew across the quay.

`tools/streaming/manifest_match.py` reads a world census (the `tools/world_census` output,
read-only). Every island has two cards: `ISLAND world:slot` and `MANIFEST world:slot <KiB>`
(its RAM cost in the G206 model, `census_budget.island_cost`). A seed picks up to 12 islands
and deals the cards face down in a row. Python dev tooling only; nothing runs inside Unreal.

Each turn flips two face-down cards by 1-based position (`3-7`). An island card and its own
manifest stay face up; anything else turns back over. The game is deterministic, so you play by
replaying: pass all your turns so far, read the faces revealed in the log, then add the next.

Par is the number of turns a player with perfect memory needs on this exact layout (tested
against an independent simulation). It is at least the number of pairs and at most twice that
minus one.

```
python tools/streaming/manifest_match.py census.json --seed 7                     # the table
python tools/streaming/manifest_match.py census.json --seed 7 --turns 1-2
python tools/streaming/manifest_match.py census.json --seed 7 --turns 1-2,3-1
python tools/streaming/manifest_match.py census.json --seed 7 --auto
```

| verdict | meaning |
|---|---|
| `sharp` | all pairs matched in par turns or fewer |
| `matched` | all pairs matched, in more turns than par |
| `unfinished` | some pairs are still face down |

Exit 2 refuses a position off the table, a card already matched, the same card twice, or turns
after the game ended. CI (`.github/workflows/manifest-match.yml`) runs the tests, including the
real census fixtures, and plays the seed-7 table. Hook: `data/islands/disk-saver/manifest-match-v1.json`.
