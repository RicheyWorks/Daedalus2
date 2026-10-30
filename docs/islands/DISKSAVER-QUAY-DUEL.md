# DiskSaver Island: Quay Duel (G550)

Two captains settle a tide on the quay against Wharfinger Casimir.

`tools/streaming/quay_duel.py` reads a world census (the `tools/world_census` output,
read-only). Every island becomes a crate worth its RAM cost in the G206 model
(`census_budget.island_cost`), and a seed lines the crates up end to end. The captains take
turns hauling ONE crate from either end of the line (`L` or `R`) until the quay is empty; more
cargo wins. Casimir plays perfectly. Python dev tooling only; nothing runs inside Unreal.

How Casimir thinks: an exact interval DP gives, for every stretch of quay, the best margin the
captain to move can force (the tests check it against plain minimax). Each turn of the log shows
the best move and how many KiB of margin a weaker move gave away.

| field | meaning |
|---|---|
| `outcome` | `won`, `tied` or `lost` (your cargo vs Casimir's) |
| `perfect` | you never gave margin away |
| `best_margin_kib` | the margin perfect play would have secured for you |
| `opener_cannot_lose` | even number of crates: the opener can always take all odd-placed or all even-placed crates |

```
python tools/streaming/quay_duel.py census.json --seed 7 --moves L,R,R,L
python tools/streaming/quay_duel.py census.json --seed 7 --second --auto
```

You need one move per crate you take (half the quay, rounded up when you open). Exit 0, or 2
on a refusal (bad census, unknown move, too few or too many moves).

CI (`.github/workflows/quay-duel.yml`) runs the tests, including the real census fixtures, and
plays one auto duel. Hook: `data/islands/disk-saver/quay-duel-v1.json`.
