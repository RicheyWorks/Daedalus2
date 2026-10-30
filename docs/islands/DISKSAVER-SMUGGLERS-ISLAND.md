# DiskSaver Island: Smuggler's Island (G553)

A yes/no deduction game: Exciseman Bartholomew hunts the one island hiding contraband.

`tools/streaming/smugglers_island.py` reads a world census (the `tools/world_census` output,
read-only). Every island is a suspect, and a seed hides the contraband on one of them. The
exciseman may only ask yes/no questions built from the census. Python dev tooling only; nothing
runs inside Unreal.

| question | asks |
|---|---|
| `world:W` | is it in world W? |
| `realm:R` | is its world in realm R? (`realm:none` for worlds with no realm) |
| `slot>=K` | is its island slot at least K? |
| `cargo>=K` | does it carry at least K asset definitions? |
| `empty` | does it carry none? |

A question that splits the suspects the same way as an earlier one is dropped, so every listed
question tells you something at the start. An exact memoised minimax search (checked against
plain recursion in the tests) gives the fewest questions that always find the island; that is
the par, and `--auto` plays it.

```
python tools/streaming/smugglers_island.py census.json --seed 7 --list
python tools/streaming/smugglers_island.py census.json --seed 7 --ask world:alpha,slot>=4 --accuse alpha:2
python tools/streaming/smugglers_island.py census.json --seed 7 --auto
```

| verdict | meaning |
|---|---|
| `sharp` | right island, in no more questions than par |
| `caught` | right island, but more questions than par |
| `escaped` | wrong island |

CI (`.github/workflows/smugglers-island.yml`) runs the tests, including the real census
fixtures, and plays one auto game. Hook: `data/islands/disk-saver/smugglers-island-v1.json`.
