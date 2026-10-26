# G106 The Rigged Coin (OddsReaper Island)

Owner: oddsreaper. Code: `daedalus-core/src/main/java/com/daedalus/world/odds/bayes/`.
Reuses `world.odds.OddsRng` and `Intervals`. Story tie-in to G77 (the rival bookmaker); no code dependency on it.

## Story

The rival bookmaker from the ark docks (G77) got behind the Keeper's bar one night and swapped one
of his three storm coins for a coin weighted with ark lead. The Keeper does not know which. Every
flip costs a herb, and the purse holds thirty. The Keeper's rule: flip until the ledger is sure, not
until you are.

| Story beat | Mechanic in code |
|---|---|
| A rigged coin lands heads 70% of the time | `RiggedCoinQuest.RIGGED_P` vs fair 0.5, rigged coin chosen by seed |
| The Keeper's ledger: who is the likeliest culprit? | `RiggedCoinQuest.posterior`: exact Bayes, proportional to (p1/p0)^heads x ((1-p1)/(1-p0))^tails |
| Stop flipping when the evidence is enough | `Sprt`: Wald's SPRT, thresholds ln((1-beta)/alpha) and ln(beta/(1-alpha)) |
| How often does that rule get fooled, and how many flips does it cost? | `SprtOdds.simulate`: seeded rigged-call rate (Wilson), undecided count, mean flips |
| Accuse a coin | `RiggedCoinQuest.accuse` |

## Quest q_rigged_coin

Three coins, one rigged (p = 0.7), 30 flips, SPRT alpha = beta = 5%.

1. FLIPPING: "N flips left. My money is on coin K at P%. Flip until the ledger is sure, not until you are."
2. CAUGHT: "That's the one. Weighted with ark lead. The rival owes me a coin and an apology."
3. WRONG_COIN: "Honest coin, that. It was coin K. Streaks lie; counts don't."
4. OUT_OF_HERBS: "Purse is empty. The rival keeps his secret today."

Following the posterior to 95% (or until the purse runs out) catches the rigged coin in about seven of ten seeded games (145 of 200 in the test seeds).
Herbs are in-game only; there is no real-money wagering.

## Editor / asset needs (later, not in this PR)

- Three storm-coin props on the bar; coin-flip animation and bark.
