# G125 The Torn Star Chart (Sky Islands arks / OddsReaper Island)

Owner: oddsreaper. Code: `daedalus-core/src/main/java/com/daedalus/world/odds/collect/`.
Reuses `world.odds.OddsRng` and `Intervals`. Self-contained.

## Story

The arks' star chart was torn into eight pieces in the belt storms and the pieces were packed at
random into the salvage crates, one piece a crate. The supply skiff hauls crates until it sails.
Alone, you would need 33 crates to be 90% sure of all eight. The Odds Keeper keeps a counter where
three spare pieces buy any piece you name, and with it 13 crates are enough.

| Story beat | Mechanic in code |
|---|---|
| One random piece per crate | `ChartFragments`: n x H(n) expected crates (21.74 for 8), expected missing n(1 - 1/n)^c |
| "33 crates alone" | `completeNoTrade`: inclusion-exclusion, smallest 90% haul = 33 |
| The Keeper's counter: three spares for any piece | `completeWithTradeIn`: exact finite-horizon walk over (distinct, duplicates); 13 crates = 90.03% |
| The crates themselves | `CrateHaul`: seeded hauls, `simulate` with Wilson interval |
| Haul, trade, chart | `ChartCollectorQuest` (q_star_chart) |

## Quest q_star_chart

1. PLANNING: "Eight pieces, one a crate. Alone you'd want 33 crates; bring me spares, three for any piece, and 13 gives 90%."
2. CHARTED: "C crates, P pieces found, T traded at my counter. Charted."
3. TORN: "C crates, P pieces and S spares. Still M short; the skiff has sailed."

No wagering.

## Editor / asset needs (later, not in this PR)

- Salvage crate props, the Keeper's trade counter, chart-fragment pickups and the assembled chart UI.
