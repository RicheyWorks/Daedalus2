# MORAN01 - Lucky Feather (contest G523)

Code: `daedalus-core/src/main/java/com/daedalus/world/battlefield/LuckyFeather.java`
Tests: `LuckyFeatherTest` (10 tests, including a dense Gaussian brute force). Source only; no Unreal, no assets.

## Story / Daedalus hook

A chick in the G163 studbook aviary hatches with a lucky copper feather. Will the colour spread through the whole
aviary, or vanish? Pip can bring in more carriers from the marsh. The quest asks how many carriers are needed for
the copper feather to take over with a 50 % or 90 % chance.

- `Settings.aviary(r)` uses the G163 aviary cap of 20 cranes, with one carrier.
- `carriersNeeded(target)` is the quest answer.

## Model (Moran process)

Each step one crane breeds in proportion to fitness (carriers r, others 1). Its chick replaces a crane chosen at
random. With i carriers out of N:

```
P+ = r i / (r i + N - i) * (N - i) / N        P- = (N - i) / (r i + N - i) * i / N
fixation(i) = (1 - r^-i) / (1 - r^-N)        (i / N when r = 1)
```

`exact()` solves the absorbing Markov chain directly (tridiagonal Thomas solve). `meanStepsAll()` gives the
expected steps until the allele is fixed or lost. `simulate(runs, seed)` replays the process with splitmix-hashed
draws, so a seed always gives the same aviary.

| r (20-crane aviary) | 1 carrier fixes | mean steps | carriers for 50 % | carriers for 90 % |
|---|---|---|---|---|
| 0.9 | 0.015 | 57 | 15 | 20 |
| 1.0 (neutral) | 0.050 | 71 | 10 | 18 |
| 1.1 | 0.107 | 83 | 6 | 16 |
| 1.5 | 0.333 | 95 | 2 | 6 |
| 2.0 | 0.500 | 92 | 1 | 4 |

The lesson: even a strongly favoured feather (r = 2) is lost half the time from a single chick. Luck rules small
aviaries, which ties back to G163 founder drift.

## Tests (LuckyFeatherTest, 10)

1. A neutral allele fixes with probability i/N.
2. The closed form matches the exact chain to 1e-10 for N from 2 to 30 and seven r values, including r near 1.
3. Brute force: dense Gaussian elimination on the full chain matches the Thomas solve, for both fixation odds and
   mean steps.
4. Seeded simulation (4000 runs) matches the fixation odds within 4 sd and the mean steps within 6 %.
5. Selection tilts the odds: above 1/N when r > 1, below when r < 1, and rising in r.
6. A big flock (N 5000) gives 1 - 1/r from one carrier.
7. `carriersNeeded` is the smallest count that reaches the target.
8. Seeded runs replay exactly; another seed differs.
9. The step cap is reported.
10. Bad tuning is rejected.

## Native C++ core (G568)

Unreal runs C++, so the rules also ship as a header-only C++17 port:
`engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusLuckyFeatherCore.h`
(namespace `daedalus::luckyfeather`, standard library only, no Unreal types). The Java class stays the rules
authority.

- Same splitmix hash and the same expression order as the Java core, so a seed gives the same aviary in both.
- Parity fixture: `engines/unreal/core-test/luckyfeather_parity.txt`, 20 cases written by
  `tools/minigames/LuckyFeatherParity.java` from the Java core.
- `engines/unreal/core-test/luckyfeather_core_test.cpp` checks seeded simulation counts and mean steps exactly.
  It checks the closed form, exact chain and mean steps to 1e-12 relative, plus the carriers-needed answers. It
  also runs unit checks (neutral i/N, closed form = chain, selection, large-N limit, quest minimality, replay, step
  cap, validation): 151 checks in total.
- CI: `engines.yml` builds it with gcc (ASan + UBSan) and with clang.
- Not done here (editor work, out of scope): an ADaedalusDesktopArcade cabinet or Blueprint wrapper.
