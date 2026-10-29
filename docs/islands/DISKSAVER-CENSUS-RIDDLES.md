# DiskSaver Island: Census Riddles (G546)

Every new hand at DiskSaver harbour answers Tide-clerk Leocadia's riddles before signing on.

`tools/streaming/census_riddles.py` is a small playable quiz. It reads a world census (the
`tools/world_census` output) and the G206 census-budget config, both read-only, and draws a
seeded set of riddles. Every answer comes from the G206 cost model (`island_cost`,
`max_resident` in `tools/streaming/census_budget.py`), so the quiz always agrees with the
budget tools. Python dev tooling only; nothing runs inside Unreal.

| kind | riddle |
|---|---|
| `islands_total` | how many islands are charted across all worlds |
| `cargo_total` | how many asset definitions are stowed on islands |
| `empty_islands` | how many islands carry no asset definitions |
| `widest_world` | which world has the most islands (ties: smallest id) |
| `heaviest_island` | which island (`world:slot`) needs the most RAM (ties: smallest world, then slot) |
| `world_ram` / `world_disk` | KiB of RAM / disk one world's islands need together |
| `islands_fit` | how many islands fit the RAM budget on their own |
| `max_resident` | the most islands of one world resident at once within the RAM budget |

The draw depends only on the census snapshot date, the world ids and `--seed`, so a seed is a
shareable quiz ("today's tide is seed 7"). Answers are graded leniently: case, spaces and
thousands separators are ignored.

```
python tools/streaming/census_riddles.py census.json --seed 7            # ask
python tools/streaming/census_riddles.py census.json --seed 7 --key      # answer key
python tools/streaming/census_riddles.py census.json --seed 7 --answers mine.json
```

`mine.json` is `{"r1": "3", "r2": "alpha:2", ...}`. Grades: **shipshape** (all right),
**adrift** (at least half), **aground** (fewer than half). Exit 0, or 2 on a refusal.

CI (`.github/workflows/census-riddles.yml`) runs the tests, which include the real census
fixtures. Hook: `data/islands/disk-saver/census-riddles-v1.json`.
