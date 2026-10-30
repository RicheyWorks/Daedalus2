# SPREAD01 - Crane Spread (contest G200)

Code: `daedalus-core/src/main/java/com/daedalus/world/battlefield/CraneSpread.java`
Tests: `CraneSpreadTest` (8 tests). Source only; no Unreal, no new assets.

## Story / Daedalus hook

Once the G194 flock is growing, cranes leave the release reedbed and fan out along the marsh. Pip watches the
front creep toward the far reedbed 40 km away. The quest asks: how many springs until cranes nest there?

- `CraneSpread.fromCohorts(flock, b, cell, K, years)` takes lambda straight from G194 `CraneCohorts`.
- `Report.yearReached(km)` answers the quest. The default G194 flock (lambda 1.029) gets there in year 195.
  The drought flock (lambda 0.961) never leaves the reedbed (-1).
- The front can never move faster than c*, so the board can show "at least N years" before the run finishes.

## Model

Each cell (0.25 km) grows by Beverton-Holt `G(n) = lambda n / (1 + (lambda - 1) n / K)`, then the birds disperse
with a Laplace kernel `exp(-|x|/b) / 2b` (discretised and cut at 30 b). The first 4 cells are the release reedbed
and stay full. Front = furthest cell at K/2 or more.

Without an Allee effect the spread is linearly determined. Its speed is

`c* = min over 0 < s < 1/b of ln(lambda M(s)) / s`,

where M is the moment generating function of the discretised kernel (golden-section search). The simulated front
approaches c* from below; the gap is the usual slow (log t) correction.

| Case | c* (km/yr) | simulated front speed (yrs 100-200) |
|---|---|---|
| lambda 1.5, b 1 km (DEFAULT) | 1.383 | 1.363 |
| same with demographic noise (5 seeds) | - | 1.209 |
| G194 flock, lambda 1.029, b 1 km | 0.340 | 0.288 (yrs 150-300) |
| lambda below 1 | 0 | front stays at the reedbed |

Noisy runs make each cell's count a Poisson draw (normal above mean 40) around the deterministic value. Every draw
is a splitmix hash of (seed, year, cell), so a seed always replays the same run.

## Tests (CraneSpreadTest, 8)

1. The kernel is normalised, and its MGF is close to the continuous Laplace `1/(1 - b^2 s^2)`.
2. c* is the minimum of the dispersion curve: 1.38303 for the default. Doubling b about doubles it, and a higher
   lambda makes it faster.
3. The front speed sits within 3 % of c* and never above it, on three tunings.
4. A flock with lambda below 1 has c* = 0, stays at the reedbed and never reaches 20 km.
5. The noisy front tracks the deterministic front within 15 %.
6. Seeded runs replay exactly; another seed differs.
7. The G194 flock reaches 40 km no sooner than 40/c* years; the drought flock never does.
8. Bad tuning and null inputs are rejected.

## Assets

None. Reuses Mob_Sky_Crane (G142) and the marsh kits. Optional UI: a front marker on the G119 census board.

## Native C++ core (G583)

`engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusMarshCraneSpreadCore.h` (namespace `daedalus::marsh`)
is a header-only C++17 port of this core. It covers the kernel and `Mgf`, `SpreadingSpeed` (c*), the deterministic and
seeded noisy `Run`, `SpreadReport::YearReached` and `SpreadSettings::Valid`. It uses the standard library only. The Java
class stays the rules authority. `MarshCoresParityTest.craneSpread` writes golden vectors (6 tunings × MGF/c*,
deterministic run and noisy run, sampled every 5 years over 40 years) to
`engines/unreal/core-test/marsh_crane_spread_parity.txt`. `marsh_crane_spread_core_test.cpp` replays them and runs in
`.github/workflows/marsh-cores.yml`. Pattern: [NATIVE-PORT-PATTERN.md](NATIVE-PORT-PATTERN.md).
