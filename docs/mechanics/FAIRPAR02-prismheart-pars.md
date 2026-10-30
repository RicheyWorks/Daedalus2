# FAIRPAR02 - Prismheart Fair Par (G603-G606; Prismheart balance lane)

Code: `tools/minigames/fair_par.py` (authority; read-only on the games' rules)
C++: `engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusPrismFairParCore.h` (namespace `daedalus::prismpar`)
Tests: `tools/minigames/test_fair_par.py` (6 tests); `engines/unreal/core-test/prism_fair_par_core_test.cpp`
(195 checks). The C++ core plays the same bot through each game's own C++ core and must
rebuild `prism_fair_par_parity.txt` exactly.
Shardring is the exception: its core is Oracle-fed (no PRNG port), so its rows are Python-only and the C++ test
checks them for shape and tier order. CI: `engines.yml` (g++ ASan+UBSan, clang++) and `desktop-games.yml`
(`fair_par.py --check`). Source only; no editor, no new assets.

Marsh cabinets: see `FAIRPAR01-fair-par.md` (G600/G602). This is the first par table for the Prismheart games, as
PLAN.md asks: Glowmoss Delve, Spiritkite Weave and Glimmerloom Ledger, each on every difficulty.

## Rules

1. These cabinets already have a win target, so **BRONZE is any win**. A lost round scores 0 and earns no tier.
2. **SILVER and GOLD** are the scores reached by at least 40 % and 10 % of the bot's *winning* rounds, using the
   integer rank rule from FairPar.java.
3. **The casual bots** are careful but random:
   - Glowmoss: dig a random ledge that still leaves light to climb out; climb out once the target is met.
   - Spiritkite: fly random lanes that keep a way home; head home once the target is met; then land.
   - Glimmerloom: sell what the rumor does not favour; buy a random amount of the hue rumored to rise; rest.
   - G604-G606 cabinets (Lumenpath, Wardens' Accord, Facetlock, Prismvault, Shardfall, Prismcairn, Shadewatch,
     Shardring): a mixed bot. Each move, a coin flip either plays the game's own demo move (Shardring: greedy_move)
     or a random legal move (a random mirror cell; a random take or affordable summon; a random row or column slide;
     name a random remaining candidate; draw or bank on a coin; any legal take; flare any lane, kindle or nova; any
     empty facet).
4. Bot choices come from the stateless SplitMix64 hash shared with FairPar.java (bot seed 600), never from the
   game's own RNG. Each game uses seeds 0-399.
5. **Daedalus hook:** `prismpar::TierOf(row, won, score)` gives the result-screen tier. Satchel tiers, Almanac daily
   pars and trophies read the same table.

## Par table (400 seeds per row)

| Game | Difficulty | Bot wins | Silver | Gold | Hits B/S/G (per mille) | Bot win median | Demo wins | Demo median | Separated |
|---|---|---|---|---|---|---|---|---|---|
| glowmoss | easy | 50.5 % | 28 | 33 | 505 / 252 / 65 | 27 | 100.0 % | 38 | yes |
| glowmoss | normal | 13.7 % | 32 | 38 | 137 / 60 / 15 | 31 | 100.0 % | 42 | yes |
| glowmoss | hard | 4.5 % | 29 | 39 | 45 / 20 / 5 | 25 | 100.0 % | 41 | yes |
| spiritkite | easy | 58.7 % | 22 | 28 | 587 / 290 / 67 | 21 | 100.0 % | 23 | yes |
| spiritkite | normal | 18.7 % | 22 | 29 | 187 / 80 / 20 | 20 | 100.0 % | 24 | yes |
| spiritkite | hard | 2.0 % | 22 | 25 | 20 / 12 / 2 | 22 | 100.0 % | 24 | yes |
| glimmerloom | easy | 58.2 % | 167 | 205 | 582 / 242 / 62 | 159 | 81.7 % | 187 | yes |
| glimmerloom | normal | 30.2 % | 157 | 185 | 302 / 125 / 32 | 152 | 55.5 % | 142 | yes |
| glimmerloom | hard | 20.7 % | 120 | 135 | 207 / 87 / 22 | 117 | 31.0 % | 0 | yes |
| lumenpath | easy | 88.0 % | 190 | 230 | 880 / 435 / 145 | 180 | 100.0 % | 210 | yes |
| lumenpath | normal | 83.0 % | 160 | 190 | 830 / 350 / 122 | 150 | 100.0 % | 170 | yes |
| lumenpath | hard | 74.5 % | 140 | 180 | 745 / 302 / 75 | 130 | 100.0 % | 150 | yes |
| wardens_accord | easy | 100.0 % | 50 | 55 | 1000 / 457 / 192 | 45 | 100.0 % | 45 | yes |
| wardens_accord | normal | 83.5 % | 60 | 65 | 835 / 337 / 127 | 55 | 94.7 % | 55 | yes |
| wardens_accord | hard | 22.0 % | 60 | 65 | 220 / 120 / 47 | 60 | 44.0 % | 0 | yes |
| facetlock | easy | 51.5 % | 140 | 160 | 515 / 322 / 85 | 140 | 100.0 % | 140 | yes |
| facetlock | normal | 27.5 % | 140 | 170 | 275 / 145 / 32 | 140 | 100.0 % | 150 | yes |
| facetlock | hard | 11.5 % | 130 | 160 | 115 / 70 / 25 | 130 | 100.0 % | 130 | yes |
| prismvault | easy | 42.7 % | 150 | 250 | 427 / 427 / 75 | 150 | 100.0 % | 150 | no |
| prismvault | normal | 29.7 % | 150 | 250 | 297 / 150 / 45 | 150 | 100.0 % | 100 | yes |
| prismvault | hard | 23.5 % | 100 | 200 | 235 / 235 / 35 | 100 | 100.0 % | 100 | no |
| shardfall | easy | 32.7 % | 44 | 50 | 327 / 142 / 40 | 43 | 97.5 % | 43 | yes |
| shardfall | normal | 6.2 % | 43 | 48 | 62 / 32 / 7 | 43 | 59.0 % | 41 | yes |
| shardfall | hard | 6.0 % | 34 | 38 | 60 / 27 / 10 | 33 | 40.0 % | 0 | yes |
| prismcairn | easy | 54.5 % | 105 | 105 | 545 / 292 / 292 | 105 | 100.0 % | 105 | no |
| prismcairn | normal | 28.5 % | 105 | 105 | 285 / 117 / 117 | 100 | 100.0 % | 105 | no |
| prismcairn | hard | 0.0 % | 0 | 0 | 0 / 0 / 0 | 0 | 100.0 % | 105 | no |
| shadewatch | easy | 83.0 % | 115 | 125 | 830 / 372 / 125 | 110 | 96.2 % | 120 | yes |
| shadewatch | normal | 45.7 % | 129 | 144 | 457 / 237 / 80 | 129 | 79.2 % | 134 | yes |
| shadewatch | hard | 14.0 % | 148 | 163 | 140 / 75 / 25 | 148 | 49.5 % | 0 | yes |
| shardring | easy | 14.5 % | 289 | 330 | 145 / 60 / 15 | 285 | 68.7 % | 287 | yes |
| shardring | normal | 3.2 % | 242 | 264 | 32 / 15 / 5 | 233 | 34.7 % | 0 | yes |
| shardring | hard | 2.2 % | 188 | 215 | 22 / 10 / 2 | 183 | 20.2 % | 0 | yes |

## Balance findings

- Every G603/G604/G606 row is separated: a win, silver and gold need strictly better scores. Five G605 rows are not
  (below).
- **Hard is very hard for casual play.** Spiritkite hard: 2 % of casual rounds win (8 of 400), so its silver and gold
  rest on 8 rounds and are low-confidence. Glowmoss hard: 4.5 %. A careful player with the exact plan always wins
  (demo 100 %).
- **Glimmerloom's own demo loses often** (normal 55 %, hard 31 %, demo median 0 on hard). Rumors are only 70-75 %
  true, so a target of 110-135 is luck-heavy. Worth a look by the game's owner; these rules are read-only here.
- Gold sits above the demo median on Glimmerloom easy and normal (205 vs 187, 185 vs 142). A lucky casual trader
  beats the scripted demo, so gold is a real stretch goal.
- **Wardens' Accord easy is a give-away**: the casual bot wins 100 %, and silver and gold (50/55) sit only one
  spirit above the win line. Hard is the opposite: the demo itself wins 44 % (demo median 0).
- **Facetlock falls off steeply**: casual wins 51 % / 27.5 % / 11.5 % on easy / normal / hard. The demo always
  solves it, so pars are fair but hard is unforgiving to one wrong slide.
- **Lumenpath is gentle on every difficulty** (casual wins 74-88 %). Gold (230/190/180) needs a near-demo solve with
  moves to spare.
- **Prismvault scores in 50-point steps** (100 + 50 per spare weighing), so silver can equal the plain-win score
  (easy, hard). Pars are coarse; a finer score (for example a bonus for fewer shards on the scale) would separate
  them. A careful weigher always wins.
- **Shardfall normal and hard are brutal for casual play** (6 %), and even the demo's banking rule wins only 59 % /
  40 %. The target is luck-heavy; worth a look by the game's owner.
- **Prismcairn has a perfect-play wall**: the demo (exact Grundy play) wins 100 %, the casual bot wins 0 % on hard,
  and scores cap at 105 (50 per round + 5 per round left), so silver = gold. There is no room for a gold tier
  without a new score source (for example a bonus for fast rounds).
- **Shadewatch is the best-tuned cabinet**: casual play wins 83 % / 46 % / 14 %, the demo 96 % / 79 % / 50 %, and
  every row is separated. Hard is a real test even for the demo.
- **Shardring is the harshest**: casual play wins 14.5 % / 3 % / 2 %, and the greedy helper only 69 % / 35 % / 20 %.
  The normal and hard pars rest on 13 and 9 winning rounds, so they are low-confidence. The ring fills up too fast
  for casual play; worth a look by the game's owner.
