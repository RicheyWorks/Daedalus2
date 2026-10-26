# DiskSaver Island: Coral Wear (contest G78, quest `q_coral_wear`)

## Story
The Reef's newest shelf is living coral, which works like flash cells. Every save written
into a cell wears it, and a cell that wears through goes white and never takes another
save. Hot island saves move every tide, while the old archives (kept by the G59 Save Vault)
sit still on fresh coral. Coralkeeper Wren asks the player to spread the wear so the shelf
lives through the season.

## Mechanics (code: `tools/streaming/coral_wear.py`)
- `cells` cells, each with a seeded endurance in [`endurance_min`, `endurance_max`]. Each
  island save lives in one cell.
- Each tick a seeded island (weighted) rewrites its save. The keeper picks a free living
  cell, the save moves there (+1 wear), and the old cell is freed. A cell retires when its
  wear reaches its endurance. It keeps the save it holds but never takes another one.
- Once per tick the keeper may **relocate** one save to another free cell (+1 wear on the
  target). This is static wear leveling: an archive moves onto worn coral so its fresh cell
  can serve the hot saves.
- If a write finds no free living cell, the game is **failed: no_living_cell**. Surviving
  `season_ticks` is a **win**.
- The policy ladder on seeds 1-40 with the shipped data:
  - `leveling_policy` (dynamic + static) wins 40
  - `least_worn_policy` (dynamic only) wins 33
  - `first_free_policy` (the trap) wins 7

## Daedalus tie-in
- `islands_from_tide_chart(tide)`: the hot saves are the G70 Tide Chart islands (G39
  islands) with weight x 10, plus three cold G59 archives. The shipped data equals that.
- It uses the same LCG as the rest of the DiskSaver lane, and `receipt()` returns a
  G12-style activity receipt.

## Checks
`python -m unittest tools/streaming/coral_wear_test.py -v`; the CI job is `Coral Wear`.
Source only, with no editor work.
