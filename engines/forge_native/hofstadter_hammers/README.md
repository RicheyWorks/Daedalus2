# Hofstadter Hammers (G521), native C++17 core

Header-only port of `daedalus-core/.../world/forge/HofstadterHammers.java`, written for a thin Unreal wrapper.

- `hofstadter_hammers.h`: plain `constexpr` functions over `int32_t` with caller-owned buffers. It does no allocation and uses no exceptions, no RTTI and no Unreal headers. Failures come back as `Status {Ok, BadArgument, BufferTooSmall, IndexFell, NullPointer}` (stable values 0..4, `StatusName(s)` for logs).
  `QSequence(n, buf, len)`, `ConwaySequence(n, buf, len)` (fill slots 0..n, slot 0 = 0), `QExtend(from, n, buf, len)` / `ConwayExtend` (grow a cached table without recomputing the prefix), `Q` / `Conway` / `Strike(h, n, scratch, len, &out)`, `GradeClaim`, `ForgemasterLine`, `kMaxN` (10,000,000).
- `hofstadter_hammers_golden.txt`: golden vectors generated from the Java version by `GenHofstadterGolden.java`. Every Q and Conway term 1..3000 is included, then samples up to `MAX_N` (multiples of 99991, 2^k and 2^k +/- 1, and `MAX_N` itself).
- `hofstadter_hammers_test.cpp`: standalone test. It builds both sequences to `kMaxN` and checks them against the golden file. It also checks properties (a(2^k) = 2^(k-1), Conway steps of 0 or 1, a(n) >= n/2, 1 <= Q(n) <= n), that the single-index API matches the sequences, and argument and buffer edges, plus compile-time `static_assert`s.

```
g++     -std=c++17 -O2 -Wall -Wextra -Werror -pedantic hofstadter_hammers_test.cpp -o t && ./t hofstadter_hammers_golden.txt
clang++ -std=c++17 -O2 -Wall -Wextra -Werror -pedantic hofstadter_hammers_test.cpp -o t && ./t hofstadter_hammers_golden.txt
cl /O2 /std:c++17 /W4 /WX /EHsc hofstadter_hammers_test.cpp && hofstadter_hammers_test.exe hofstadter_hammers_golden.txt
```

The header alone also builds with `-fno-exceptions -fno-rtti` and `/EHs- /GR-`. The test needs about 80 MB for the two full sequences.
No CI workflow builds this folder yet.
## Iteration log

Claim 58921. The Java golden fixture `hofstadter_hammers_golden.txt` is the source of truth and is never regenerated or edited (sha256 `f7ba2157...766f`, unchanged).

1. **Clearer status codes.** Added `Status::NullPointer` (null buffer, scratch or output pointer), so a null pointer is no longer reported as `BufferTooSmall` or `BadArgument`. Values are stable (0..4), and `StatusName()` gives a log name. The range check still runs before the pointer checks.
2. **Hardened Q look-back.** `QSequence` now also rejects look-backs at or above `i`, so it can never read a slot it has not filled yet. A `static_assert` proves that a sum of two terms (each <= n) fits `int32_t` for `kMaxN`.
3. **Strict golden reader.** `M` must come first and match `kMaxN`. Rows must have exactly three fields, with no trailing tokens and CRLF tolerated. Each hammer's `n` must strictly increase (no duplicates), 1..3000 must be dense for both hammers, and both must reach `kMaxN`.
4. **Incremental fast path.** `QExtend` and `ConwayExtend` grow an existing table from `from + 1` to `n`, so a cache (for example a `TArray`) is never recomputed from 1. `QSequence` and `ConwaySequence` are now thin calls into them. `ConwayExtend` detects a corrupt prefix (`IndexFell`). Tests check that a chunked fill to 200,000 equals one full fill, plus the extend argument edges.
5. **Independent model and recurrence re-check.** A separate memoized-recursion model has to agree for 1..4000. Both recurrences are re-verified at every n up to `kMaxN`. A mutation run shows why this matters: a one-off error at n = 150,000 slips between the golden samples, but the recurrence check catches it.
6. **Canary buffer guards.** 3,000 randomized cases (fixed seed) use lengths around `n + 1`, with canaries after the buffer. They check that the status follows the length rule, that nothing is written past `len`, and that argument failures leave the whole buffer untouched. Iteration 6 also tightened the header docs on that guarantee. A mutation run (an off-by-one length check) is caught by both the canaries and ASan.
