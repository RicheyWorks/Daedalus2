# Hofstadter Hammers (G521), native C++17 core

Header-only port of `daedalus-core/.../world/forge/HofstadterHammers.java`, written for a thin Unreal wrapper.

- Q hammer: `Q(n) = Q(n - Q(n-1)) + Q(n - Q(n-2))` gives 1, 1, 2, 3, 3, 4, 5, 5, 6, 6, ... (OEIS A005185).
- Conway hammer: `a(n) = a(a(n-1)) + a(n - a(n-1))` gives 1, 1, 2, 2, 3, 4, 4, 4, 5, ... (OEIS A004001).
- Both are 1-indexed, with slot 0 = 0 unused, for `n` up to `kMaxN` = 10,000,000 (the Java `MAX_N`).

The header uses plain `constexpr` functions over `int32_t` with caller-owned buffers. It does no allocation and uses no exceptions, no RTTI, no Unreal headers and no `__int128`. Every function is usable at compile time.

## Files

| File | Role |
| --- | --- |
| `hofstadter_hammers.h` | The core (the only file a game module includes) |
| `hofstadter_hammers_test.cpp` | Standalone test |
| `hofstadter_hammers_golden.txt` | Golden vectors from the Java version (the source of truth, never hand-edited) |
| `GenHofstadterGolden.java` | Generator for the golden file |

## API

| Function | Does | Java |
| --- | --- | --- |
| `QSequence(n, buf, len)` / `ConwaySequence(n, buf, len)` | Fill `buf[0..n]` | `qSequence` / `conwaySequence` |
| `QExtend(from, n, buf, len)` / `ConwayExtend(...)` | Grow a table already valid for `0..from` up to `n` | none |
| `Q(n, scratch, len, &out)` / `Conway(...)` / `Strike(h, ...)` | Single term, using `scratch[0..n]` as work space | `q` / `conway` / `strike` |
| `GradeClaim(h, n, claimed, scratch, len)` | `Grade::Turned` or `Slipped` (any failure grades `Slipped`) | `grade` |
| `ForgemasterLine(g)`, `kQuestId`, `kMaxN` | Same text and values as the Java version | same |
| `StatusName(s)` | Stable log name for a status | none |

## Status codes

| Value | Status | When | Buffer |
| --- | --- | --- | --- |
| 0 | `Ok` | Success | Filled |
| 1 | `BadArgument` | `n` or `from` out of range (the Java `IllegalArgumentException`) | Untouched |
| 2 | `BufferTooSmall` | `len < n + 1` | Untouched |
| 3 | `IndexFell` | A look-back left `1..i-1` (the Java `IllegalStateException`; only happens on a corrupt prefix) | Partly filled |
| 4 | `NullPointer` | A null buffer, scratch or output pointer | Untouched |

Checks run in this order: range, then pointer, then length. Status values are stable.

## Cost

Filling `0..n` is O(n) time and needs `n + 1` `int32_t` slots (about 40 MB at `kMaxN`). A single-term call is O(n) as well, so for repeated lookups keep one table and grow it with `*Extend`. Term sums stay below `2 * kMaxN`, which a `static_assert` checks, so nothing can overflow.

## Unreal wrapper sketch

```cpp
// In a UE module, include the header unchanged (it builds warning-free at high warning levels).
#include "hofstadter_hammers.h"
namespace hh = daedalus::forge::hofstadter;

TArray<int32> Table;  // a cache that grows on demand
int32 StrikeQ(int32 N) {
    const int32 Have = Table.Num() - 1;  // -1 when empty
    if (N > Have) {
        Table.SetNumUninitialized(N + 1);
        const hh::Status S = hh::QExtend(Have < 0 ? 0 : Have, N, Table.GetData(), static_cast<size_t>(Table.Num()));
        if (S != hh::Status::Ok) { UE_LOG(LogTemp, Warning, TEXT("Q: %hs"), hh::StatusName(S)); return 0; }
    }
    return Table[N];
}
```

## Build and test

