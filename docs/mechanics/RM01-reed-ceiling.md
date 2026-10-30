# RM01 - Reed Ceiling (contest G504)

Code: `daedalus-core/src/main/java/com/daedalus/world/battlefield/ReedCeiling.java`
Tests: `ReedCeilingTest` (9 tests, including brute-force RK4 checks). Source only; no Unreal, no new assets.

## Story / Daedalus hook

Marsh hawks follow the sky-cranes home. Pip's first idea is to plant more reed (the G183 meadows crew can extend
the reedbed) so the marsh holds more cranes. The quest shows why that backfires. Past a certain size the extra
reed feeds hawks, not cranes, and the marsh starts swinging between crane booms and near-wipeouts. This is the
paradox of enrichment.

- `ReedCeiling.fromCohorts(flock, settings)` sets the crane growth rate r = ln lambda from G194.
- `cycleHectares()` is the quest answer: the reedbed size where swings begin (64.3 ha by default).
- `hawkHectares()` is the smallest reedbed that can feed hawks at all (7.1 ha).
- The capacity K = hectares x cranes per hectare is also the K that G200 spread and G251 plans assume.

## Model (Rosenzweig-MacArthur)

```
dN/dt = r N (1 - N/K) - a N P / (1 + a h N)     cranes
dP/dt = e a N P / (1 + a h N) - m P             hawks (Holling II)
N* = m / (a (e - m h))     P* = (r/a)(1 - N*/K)(1 + a h N*)
hawks persist iff K > N*;  stable iff K < K_H = 2 N* + 1/(a h)  (Hopf)
trace J* = r N* a h (K - 1/(a h) - 2 N*) / (K (1 + a h N*)),  det J* > 0
```

Default: r 0.4, 2 cranes/ha, a 0.02, h 0.5, e 0.6, m 0.15. N* = 14.29, K_H = 128.6.

| Reedbed | K | Regime | Cranes, long run (RK4) | Hawks P* |
|---|---|---|---|---|
| 40 ha (default) | 80 | stable | 14.29 (= N*) | 18.8 |
| 80 ha | 160 | cycles | 0.57 to 69.4 | 20.8 |
| 150 ha | 300 | cycles | 0.00001 to 246.7 | 21.8 |

The crane equilibrium never moves with the reedbed; only the hawks and the swing grow.

This differs from G58 Trophic Cascade (wolves and elk, landscape of fear, willow recovery). G58 does not have the
carrying-capacity-driven Hopf threshold.

## Tests (ReedCeilingTest, 9)

1. (N*, P*) is a rest point (rates below 1e-9), and the closed forms for N* and K_H hold.
2. A bigger reedbed leaves N* fixed and raises P*.
3. A finite-difference Jacobian matches the analytic trace (1e-6) on 5 reedbeds, with a positive determinant.
4. Brute force: RK4 over 3000 years on a K grid from 5 to 300 (more than 25 points, skipping 12 % around each
   threshold) gives the analytic regime every time (no hawks, stable at N*, or cycles).
5. The cycle amplitude grows with the reedbed, and deep cycles push cranes below half of N*.
6. The quest thresholds sit in hectares: 1 ha either side of `cycleHectares()` flips stable to cycles.
7. The G194 hook: r = ln lambda; growth does not move N* or K_H; a declining flock is rejected.
8. Seeded noisy runs (yearly log-normal shocks on cranes) replay exactly; another seed differs.
9. Bad tuning and runs are rejected.

## Assets

None needed. Reuses Mob_Sky_Crane and the marsh kits. A marsh hawk mob would be a later, optional Blender ask.

## Native C++ core (G591)

`engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusMarshReedCeilingCore.h` (namespace `daedalus::marsh`)
is a header-only C++17 port of this core. It covers N*, P*, the Hopf capacity, cycle and hawk hectares, the regime,
`Rate`, `Trace`, the RK4 `Integrate`, the seeded `Noisy` seasons, `FromCohorts` (on the G585
`DaedalusMarshCraneCohortsCore.h`) and `ReedSettings::Valid`. It uses the standard library only. The Java class stays
the rules authority. `MarshCoresParityTest.reedCeiling` writes golden vectors for 7 marshes (stable,
cycling and no-hawks regimes; the no-hawks case was added with G593) to `engines/unreal/core-test/marsh_reed_ceiling_parity.txt`. `marsh_reed_ceiling_core_test.cpp`
replays them in `.github/workflows/marsh-cores.yml`. Pattern: [NATIVE-PORT-PATTERN.md](NATIVE-PORT-PATTERN.md).
