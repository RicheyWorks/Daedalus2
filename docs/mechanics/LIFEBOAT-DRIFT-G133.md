# G133 The Lifeboat Drift (Sky Islands arks / OddsReaper Island)

Owner: oddsreaper. Code: `daedalus-core/src/main/java/com/daedalus/world/odds/walk/`.
Reuses `world.odds.OddsRng` and `Intervals`. Self-contained; does not touch the G56 bankroll.

## Story

An ark went down on the belt reef. Its lifeboat lies four cables off the reef and six from the
harbour lights. Each watch it drifts one cable; the wind pushes it shoreward 45% of the time and the
current drags it back the rest. Left alone, it makes the harbour 19% of the time. The crew has three
biscuit rations; rowing a watch eats one and lifts the shoreward chance to 65%. The Odds Keeper, by
lantern from the harbour wall, calls when to row: never in mid-channel, only when the reef is close
or the lights are within reach. With his calls the boat makes the harbour 28% of the time.

| Story beat | Mechanic in code |
|---|---|
| Drift between reef and lights | `DriftOdds`: gambler's ruin, P(harbour) = (1 - (q/p)^k) / (1 - (q/p)^N), k/N when fair; expected watches k/(q-p) - N/(q-p) P(harbour), k(N-k) when fair |
| Currents that change along the channel | `DriftOdds.harbourChancesAt` (exact step-ratio product), `expectedWatchesAt` (tridiagonal solve) |
| Three rations, row or rest | `LifeboatDrift`: exact best P(harbour) per (rations, cable) by value iteration per ration layer; `plan(r)` shows where to row ('R') |
| The voyages themselves | `LifeboatDrift.sail` / `simulate`: seeded voyages on the best plan, Wilson interval |
| Watch by watch with the Keeper | `LifeboatQuest` (q_lifeboat_drift) |

Numbers for the quest (N = 10, start 4, p = 0.45, tilt 0.20, 3 rations): drift only 19.13%, expected
20.9 watches; best plan 28.23% with plan `.RRR...RRR.` (row at cables 1-3 and 7-9 while rations last).
More rations help less and less: even 30 rations stay below steady rowing (91.8%) because they run out.

## Quest q_lifeboat_drift

1. ADRIFT: "6 cables to the lights, 4 off the reef, 3 rations. Drift alone and it's 19%; row when I call and it's 28%. Rest the oars." (or "Row now.")
2. HARBOUR: "Harbour lights after W watches, R rowed. Ashore."
3. REEF: "The reef took her after W watches, R rowed. Swim for it."

No wagering.

## Editor / asset needs (later, not in this PR)

- Lifeboat prop on a channel strip with reef and harbour-light ends, oar/rest prompt, ration counter, Keeper lantern line.
