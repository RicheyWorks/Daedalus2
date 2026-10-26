# ISLES01 — Island Biogeography (contest G119)

*Code: `daedalus-core/src/main/java/com/daedalus/world/battlefield/IslandBiogeography.java` (tests: `IslandBiogeographyTest`, 10).*

## Story

When the planet shattered, the fragments drifted out like an archipelago. The mainland shard still holds forty species of
birds, beetles, seeds and spores. The **Ark Refuge** is the biggest fragment, sixty-four hectares of good ground, but it
sits nine kilometres out. Almost nothing reaches it, and what does arrive can live there a long time. Census-keeper
Orrin Vale explains: "Big islands keep what they get. Near islands get a lot. Ours is big and far, so it starves."

## Quest `q_island_census`: "Forty Species, One Raft at a Time"

1. Vale gives you **three stepping-stone rafts** (`stones`). Each raft you put on the route to an island divides that
   island's effective distance by (1 + rafts).
2. Place them (`raft(i)`), then let 80 seasons pass (`run()`).
3. Vale counts the refuge over the last ten seasons (`Report.census`).
   - **THRIVING**: the census reaches 18 species. Vale opens the ark seed-vault to the refuge.
   - **FRAGILE**: the census reaches 75% of that.
   - **BARREN**: anything less.
4. Rafts spent on Cinder Key or Gull Stack help those islands but never the refuge.

Over 100 seeds with the defaults, the share of THRIVING runs is 0% with no rafts, 14% with one, 72% with two and 94% with
all three. Luck still matters, which is the lesson: equilibrium is an average, not a promise.

## Rules (deterministic from the seed and the rafts)

| Quantity | Rule |
|---|---|
| Arrival chance I | `colonize · exp(−d/reach)`, with d = distance / (1 + rafts) |
| Extinction chance E | `min(1, extinct / area^z)` |
| Each species, each year | if absent, arrives with chance I; if present, dies out with chance E |
| Equilibrium | `S* = pool · I / (I + E)` (`equilibrium(i)`) |

Every roll is a splitmix hash of (seed, year, island, species). Moving a raft never changes another island's dice.
`Settings.DEFAULT = (40, 80, 0.2, 3.0, 0.6, 0.5, 3, 3, 18)`.
The default sky archipelago `SKY` is Gull Stack (4 ha, 1 km), Fernholm (25, 3), Thimble (1, 6), Ark Refuge (64, 9) and
Cinder Key (9, 12).

## What the tests pin

- The THRIVING share rises with every raft on the refuge (at least 43 of 50 seeds with all three), and is zero with none.
- Rafts spent elsewhere leave the refuge BARREN.
- Larger islands and nearer islands have higher equilibria.
- Long-run richness settles on the closed-form S* (within 1.5 species).
- Rafts divide distance, and rafts on one island leave every other island's run unchanged.
- `band(i, pool)` shares map to Vegetation: under 15% is BARE, under 35% SCRUB, under 60% MEADOW, otherwise OAK.
- A tiny island with E = 1 keeps nothing past a year.
- The raft budget and invalid settings are refused.

## Host seam

- `IslandBiogeography.archipelago(Settings, SKY, seed)`, then `raft(i)` from the raft-placement UI, then `run()`.
- `Report.years()` drives a season scrub, `Report.band(i, pool)` paints each fragment's cover, and `Report.census` with
  the outcome drives Vale's census board.
- Ties: stocking the Ark Refuge feeds the arks chain. The rafts are the same stepping-stone idea as SALMON01's ladder
  and WEB01's mycorrhizal links. Refuge cover uses the battlefield `Vegetation` bands.
- Assets: `Prop_Sky_Raft` (stepping-stone raft), `Prop_Census_Board` (Vale's tally board with 40 pegs), and existing
  sky-island tiles (see UNREAL-QUEUE / BLENDER-ASKS).
- Staged by blender-team (NOT READY) in `bot-team\staging\g119-island-biogeography-20261019` (D2 9b435b44e, builder
  `tools/blender/contest/sky_g119.py`): `Prop_Sky_Raft` (seven lashed logs, 3 m, mast and kite; `SOCKET_Mooring` on the
  bow post at deck + 0.3 m, `SOCKET_Deck`), `Prop_Census_Board` (1.5 m; 40 peg holes in a 4 x 10 grid,
  `SOCKET_Peg_00`..`SOCKET_Peg_39` = the pool of 40; GoalRail mark after peg 18 = the THRIVING census, FragileNotch
  after peg 14 = 75% of it; `SOCKET_Text`) and `Prop_Census_Peg` (`SOCKET_Grip`; seats 3 cm into a hole along the
  socket axis). Bind: peg i is filled when i < round(`Report.census`). Islands themselves are not built yet.