```
g++     -std=c++17 -O2 -Wall -Wextra -Wshadow -Werror -pedantic hofstadter_hammers_test.cpp -o t && ./t hofstadter_hammers_golden.txt
clang++ -std=c++17 -O2 -Wall -Wextra -Wshadow -Werror -pedantic hofstadter_hammers_test.cpp -o t && ./t hofstadter_hammers_golden.txt
g++     -std=c++17 -O1 -Wall -Wextra -Wshadow -Werror -fsanitize=address,undefined -fno-sanitize-recover=all hofstadter_hammers_test.cpp -o t && ./t hofstadter_hammers_golden.txt
cl /O2 /std:c++17 /W4 /WX /EHsc hofstadter_hammers_test.cpp && hofstadter_hammers_test.exe hofstadter_hammers_golden.txt
```

The header alone also builds with `-fno-exceptions -fno-rtti` and `/EHs- /GR-`. The test needs about 80 MB for the two full sequences and runs in about a second at `-O2`.
No CI workflow builds this folder yet.

## Iteration log

Claim 58921. The Java golden fixture `hofstadter_hammers_golden.txt` is the source of truth and is never regenerated or edited (sha256 `f7ba2157...766f`, unchanged).

1. **Clearer status codes.** Added `Status::NullPointer` (null buffer, scratch or output pointer), so a null pointer is no longer reported as `BufferTooSmall` or `BadArgument`. Values are stable (0..4), and `StatusName()` gives a log name. The range check still runs before the pointer checks.
2. **Hardened Q look-back.** `QSequence` now also rejects look-backs at or above `i`, so it can never read a slot it has not filled yet. A `static_assert` proves that a sum of two terms (each <= n) fits `int32_t` for `kMaxN`.
3. **Strict golden reader.** `M` must come first and match `kMaxN`. Rows must have exactly three fields, with no trailing tokens and CRLF tolerated. Each hammer's `n` must strictly increase (no duplicates), 1..3000 must be dense for both hammers, and both must reach `kMaxN`.
4. **Incremental fast path.** `QExtend` and `ConwayExtend` grow an existing table from `from + 1` to `n`, so a cache (for example a `TArray`) is never recomputed from 1. `QSequence` and `ConwaySequence` are now thin calls into them. `ConwayExtend` detects a corrupt prefix (`IndexFell`). Tests check that a chunked fill to 200,000 equals one full fill, plus the extend argument edges.
5. **Independent model and recurrence re-check.** A separate memoized-recursion model has to agree for 1..4000. Both recurrences are re-verified at every n up to `kMaxN`. A mutation run shows why this matters: a one-off error at n = 150,000 slips between the golden samples, but the recurrence check catches it.
6. **Canary buffer guards.** 3,000 randomized cases (fixed seed) use lengths around `n + 1`, with canaries after the buffer. They check that the status follows the length rule, that nothing is written past `len`, and that argument failures leave the whole buffer untouched. Iteration 6 also tightened the header docs on that guarantee. A mutation run (an off-by-one length check) is caught by both the canaries and ASan.
7. **Compile-time OEIS anchors.** `static_assert` checks that the first 30 terms of both hammers match OEIS A005185 and A004001. These anchors are independent of the Java fixture, so a broken recurrence fails the build before any test runs (mutation-checked: an off-by-one at n = 25 stops compilation). `StatusName` is also checked at compile time.
8. **Strict conversion-warning cleanliness.** The header and the test now build warning-free with `-Wconversion -Wsign-conversion -Wold-style-cast -Wdouble-promotion -Wcast-qual` (plus `-Wuseless-cast` on g++, and `-Wnewline-eof -Wimplicit-int-conversion -Wshorten-64-to-32` on clang). Unreal modules that compile with high warning levels can include the header unchanged. In the test, a signed-index helper `At()` replaces the raw vector indexing, and missing end-of-file newlines were fixed.
9. **README rewrite.** Added API, status-code and file tables (with the buffer state after each status), the check order, time and memory cost, a sketch of a cached `TArray` Unreal wrapper using `QExtend`, and the full build matrix including the sanitizer line.
10. **The reader proves it rejects bad fixtures.** The strict reader is now `ReadGolden(istream&)` and returns a problem count. The test feeds it 10 in-memory corruptions of the real fixture: a wrong value, a trailing token, a duplicate row, a gap in the dense range, a missing, wrong or second `M` header, an unknown tag, an out-of-range `n`, and a lost `kMaxN` row. It must reject every one and still accept CRLF. The file on disk is only read. The golden replay now reports one aggregated check plus a problem count, so the total check count is lower, but every row is still compared.
