# LESLIE01 - Crane Cohorts (contest G194)

Code: `daedalus-core/src/main/java/com/daedalus/world/battlefield/CraneCohorts.java`
Tests: `CraneCohortsTest` (9 tests). Source only; no Unreal, no assets required.

## Story / Daedalus hook

After the sky-cranes are back on the marsh (G142 Sky-Crane Return) and the studbook keeps their genes in check
(G163), the keeper has to plan the flock's future: which birds die young, which breed, and which cohort to send
out next spring. Pip reads the Leslie matrix off the census board and learns that a flock is not just a head
count. Six chicks are worth only about two adults, so a release of chicks is far likelier to vanish.

- `bestRelease()` names the cohort worth most per bird (adults with the default rates).
- `adultEquivalents(int[] cohorts)` converts a mixed release into the adult count that
  `AlleeRelease.release(year, birds)` (G142) takes, so the Allee threshold is judged on real breeding value.
- `trend()` drives the quest line: GROWING flocks unlock the "Full Marsh" ending; DECLINING flocks (drought or
  poaching, `withAdultSurvival(0.8)`) send Pip to fix adult survival, the entry with the biggest elasticity.

## Model

Cohorts: CHICK (0), JUVENILE (1), SUBADULT (2), ADULT (3+).

```
  [ 0   0   Fs  Fa ]
  [ s0  0   0   0  ]
  [ 0   s1  0   0  ]
  [ 0   0   s2  p  ]
```

Default marsh: s0 0.5, s1 0.7, s2 0.85, p 0.9, Fs 0.15, Fa 0.45, 30 years.

| Quantity | Default value |
|---|---|
| lambda (power iteration, Euler-Lotka checked) | 1.02907 (grows ~2.9 %/yr) |
| lambda with adult survival 0.8 | 0.96056 (declines) |
| Stable ages (chick, juv, sub, adult) | 0.250, 0.122, 0.083, 0.545 |
| Reproductive value (chick = 1) | 1.00, 2.06, 3.03, 3.49 |
| Elasticity of adult survival | 0.627 (largest entry) |
| Elasticity of each juvenile-path survival | 0.094 (equal on s0, s1) |
| 6 chicks released, extinct in 30 yrs (200 seeds) | 88 / 200 |
| 6 adults released, extinct in 30 yrs (200 seeds) | 11 / 200 |

- lambda: shifted power iteration (`(A + I) / 2`, so even a periodic matrix converges), Rayleigh quotient on A.
- Euler-Lotka for this shape: `1 = Fs l2 / L^3 + Fa l3 / (L^4 (1 - p / L))`, with l2 = s0 s1, l3 = l2 s2.
- Elasticity `e_ij = a_ij v_i w_j / (lambda v.w)`; all 16 sum to 1.
- Projection: binomial survival per bird, Poisson chicks (Knuth below mean 40, Box-Muller normal above),
  every draw a splitmix hash of (seed, year, cohort, bird, salt): the same seed always replays the same flock.

## Tests (CraneCohortsTest, 9)

1. lambda solves Euler-Lotka to 1e-9 on four rate sets; default 1.0290662633, drought 0.9605619165.
2. No chicks: lambda equals adult survival, trend DECLINING.
3. Right and left eigenvectors satisfy Aw = lambda w and vA = lambda v to 1e-10, all positive, value rises with age.
4. Elasticities sum to 1; adult survival dominates; s0 and s1 elasticities equal.
5. Deterministic projection settles to the stable ages and growth ratio lambda (1e-9).
6. Big noisy flocks (4000 birds, 10 seeds, 20 years) grow at log lambda within 0.005.
7. Releasing 6 adults beats 6 chicks by more than 40 extinctions in 200 seeds; adult-equivalent hook checked.
8. Seeded runs replay exactly; another seed differs.
9. Bad rates, null settings and malformed cohort vectors are rejected.

## Assets

None needed: reuses Mob_Sky_Crane (G142) and the G119 census board. Optional UI: cohort bars on the board.
