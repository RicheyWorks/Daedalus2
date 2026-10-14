# ADR-066: The Colony Ledger — the M.U.L.E. loop, advanced, in every realm

Status: proposed, 2026-10-14 (Richey 14:09–14:10: "mule was from the Commodore 64 ... we are trying to run a more
advanced version where we add more items to collect ... yes we are adding that to the realm")

## Why

The C64 game had the cleanest economy loop ever shipped: claim a plot, outfit a M.U.L.E. for one good, produce,
sell at an auction whose price moves with supply and demand, survive a random event, repeat for twelve rounds, and
the colony's total wealth is the score. Our islands already roll what they are made of (`island_chemistry.py`:
geology grade, ores, herbs, orchard, crops, livestock, power, four goods with surplus and need) and every realm has
its own chemistry table. What is missing is the loop that makes those items worth collecting — and the loop is also
what pulls new items into the story (MECHANICS-REGISTRY: story → item → mechanic → island → story).

## Decision

**One ledger per realm, one round per market day.** The ledger is pure, clock-free core (like `ArkFleet`,
ADR-020): every method takes the round number; the server drives it; tests drive it faster.

1. **Plots are deeds.** A land's production profile comes from its seed + realm (`island_chemistry.profile`).
   Adjacent owned plots of the same good get the M.U.L.E. adjacency bonus (+1 output per neighbour, max +3) — the
   reason to tug plots together with an ark (ADR-065) and to make Super Islands (Ultra's standard).
2. **Workers are outfitted, not bought generically.** A worker is a pack mule (REALM-CASTS creature) or a Codex
   PowerUnit, outfitted for one **good family**; outfitting consumes the parts the chemistry names (a rotor needs
   iron + copper, a battery needs crystal, a plough needs iron + plank). An un-outfitted worker produces nothing;
   an outfitted worker on the wrong terrain produces one.
3. **Goods are the realm's item catalog, not four slots.** The four families stay (FOOD, ENERGY, ORE, CRYSTAL) for
   pricing, but every item is its own line: wheat, carrots, apples, cherry pie, wool, eggs, milk, honey, coal,
   copper, iron, gold, starmetal, each herb, each brew, crystals, power-unit parts, salvage. New collectibles enter
   by adding a chemistry row (per realm) — the Labyrinth sells chalk, thread and torch oil; Gallery City sells
   pigments; Parcels sells mail contracts and hay; Bricks sells parts; Portal sells keys and eggs.
4. **Production per round** = base(output of the terrain for that family) × fertility/purity/grade from the
   chemistry × worker count × (1 + adjacency) − spoilage (FOOD only) − the energy tax: every worker needs 1 ENERGY
   per round or it halts (the M.U.L.E. rule), so a windmill or a water wheel or a crystal lamp is the first thing a
   plot needs. The realm's power source list decides what counts as energy there.
5. **Market day** is a double auction per item: sellers post asks, buyers post bids, the price walks toward the
   crossing (M.U.L.E.'s moving price lines). Islands with a NEED buy; the shop and the inn are standing buyers at a
   floor price so a lone player can always sell. Arks haul: a sale between two islands is an `ArkVoyage` with cargo
   (ADR-020 held item "cargo"), so distance and the harbour queue are part of the price.
6. **Events** are rolled from the chemistry at the end of each round (one per realm per round): meteor (starmetal
   crater appears → LEGENDARY), blight (an orchard species halves), pirates/raiders take ENERGY from the richest
   plot (Arc-Raiders salvage vibe: the stolen power unit reappears as salvage on a far island), wampus-style hunt
   (a creature from the realm cast hides on a random plot; first to reach it gets a bonus), festival (a holiday
   cluster theme doubles that item's demand: pumpkins in harvest, lights in christmas).
7. **Score** is colony wealth: goods at market value + plots + workers, shown per realm and per player; the realm's
   storyline advances on wealth milestones (the Heartstone quest chain, ADR-040), which is the self-reinforcing
   loop Richey described: richer colony → richer story → new items to collect → richer colony.

## Two more layers on the same ledger (Richey 14:11–14:12)

**Animal Crossing — the daily life of a plot.** Every island has a **day book**: on each in-game day the chemistry
and the ecology (`engines/unreal/pcg-ecology`: seral stage per tile, biodiversity index, season) decide what can be
*found* — fish in the lake and the sky river by season and hour, bugs by seral stage (meadow bees, scrub hens,
old-forest deer), fossils and starmetal shards in the keel, shells on the ocean basin, fruit that ripens on a
schedule and must be picked. Found things go to the **collection** (the island's museum/news board: first-of-kind
bonus, completion rewards) or to the shop at the day's price (the shop's buy price drifts daily; turnip-style
speculation on one item per realm per week). Villagers (REALM-CASTS cast) post daily requests on the news board
("bring me three Rillprism and a cherry pie") that pay in items the island cannot make — the cross-realm trade
pull. Decorating counts: placed props raise the island's charm score, which raises visitor traffic and prices.

**Arc Raiders — scavenging and defending.** Rich and legendary lands, meteor craters and the drifting **salvage
hulks** (broken power units, wrecked arks, abandoned workshops that the events drop onto far islands) are
**scavenge sites**: anyone can land, loot parts (gearbox, rotor, battery, starmetal, rare herbs) and must get them
home by ark — cargo in the air can be intercepted. Owners can **defend**: fences, lanterns and watchtowers raise
the time-to-loot, trained creatures (kennel tonics) patrol, traps consume crystals; defenders who catch a raider
take the raider's cargo. Scavenged goods enter the same auction, so raiding is the other way to fix a NEED. All of
it is per realm: the Labyrinth's raids are into the maze, Bricks' are into wreck fields, World Zero's are
sky-hulk boardings by airship.

**Fishing and sky-sea boats (Richey 14:17).** Every island fishes: the lake, the stream, the pier on the ocean
basin and the sky river itself are fishing spots, each with its own fish list from the chemistry (`water.fish`),
season and hour windows (day book). Rare catches go to the collection; the Fisher villager buys the rest. And the
water that floats in the sky is **navigable**: a *sky-sea boat* floats on sky rivers, lakes and ocean basins but
cannot fly — it must stay in the water, so the sky-river network (lake → sky river → lake → waterfall → basin) is a
travel graph of its own, separate from arks and airships. A boat can only reach islands its water connects to,
which is why water sockets matter in the Super Island standard, why a stream's outlet is a route and why towing
plots together can open a new sea lane. Boat hulls come from the chemistry too (plank + iron, sails from wool);
cargo on a boat is slower than an ark but cannot be intercepted from the air.

## Where it lives

- `tools/economy/colony_ledger.py` — the pure core (production, outfitting, auction walk, events, score) with
  `test_colony_ledger.py`; same shape as the other `*_rules.py` portables, ready to port to `daedalus-core` Java.
- Chemistry rows: `tools/blender/island_chemistry.py` `REALMS` + the Chemistry sheet; item catalog per realm is
  derived from them (`catalog(realm)`).
- Mechanics sheet rows WZ10 (power unit), WZ11 (colony ledger), WZ12 (market day + ark cargo), WZ13 (events),
  WZ14 (day book: finds, collection, villager requests, charm), WZ15 (scavenge sites, cargo interception, defence),
  WZ16 (fishing spots per island and fish by water type/season/hour), WZ17 (sky-sea boats on the sky-river network).

## Held

- Server endpoints and persistence (`/realm/{r}/ledger`, rounds in `*.daew`), the realm UI for market day, and the
  on-chain settlement of sales (ADR-028 wallets) — after the core proves the loop in tests.
- Worker art: outfitted-mule variants per family (Blender), PowerUnit wiring/snapping (Codex).
