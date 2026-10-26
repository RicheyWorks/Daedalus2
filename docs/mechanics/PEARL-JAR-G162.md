# G162 The Pearl Jar (Sky Islands arks / OddsReaper Island)

Owner: oddsreaper. Code: `daedalus-core/src/main/java/com/daedalus/world/odds/urn/`.
Reuses `world.odds.OddsRng` and `Intervals`. Self-contained.

## Story

On the ark's first night the Odds Keeper sets out a jar with one white pearl and one black. Each pearl
drawn goes back with a twin of its colour, so early luck snowballs. Before twenty draws you name which
third the jar's final white share will land in. Most pick the middle, expecting things to even out.
They don't: with one of each to start, every final count from 0 to 20 white is equally likely, so each
third is exactly 1 in 3. The jar remembers its first pearls.

| Story beat | Mechanic in code |
|---|---|
| Each pearl brings a twin | `PolyaUrn(white, black, add)`; `nextWhite(w, m)` = (white + add w)/(white + black + add m), Laplace's rule at 1, 1, 1 |
| How many white in n draws | `whiteCounts(n)`: exact distribution draw by draw = beta-binomial (tested against the Beta-function formula); uniform 1/(n+1) at 1, 1, 1 |
| Where the jar ends up | `shareBetween(n, lo, hi)`; `expectedShare` stays white/(white+black) (martingale) |
| The draws themselves | `PearlDraws`: seeded draws, `simulate` with Wilson interval |
| Name your third | `PearlJarQuest` (q_pearl_jar) |

## Quest q_pearl_jar

1. CHOOSING: "One white, one black, and each pearl brings a twin. After 20 draws: lowest third 33%, middle 33%, top 33%. Name your third."
2. RIGHT_BAND: "W white of 20. Third T, as you said."
3. WRONG_BAND: "W white of 20: third T, not your C. The jar remembers its first pearls."

No wagering.

## Editor / asset needs (later, not in this PR)

- Glass jar prop with pearls, draw animation, three-band share gauge.
