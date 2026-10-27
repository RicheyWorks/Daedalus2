# CRANE01 — Sky-Crane Return (contest G142)

*Code: `daedalus-core/src/main/java/com/daedalus/world/battlefield/AlleeRelease.java` (tests: `AlleeReleaseTest`, 11).*

## Story

The sky-cranes left the Pythagoras marsh when the planet shattered. The ark aviary has bred **40 of them** since then,
and keeper Ilsa Marr has to decide how to let them go. The fishers want a few birds at a time ("so we can watch them
settle"). Ilsa knows something the fishers don't: a crane alone on a big marsh does not find a mate. Below a certain
flock size, every year loses more birds than it gains. This is the **Allee effect**.

## Quest `q_sky_crane_return`: "Not One at a Time"

1. Schedule releases from the aviary (`release(year, birds)`, total 40).
2. Run 40 years on the marsh (`run()`).
3. **ESTABLISHED**: the flock is 50 or more. The marsh stays WETLAND and the cranes dance at the solstice.
   **LINGERING**: a few birds are left. **EXTINCT**: none are.

Results with the defaults over 100 seeds:

| Schedule | ESTABLISHED | LINGERING | EXTINCT |
|---|---|---|---|
| all 40 in year 0 | 90 | 4 | 6 |
| 20 + 20 | 88 | 4 | 8 |
| 4 a year for 10 years | 62 | 15 | 23 |
| 2 a year for 20 years | 27 | 20 | 53 |

## Rules (per year, seeded)

1. The year's releases join the flock.
2. Each adult survives with chance 0.75.
3. The survivors form ⌊N/2⌋ possible pairs. Each nests with chance `N/(N+30)`: the mate-finding Allee effect.
4. Each nest has two eggs. Each fledges with chance `1.0 · max(0, 1 − N/150)`.

`growth(n)` is the expected flock next year over this year: 0.89 at 10 birds, 0.98 at 20, 1.00 at 25 (`threshold()`
= 25), 1.06 at 60, and back under 1 at about 100 as the marsh fills. Every roll is a splitmix hash of (seed, year, bird,
salt). `Settings.DEFAULT = (40, 40, 0.75, 30, 1.0, 150, 50)`.

## What the tests pin

- One release at half the threshold (12 birds) dies out in at least 95 of 100 seeds; one release of all 40 (above it) dies out in at most 15 (measured: 99 vs 6).
- A single release establishes in at least 85 of 100 seeds.
- Twenty trickles establish in at most 35 and die out in at least 40.
- The odds never improve as batches get thinner (1 → 2 → 10 → 20).
- Growth is below 1 under the threshold, at least 1 at it, and below 1 at capacity. With no mate-finding cost
  (`mateHalf` = 0) there is no threshold.
- Fledglings never exceed two per nest, and nests never exceed half the flock.
- An empty aviary goes extinct and the marsh scrubs over (`band()`).
- The same schedule gives the same season, and the aviary budget and invalid settings are refused.

## Host seam

- `AlleeRelease.marsh(Settings, seed)`, then `release(year, birds)` from Ilsa's release-schedule UI, then `run()`.
- `Report.years()` drives the flock counter, nests and chicks. `Report.band()` keeps the crane grounds WETLAND or lets
  them scrub over.
- Ties: the cranes come from the arks chain's aviary. The marsh is the same WETLAND band as SHORE01's kelp and the
  salmon ponds. G119 (Island Biogeography) teaches arrival and extinction across islands, and this gap is its
  single-island close-up.
- Assets: `Mob_Sky_Crane` (Idle/Walk/Fly/Dance), `Prop_Release_Crate` (aviary crate with a door), and reuse of the
  marsh/wetland kit (see UNREAL-QUEUE / BLENDER-ASKS).
- Staged by blender-team (NOT READY) in `bot-team\staging\g142-sky-crane-return-20261019` (D2 714b05bf3, builders
  `tools/blender/contest/crane_g142.py`, `sky_g142.py`, `tools/blender/creatures/bird_rig.py`): `Mob_Sky_Crane` (1.18 m,
  384 tris; clips Idle, Walk, Fly and Dance, the courtship hop for an ESTABLISHED flock; `SOCKET_LegBand` on bone
  `Leg_L`, shipped in `Mob_Sky_Crane.sockets.json` because UE does not import glTF skeleton sockets). Release crate:
  `Prop_Release_Crate_Closed` / `_Open`, or the frame `Prop_Release_Crate` plus the mover `Prop_Release_Crate_Door`
  attached at `SOCKET_Door` (hinge UE (-37, 50, 0) cm, open yaw 110 from the sockets.json `hinges`). Spawn each
  released bird at `SOCKET_Crane` (inside, facing out) and walk it to `SOCKET_Release` (0.8 m in front of the door);
  `SOCKET_Carry_L/R` are for the keepers. One crate opening per `release(year, birds)` batch.
