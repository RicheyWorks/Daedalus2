# OddsReaper Island: Wager Herb balance (round-2 polish)

Round 1 gave a storm brew a flat +0.1 to jackpot odds p while the payout stayed at 1/p. That made the storm
edge wildly uneven: Longshot (p 0.1) jumped to 2.0x expected value, Luckroot to 1.2x, Hedgeleaf to 1.11x, so
the only right play was "Longshot in every storm". Stormbloom's free re-roll also paid 1.67x EV even in clear
weather, because its payout ignored the second roll.

The fix: a storm multiplies p by 1.2 (cap 0.95), and storm-cistern water multiplies it by a further 1.05.
The payout stays at 1/p_base, so every herb gets the same edge and the choice is about effects and variance,
not a broken number. Stormbloom pays 1/p_eff with p_eff = 1-(1-p)^2 = 0.551, so its re-roll is fair in clear
weather and earns the same storm edge as everything else. Parlayvine is a catalyst and stays at p 1.0.

| Herb | p clear | EV clear | p storm | EV storm | p storm + cistern | EV |
|---|---|---|---|---|---|---|
| Luckroot | 0.50 | 1.00 | 0.60 | 1.20 | 0.63 | 1.26 |
| Hedgeleaf | 0.90 | 1.00 | 0.95 (cap) | 1.06 | 0.95 (cap) | 1.06 |
| Bluffmoss | 0.40 | 1.00 | 0.48 | 1.20 | 0.504 | 1.26 |
| Longshot | 0.10 | 1.00 | 0.12 | 1.20 | 0.126 | 1.26 |
| Stormbloom (p_eff) | 0.551 | 1.00 | 0.636 | 1.15 | 0.659 | 1.20 |
| Vigweed | 0.75 | 1.00 | 0.90 | 1.20 | 0.945 | 1.26 |
| Oddsthistle | 0.25 | 1.00 | 0.30 | 1.20 | 0.315 | 1.26 |

Stormbloom's storm row applies the x1.2 to the single-roll p (0.33 to 0.396) before the re-roll. Hedgeleaf hits
the cap, which keeps the safe bet safe instead of free. Parlays multiply the boosted p values, so a storm parlay
of two herbs earns about 1.44x: the Reaper rewards the bold who brew in the lightning, but no single herb breaks
the table.