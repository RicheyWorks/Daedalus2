# G56 The Keeper's Ledger (OddsReaper Island)

Owner: oddsreaper. Code: `daedalus-core/src/main/java/com/daedalus/world/odds/ledger/`.
Reuses `world.odds.OddsRng` and `world.odds.Intervals` (Wilson). Read-only on G18 (parlay), G35 (Squall Cup)
and G47 (ark routes): any board that quotes a chance and posted decimal odds can feed the ledger.

## Story

On the arks, every ration was a wager: feed the pups now, or hold grain for a storm that might not
come. The ones who lived kept ledgers. The Odds Keeper of the inn (G18) still opens one for every
newcomer, in storm herbs, and teaches one rule from those days: stake what the odds justify, not
what hope asks.

| Story beat | Mechanic in code |
|---|---|
| The Keeper chalks a chance and a price; how much should you put down? | `KellyStake.fraction` / `edge`: Kelly fraction (b p - q) / b, zero with no edge |
| The Keeper always advises half of that, and never more than a quarter of the ledger | `KellyStake.advise`: floor(bankroll x min(cap, multiplier x Kelly)), min 1 herb when there is an edge |
| One ledger for every Keeper game | `HerbLedger.settle`: wins pay floor(stake x odds); tracks history, peak, max drawdown |
| "Show me what greed does": the Keeper's old ark ledgers | `RuinOdds.simulate`: seeded doubled / ruined / expired chances with Wilson intervals for any staking plan |
| Double your herbs without going broke; do it by the chalk and earn the Keeper's Mark | `KeepersLedgerQuest` |

## Quest q_keepers_ledger

Start 20 storm herbs, target 40, at most 12 wagers on any Keeper board.

1. OPEN: "N herbs on the ledger, M wagers left. Stake what the odds justify, not what hope asks."
2. DOUBLED: with every stake at or under the half-Kelly advice: "Doubled, and never once over my advice. Take the Keeper's Mark; the arks needed hands like yours." Otherwise: "Doubled. Lucky or good, the ledger cannot tell yet. Next time, stake by the chalk."
3. BROKE: "Ledger's empty. The arks rationed better than that. Come back when the glass falls."
4. OUT_OF_WAGERS: "Twelve wagers and N herbs. Steady keeps an ark afloat; it does not double it."

Herbs are in-game only; there is no real-money wagering.

## Determinism

`RuinOdds` trial `t` uses `OddsRng.forTrial(seed, t)` with one `chance(p)` draw per wager.
The quest itself takes settled results from the game boards, so it has no randomness of its own.

## Editor / asset needs (later, not in this PR)

- Ledger book prop on the inn counter; Keeper's Mark badge icon.
