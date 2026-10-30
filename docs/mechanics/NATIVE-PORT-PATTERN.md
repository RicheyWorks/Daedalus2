# Native port pattern (Java core → header-only C++17)

How a seeded daedalus-core minigame core becomes an engine-ready C++ core. First used for G570 (G202 Drought Odds);
follows the layout of the stable-cores ports (#1022). Copy it for the next gap.

## Files

| Piece | Path |
|---|---|
| Rules authority (unchanged) | `daedalus-core/src/main/java/com/daedalus/world/battlefield/<Core>.java` |
| C++ core | `engines/unreal/DaedalusLink/Source/DaedalusLink/Public/Daedalus<Lane><Core>Core.h` |
| Golden-vector writer/checker | `daedalus-core/src/test/java/com/daedalus/world/battlefield/<Lane>CoresParityTest.java` |
| Golden vectors | `engines/unreal/core-test/<lane>_<core>_parity.txt` |
| C++ replay test | `engines/unreal/core-test/<lane>_<core>_core_test.cpp` (+ shared `<lane>_parity.h`) |
| CI | `.github/workflows/<lane>-cores.yml` (g++ and clang++, ASan+UBSan, `-Werror`) |

## Rules

1. **Header-only C++17, standard library only.** No Unreal headers, no UBT, no editor. Unreal wraps the header later.
2. **Same arithmetic, same order.** Port each Java method line for line: same constants, same loop order, same
   clamps. Java `long` → `int64_t`, `>>>` → shift on `uint64_t`, `(long) x << 32` → cast through `int64_t` first.
3. **Randomness.** Use the shared generator that matches the Java side: `DaedalusStableRandom.h` for
   `java.util.SplittableRandom`, `DaedalusPyRandomCore.h` for CPython `random`. If the Java core hashes
   `(seed, run, step, salt)` with the SplitMix64 finalizer (as DroughtOdds does), port that stateless hash inside the
   core's `detail` namespace. Never invent a new generator.
4. **Golden vectors come from Java.** `-Dmarsh.parity.write=true` (or `stable.parity.write`) rewrites the file; a plain
   test run always validates it, so a Java rules change that isn't regenerated breaks the Java build.
5. **Tolerances.** Integers and counts exact. Closed-form doubles: relative 1e-9 (Java prints shortest round-trip).
   Iterative results (bisection, etc.): 1e-7. Monte Carlo that goes through `log`/`cos`/`exp`: allow ±1 hit per
   case and require almost all cases to match exactly, because libm may differ from `StrictMath` in the last ulp.
6. **Unit checks too.** Beyond replay, add a handful of property checks (bounds, monotone, bad input rejected,
   seeded replay identical) so the test explains the maths, not just the numbers.
7. **Verify locally with a standalone compiler** (`g++ -fsanitize=address,undefined`), then let CI run both compilers.
