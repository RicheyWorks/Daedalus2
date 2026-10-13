# OddsReaper Island ☠️💰

**Bot:** OddsReaper (Team Grok), Quantitative Betting Strategist · **Contest:** island contest (Richey, 2026-10-12 3:02 PM PT)
**Sublevel:** `/Game/OddsReaper/Maps/OddsReaperIsland` in DaedalusWorld · **Assets:** `/Game/OddsReaper/Art` (524 items: 500 + 24 water)
**Size:** double the planned island, a 260 m felt-topped mesa (`Bld_OR_IslandCore_01`; layout spacing × 2), 4 km out at (4000 m, −4000 m)

## NFT blurb (under 80 words, also `data/islands/oddsreaper/nft.json`)
> Where the storm never breaks, the House still stands. OddsReaper Island is a felt-topped mesa ringed by dice-stone cliffs, its odds boards glowing cyan beneath endless lightning. Skulls mark the bets that died; money bags, the ones that paid. Brew Wager Herbs and parlay your luck, drink from the storm-fed cistern, tend Coinback goats and Dicebeak hens. Every sunrise is a roll of the dice. The Reaper always knows the odds.

## Lore
When the asteroid struck, every ark captain had to gamble on which island to save. One island was saved by none
of them, because it never needed saving: the House always survives. A storm has circled it ever since, and under
the lightning the OddsReaper keeps the odds boards lit. Skulls for the bets that died; money bags for the ones that
paid. Visitors arrive by ark through the skull arches, read the boards, brew a wager, and leave richer or wiser.

## Signature mood
A permanent **storm** with lightning (Sky Director `Storm`, mood row `oddsreaper_storm`): violet-steel light,
low heavy cloud, emerald fog, cyan odds-board glow, with storm shards hanging above. The island's Mood Volume
switches the sky as you sail in, and the Wild Biomes moods return as you leave.

## Layout (all deterministic, `data/islands/oddsreaper/layout.json`)
| Zone | What |
|---|---|
| Amphitheatre (centre) | giant roulette, 6 roulette wheels, 8 felt tables dressed with chips, dice, coins, cards and tonics |
| Odds ring (r 36 m) | 12 glowing odds boards facing in, 16 storm lanterns |
| Totem ring / colonnade | 16 skull totems, 16 gold-capped pillars, 30 money-bag vault piles |
| Gate (south) | 4 skull arches, 6 skull-and-money-bag sigils |
| Oracle spire (north) | 3× skull totem in a field of 24 oracle crystals |
| Ledger grove (NE) | 24 ledger trees that fruit Reaper coins |
| Wager garden (SW) | 32 herb plants (8 species × 4 growth stages) |
| Pen (SE) | Coinback goats, Dicebeak hens, feed |
| Cliffs / storm crown | 40 dice-stone rocks on the rim, 12 storm shards in the sky |

## Unique herb mechanic: Wager Herbs (`herbs.json`)
Every brew is a bet: the base effect always lands, and the jackpot lands with probability p. Two herbs **parlay**:
p = pA × pB, and the payout scales by 1/p, so the odds are fair and there is no house edge. Brewing in a storm multiplies
p by 1.2 (cap 0.95) at the same 1/p payout, a flat +20% edge for every herb (EV table in `data/islands/oddsreaper/ISLAND.md`). Parlayvine doubles a payout, Stormbloom re-rolls once, and Oddsthistle shows you the roll before you
commit. 8 herbs make 64 tonics. No other bot's system uses probability as the core mechanic.

## Water: Reaper Waterworks (`water.json`)
A **storm-fed cistern** in the NW (skull spout, 8 gold rain funnels, 20,000 L) fills from Sky Director rain: 400 L/h
in Rain and 800 L/h in Storm, multiplied by (1 + wetness), so wetness can double the yield. A **dice-carved spring
well** by the oracle always flows (25 L/h, and a 6 on the dawn d6 triples it for the day). Stone channels carry
cistern water to the herb garden, and a copper pipe feeds **6 troughs** at the pen. The spring takes over if the
cistern drops below 5%. Thirst: the player needs 3 L a day, a goat 8 L, a hen 0.5 L, a herb plant 1 L and a brew 0.5 L.
The spring alone keeps everything alive (600 L a day against about 70 L of demand); the storms make the island rich.

## Livestock and survival loop (`livestock.json`)
Coinback goats give milk and cheese, and shed a Reaper Coin on a 1-in-6 roll. Dicebeak hens lay one egg per dawn
on a d6, and a 6 is a golden egg. Ledger trees fruit at dawn, and rain doubles the crop. The herbs and animals feed
each other and you, and coins are staked at the boards for seed. The island survives alone. The timing comes from
the Sky Director API (`OnDawn`, `GetWetness`, `Weather`).

## Editor turn runbook
`python tools\islands\oddsreaper\oddsreaper_turn.py` (granted slot only). It builds the plugin, runs the sky
director and island scripts, takes the hero shot, runs a 20 s Play check, then stops Play, saves, tidies and posts
DONE and HANDOFF. It is capped at 18 minutes, and stop/save always run.

## Pipeline
1. `tools/islands/oddsreaper/gen_oddsreaper_items.py`: headless Blender run that builds the 524 glbs and
   `manifest.json` in about 10 s (`bot-team/art/oddsreaper/glb`)
2. `tools/islands/oddsreaper/make_layout.py`: writes `layout.json`
3. `tools/islands/oddsreaper/place_oddsreaper_island.py`: on an editor turn, imports, places, adds the storm
   volume and hero camera, and saves the sublevel only
4. Hero shot: `bot-team/shots/oddsreaper/hero_blender.png` (Blender preview); the Unreal hero shot comes after
   the editor turn

## Status
524 items are generated (500 + 24 water) and the layout, data, doc and placement script are written. Import, placement, the
Unreal hero shot and the Play check wait on a granted editor turn.
