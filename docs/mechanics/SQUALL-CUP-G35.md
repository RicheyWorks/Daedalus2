# G35 The Squall Cup (OddsReaper Island)

Owner: oddsreaper. Code: `daedalus-core/src/main/java/com/daedalus/world/odds/tournament/`.
Reuses G07 fishing (`FishTable`, `AnglerSkill`, `Conditions`) and `world.odds.OddsRng`.

## Story

When the arks first anchored above OddsReaper Island, food was short and the storm lanes under the
fragment were the richest water. The survivors settled who fished them by contest, not by rank. The
Odds Keeper of the inn (G18) still runs that contest every time the storm glass (G22) falls: the
Squall Cup.

| Story beat | Mechanic in code |
|---|---|
| The player signs the Keeper's ledger; the oldest hands take the top seeds and the byes | `Bracket`: standard seeding, byes to top seeds for any field size |
| The Keeper chalks the title board before the first cast | `CupOdds.simulate`: seeded Monte Carlo title chance and fair odds per angler |
| Each round is fished in the squall, same casts for both anglers, catch sold at market price | `Heat`: per-cast fish draw from the G07 table, strike vs window, price total; sudden death, then seed |
| A longshot champion is paid more storm herbs | `SquallCupQuest.purse()`: 10 herbs x min(8, round(1 / pre-cup chance)) |
| The Keeper's lines follow the cup | `SquallCupQuest.keeperLine()` per stage |

## Quest q_squall_cup

1. ODDS_POSTED: "Chalk says N% you lift the Cup. The arks fished worse lanes than these."
2. CHAMPION: "Champion of the storm lanes. The survivors would have fed a whole ark on that catch." Pays the purse.
3. KNOCKED_OUT: "The squall took your line this time. Come back when the glass falls again."

The purse is in-game storm herbs only; there is no real-money wagering.

## Editor / asset needs (later, not in this PR)

Cup podium and a chalk bracket board at the inn; reuse the G18 chalkboard art if blender-team delivers it.
