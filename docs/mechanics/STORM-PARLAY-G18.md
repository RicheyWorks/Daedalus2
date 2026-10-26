# Storm Parlay inn board (contest gap G18)

Owner: oddsreaper. Module: `daedalus-core/src/main/java/com/daedalus/world/odds/parlay/` (JDK-only, no editor).
Builds on G07 (`com.daedalus.world.fishing`, PR195) and the Combat Odds Engine (`com.daedalus.world.odds`).

## Story
OddsReaper Island sits on the storm line of the Shattered Planet. When a squall rolls over the sky river, the deep
fish rise (G07 `Conditions.STORM`: rare fish bite twice as often, but every bite is shorter). The inn's **Odds
Keeper** chalks up a board of Storm Parlays for the day: land these fish, one per cast, in this order. She prices every
ticket from the true odds, says her cut out loud (never more than 5%), and pays in **storm herbs**, the island's own
in-game currency. Her quest, **The Keeper's Ledger**, asks a newcomer to settle three tickets, win or lose; the reward
is the Storm Ledger key item. The lesson of the island: know the odds before you stake anything.

## Mechanics (each story beat is code)
| Beat | Code | Rule |
|---|---|---|
| The daily board | `ParlayBoard.daily(table, islandSeed, day, sky, skill, tickets, maxLegs)` | Seeded by (island seed, day) via `OddsRng`, so everyone reads the same chalk. 1-4 legs, priced from `FishingOdds.exact`; tickets under 1-in-10,000 are wiped and redrawn. |
| An honest cut | `ParlayTicket.houseEdge()` | Offer = (1 - edge) x fair, edge drawn per day in [0, 5%]; never above `HOUSE_EDGE`. |
| Staking herbs | `ParlayBook.stake` | 1-50 herbs per ticket, one stake per ticket, cannot stake what is not in the purse. |
| Settling | `ParlayBook.settle` / `settleCasts` | Legs must land in order on consecutive casts (`CastSession` CAUGHT). Pays exactly once; a second settle is refused. |
| The Keeper's Ledger | `ParlayBook.ledgerEarned`, `OddsKeeper.ledger` | Three settled tickets complete the quest. |
| Her lines | `OddsKeeper.pitch / settle / ledger` | Plain-text dialogue for any dialog system. |

In-game currency only. Nothing here touches real money, wallets or tokens.

## Later (editor / art)
Inn chalkboard actor and herb-token props: BOARD\UNREAL-QUEUE.md and a NEED to blender-team after this lands.
