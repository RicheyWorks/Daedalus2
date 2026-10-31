# SHOAL01 — Net Quota (contest G176)

*Code: `daedalus-core/src/main/java/com/daedalus/world/battlefield/ShoalHarvest.java` (tests: `ShoalHarvestTest`, 10).*

## Story

The silverfin came back to the Pythagoras banks once the Tidewife's shore kept its kelp (SHORE01). The harbour fleet wants a rule for the
next fifty years, and harbour master Odile Fenn has two on her desk. The skippers want a **fixed quota**: 150 tonnes a
year, every year, which the almanac says is the most the shoal can give. The old net-mender wants a **fixed share**: take
the same fraction of whatever is out there. On paper both land 150 tonnes. On the real sea, where some years are lean,
only one of them still has fish in year fifty.

## Quest `q_net_quota`: "The Most the Sea Can Give"

1. Pick a rule (`Rule.QUOTA` with tonnes, or `Rule.EFFORT` with a share) and a level.
2. Run fifty years from a half-full shoal (`run(rule, level)`).
   - **THRIVING**: the shoal never fell under 5% of capacity and ends at a quarter of it or more. The kelp banks stay
     WETLAND (`band()`).
   - **DEPLETED**: it never collapsed but ends low.
   - **COLLAPSED**: it fell under 5% of capacity at some point. The banks go BARE.

Results with the defaults (K 1000 t, r 0.6, growth noise ±50%) over 200 seeds:

| Rule | THRIVING | DEPLETED | COLLAPSED | Mean catch (t/yr) |
|---|---|---|---|---|
| quota 150 (MSY) | 53 | 9 | 138 | 101.4 |
| quota 135 | 183 | 0 | 17 | 130.0 |
| quota 120 | 200 | 0 | 0 | 120.0 |
| share 0.231 (MSY) | 200 | 0 | 0 | 148.3 |
| share 0.28 | 192 | 8 | 0 | 139.0 |
| share 0.45 | 0 | 0 | 200 | 33.1 |

With no noise both MSY rules land exactly 150 t a year and hold the shoal at 500 t. With noise, the MSY quota collapses
the shoal in most seeds and lands a third less over the run; the MSY share never collapses it and lands nearly the full
MSY. A fixed catch keeps taking the same tonnage from a shrinking shoal. A fixed share backs off by itself.

## Rules (seeded)

1. The shoal starts at K/2. Each year it grows `B + r·B·(1 − B/K)·ε`, with ε uniform in 1 ± 0.5 from the seed.
2. Then the fleet lands `min(q, B)` (QUOTA) or `e·B` (EFFORT).
3. MSY is `rK/4` = 150 t (`msy()`). Because the shoal grows before the fleet fishes, the MSY share is
   `(r/2)/(1 + r/2)` = 0.231 (`msyEffort()`).

Every roll is a splitmix hash of (seed, year). `Settings.DEFAULT = (1000, 0.6, 0.5, 50, 0.05)`.

## What the tests pin

- MSY is 150 t and the MSY share 0.3/1.3.
- With no noise, both MSY rules land exactly 150 t every year (the shoal grows to 650 t and is fished back to 500 t),
  with the share at exactly (r/2)/(1 + r/2).
- The noise model and seeds are locked: golden shoal values for seed 1, and exactly 138 MSY-quota collapses and 0
  MSY-share collapses over seeds 1 to 200.
- With noise, the MSY quota collapses at least 100 of 200 seeds, while the MSY share collapses none and thrives in all.
- The MSY share lands more than 30 t a year more than the MSY quota, and more than 140 t.
- A precautionary quota of 120 never collapses, a 0.45 share always does, and no fishing always thrives.
- Effort catches are always the share times the shoal, and quota catches are always min(quota, shoal).
- `band()` is WETLAND exactly when THRIVING. The same seed and rule replay the same season, and bad rules and settings
  are refused.

## Host seam

- `ShoalHarvest.shoal(Settings, seed)`, then `run(rule, level)` from Odile's rule ledger (a quota dial or a share dial).
- `Report.years()` drives a fifty-year scrub (shoal size, catch landed). `Report.outcome()` and `band()` drive her lines
  and the kelp banks.
- Ties: the kelp banks are SHORE01's (G108), the same fishers who take the Tidewife's bait work the deep lines here,
  and the WETLAND band is shared with SALMON01 and CRANE01. The share rule is the same "take a fraction, not a fixed amount"
  lesson as CENSUS01's lower-bound quota.
- Assets: `Mob_Silverfin_Shoal` (instanced fish school, scalar Density), `Prop_Harbour_Ledger` (quota/share dial
  board) and a `Prop_Fishing_Skiff`, with reuse of the SHORE01 kelp and harbour kit (see UNREAL-QUEUE / BLENDER-ASKS).
  board) and a `Prop_Fishing_Skiff`, with reuse of the SHORE01 kelp and harbour kit (see UNREAL-QUEUE / BLENDER-ASKS).

## Native C++ core (G612)

`engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusMarshShoalHarvestCore.h` (namespace
`daedalus::marsh`) is a header-only C++17 port of this core: `ShoalHarvest::Msy`, `MsyEffort` and the seeded `Run`
under QUOTA or EFFORT (shoal and catch per year, final shoal, total and mean catch, outcome, WETLAND/BARE band), plus
`ShoalHarvestSettings::Valid`. It uses the standard library only (no Unreal headers). The Java class stays the rules
authority. `MarshCoresParityTest.shoalHarvest` writes 32 golden vectors (8 tunings x {MSY quota, MSY effort, half
quota, take-all effort}) to `engines/unreal/core-test/marsh_shoal_harvest_parity.txt`, and
`marsh_shoal_harvest_core_test.cpp` replays them exactly: the core uses only + - * / and min/max in Java's order, so
every double (including a year-weighted checksum over all years) must match bit for bit. CI runs this in
`.github/workflows/marsh-cores.yml`. See [NATIVE-PORT-PATTERN.md](NATIVE-PORT-PATTERN.md). No Fair Par cabinet reads
this core, so the par guard is unchanged.
