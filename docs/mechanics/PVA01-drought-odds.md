# PVA01 - Drought Odds (contest G202)

Code: `daedalus-core/src/main/java/com/daedalus/world/battlefield/DroughtOdds.java`
Tests: `DroughtOddsTest` (9 tests). Source only; no Unreal, no new assets.

## Story / Daedalus hook

The G194 flock grows on average, but the marsh has good and bad years. Before the keeper signs off a release, the
census board shows the odds that the flock crashes to 10 birds, the point where G142's Allee effect takes over.

- `DroughtOdds.fromCohorts(flock, sigma, start, threshold)` sets mu = ln lambda from G194 `CraneCohorts`.
- Default flock (lambda 1.029, sigma 0.15, 40 birds, threshold 10): 1.9 % risk within 50 years, 2.9 % ever.
- Drought flock (adult survival 0.8, lambda 0.961): 81.9 % within 50 years, certain in the end. Half of the
  flocks that crash do it within 28.8 years (`medianYears()`).
- Quest: Pip has to raise adult survival (the biggest G194 elasticity) until the 50-year risk shows green.

## Model

Each year multiplies the flock by a log-normal factor, so ln N is a random walk with drift mu and sd sigma.
With d = ln(start / threshold), the diffusion approximation (Dennis, Munholland and Scott 1991) gives:

```
G(T) = Phi((-d - mu T) / (sigma sqrt T)) + exp(-2 mu d / sigma^2) Phi((-d + mu T) / (sigma sqrt T))
ultimate = 1 if mu <= 0, else exp(-2 mu d / sigma^2)
```

Phi uses Abramowitz-Stegun 7.1.26 (error under 1.5e-7). Monte Carlo (`simulate`) runs `substeps` steps a year;
every normal draw is a splitmix hash of (seed, run, step), so a seed always replays the same odds.

| mu, sigma, start to threshold | G(50) | MC 40 steps/yr | MC 1 step/yr | ultimate |
|---|---|---|---|---|
| 0.03, 0.20, 40 to 10 | 0.087 | 0.081 | 0.076 | 0.125 |
| -0.02, 0.15, 30 to 10 | 0.632 | 0.617 | 0.583 | 1 |
| ln 1.029, 0.25, 40 to 10 | 0.199 | 0.192 | 0.166 | 0.281 |

Yearly censuses miss crashes that happen between counts, so the one-step-a-year Monte Carlo sits below G(T).

## Tests (DroughtOddsTest, 9)

1. Phi matches the normal tables to 2e-7.
2. Ultimate risk is 1 with mu <= 0 and exp(-2 mu d / sigma^2) otherwise.
3. G(T) never falls as T grows, and it reaches the ultimate risk. A driftless walk matches the reflection
   principle 2 Phi(-d / sigma sqrt T).
4. Monte Carlo (3000 runs, 40 steps a year) is within 0.035 of G(50) on three tunings. The yearly-step run never
   shows more risk.
5. Wilder years raise the risk even for a growing flock, and a bigger release lowers it.
6. `medianYears` puts G at half the ultimate risk; it is infinite when crashes are vanishingly rare.
7. Seeded Monte Carlo replays exactly; another seed differs.
8. The G194 drought flock has certain ultimate risk and is far worse than the default flock (more than 0.5
   higher over 50 years).
9. Bad tuning and inputs are rejected.

## Assets

None. Optional UI: a risk gauge on the G119 census board next to the G163 studbook.

## Native C++ core (G570)

`engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusMarshDroughtOddsCore.h` (namespace `daedalus::marsh`)
is a header-only C++17 port of this core: `Phi`, `DroughtOdds::Within`, `Ultimate`, `MedianYears` and the seeded
`SimulateHits`/`Simulate`, plus `DroughtSettings::Valid`. It uses the standard library only (no Unreal headers). The
Java class stays the rules authority. `MarshCoresParityTest` writes 48 golden vectors to
`engines/unreal/core-test/marsh_drought_odds_parity.txt` and `marsh_drought_odds_core_test.cpp` replays them:
closed-form values to 1e-9 relative, the median to 1e-7, and Monte Carlo hits to ±1. CI runs this in
`.github/workflows/marsh-cores.yml`. See [NATIVE-PORT-PATTERN.md](NATIVE-PORT-PATTERN.md) for how to port the next core.
