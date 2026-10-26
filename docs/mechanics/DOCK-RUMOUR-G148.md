# G148 Word on the Docks (Sky Islands arks / OddsReaper Island)

Owner: oddsreaper. Code: `daedalus-core/src/main/java/com/daedalus/world/odds/branch/`.
Reuses `world.odds.OddsRng` and `Intervals`. Self-contained.

## Story

The storm-ark sails at the turn of the tide and every dock has to hear of it first. The Odds Keeper
cannot shout across the islands, so word goes mouth to mouth: each sailor tells three mates, and each
mate believes it and passes it on 40% of the time (1.2 new tellers a teller). Even so, word started
by one sailor dies out for good 56% of the time, and is still going after eight tellings only 49% of
the time. Buy grog for four first tellers and it reaches the tide (8 tellings) 93% of the time; it lives forever 90.4% of the time.

| Story beat | Mechanic in code |
|---|---|
| Mouth to mouth | `BranchingOdds` (Galton-Watson): offspring law, mean m, generating function f |
| "Dies out for good" | `extinction`: smallest root of f(s) = s (1 when m <= 1); `expectedTotal` 1/(1-m) when subcritical |
| "Still going by the tide" | `extinctBy(g)` = f applied g times to 0, `aliveAt(g, seeds)` = 1 - f^g(0)^seeds |
| Grog for first tellers | `survival(seeds)` = 1 - q^seeds, `seedsFor(confidence)` |
| The tellings themselves | `RumourSpread`: seeded generations, `simulate` with Wilson interval |
| Buy the grog, wait for the tide | `DockRumourQuest` (q_dock_rumour) |

Numbers (3 mates, belief 0.4, so f(s) = (0.6 + 0.4 s)^3): extinction q = 0.5572. The quest's "by the tide" is a finite horizon of g = 8 tellings: P(alive at 8) = 1 - f^8(0)^s, 48.9% from 1 teller, 86.7% from 3, 93.2% from 4. Living forever is lower: 1 - q^s = 44.3% (1), 82.7% (3), 90.4% (4), 94.6% (5). The Keeper's 4 is the fewest for 90% both ways. Tests pin all of these, check f(q) = q to 1e-9, that f^g(0) climbs to q, and that seeded tellings land within a Wilson interval of both the 8-telling and the long-run figures.

## Quest q_dock_rumour

1. PLANNING: "One teller and the word lives to the tide 49% of the time. Buy grog for 4 and it's 93%."
2. SPREAD: "S first tellers, T sailors telling it at the tide. Every dock knows."
3. FIZZLED: "S first tellers and the word died out by telling G."

No wagering.

## Editor / asset needs (later, not in this PR)

- Dockside crowd with a "has heard" marker, grog purchase prompt, tide timer.
