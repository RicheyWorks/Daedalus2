# FAIRPAR02 - Prismheart Fair Par (G603, Prismheart balance lane)

Code: `tools/minigames/fair_par.py` (authority; read-only on the games' rules)
C++: `engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusPrismFairParCore.h` (namespace `daedalus::prismpar`)
Tests: `tools/minigames/test_fair_par.py` (6 tests); `engines/unreal/core-test/prism_fair_par_core_test.cpp`
(60 checks). The C++ core plays the same bot through the C++ Glowmoss, Spiritkite and Glimmerloom cores and must
rebuild `prism_fair_par_parity.txt` exactly. CI: `engines.yml` (g++ ASan+UBSan, clang++) and `desktop-games.yml`
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

## Balance findings

- Every row is separated: a win, silver and gold need strictly better scores.
- **Hard is very hard for casual play.** Spiritkite hard: 2 % of casual rounds win (8 of 400), so its silver and gold
  rest on 8 rounds and are low-confidence. Glowmoss hard: 4.5 %. A careful player with the exact plan always wins
  (demo 100 %).
- **Glimmerloom's own demo loses often** (normal 55 %, hard 31 %, demo median 0 on hard). Rumors are only 70-75 %
  true, so a target of 110-135 is luck-heavy. Worth a look by the game's owner; these rules are read-only here.
- Gold sits above the demo median on Glimmerloom easy and normal (205 vs 187, 185 vs 142). A lucky casual trader
  beats the scripted demo, so gold is a real stretch goal.
