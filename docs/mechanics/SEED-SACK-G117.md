# G117 The Last Seed Sack (Sky Islands arks / OddsReaper Island)

Owner: oddsreaper. Code: `daedalus-core/src/main/java/com/daedalus/world/odds/draw/`.
Reuses `world.odds.OddsRng` and `Intervals`. Self-contained. Not G43 (seed viability over the voyage): this is the
planting decision at landfall.

## Story

The arks' last sack of storm-herb seed came ashore with sixty seeds, and the old ledgers say only
eighteen will sprout. The herb terrace needs four plants this season to start the island's trade,
and every seed put in the ground is one fewer for next year. The Odds Keeper counts it out.

| Story beat | Mechanic in code |
|---|---|
| Sixty seeds, eighteen good, drawn blind | `Hypergeometric(60, 18)`: exact pmf in log space, `atLeast`, `mean` |
| Plant the fewest that still make the terrace likely | `smallestDraw(4, 0.90)` = 19 (91.1%; 18 seeds gives 88.0%) |
| The sack itself | `SeedSack.draw`: seeded partial Fisher-Yates without replacement |
| Chalk checked against the sack | `SeedSack.simulate`: seeded estimate with Wilson interval |
| Thrifty, spendthrift or gambler | `SeedSackQuest` (q_seed_sack) |

## Quest q_seed_sack

1. PLANNING: "Sixty seeds, eighteen good. Plant 19 and it's 91% the terrace greens. Every extra is next year's."
2. TERRACE_GREEN: exactly 19: "S sprouts from 19 seeds, and the sack still holds next year." More: "...Green, but you spent next year's seed." Fewer: "...Green, but you rolled the dice to get there."
3. TERRACE_THIN: "Only S sprouts. The terrace needs 4; the sack decides the rest."

No wagering here.

## Editor / asset needs (later, not in this PR)

- Seed sack prop and terrace planting beds; sprout VFX.
