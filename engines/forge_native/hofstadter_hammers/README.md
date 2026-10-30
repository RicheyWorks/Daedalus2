# Hofstadter Hammers (G521), native C++17 core

Header-only port of `daedalus-core/.../world/forge/HofstadterHammers.java`, written for a thin Unreal wrapper.

- `hofstadter_hammers.h`: plain `constexpr` functions over `int32_t` with caller-owned buffers. It does no allocation and uses no exceptions, no RTTI and no Unreal headers. Failures come back as `Status {Ok, BadArgument, BufferTooSmall, IndexFell}`.
  `QSequence(n, buf, len)`, `ConwaySequence(n, buf, len)` (fill slots 0..n, slot 0 = 0), `Q` / `Conway` / `Strike(h, n, scratch, len, &out)`, `GradeClaim`, `ForgemasterLine`, `kMaxN` (10,000,000).
- `hofstadter_hammers_golden.txt`: golden vectors generated from the Java version by `GenHofstadterGolden.java`. Every Q and Conway term 1..3000 is included, then samples up to `MAX_N` (multiples of 99991, 2^k and 2^k +/- 1, and `MAX_N` itself).
- `hofstadter_hammers_test.cpp`: standalone test. It builds both sequences to `kMaxN` and checks them against the golden file. It also checks properties (a(2^k) = 2^(k-1), Conway steps of 0 or 1, a(n) >= n/2, 1 <= Q(n) <= n), that the single-index API matches the sequences, and argument and buffer edges, plus compile-time `static_assert`s.

```
g++     -std=c++17 -O2 -Wall -Wextra -Werror -pedantic hofstadter_hammers_test.cpp -o t && ./t hofstadter_hammers_golden.txt
clang++ -std=c++17 -O2 -Wall -Wextra -Werror -pedantic hofstadter_hammers_test.cpp -o t && ./t hofstadter_hammers_golden.txt
cl /O2 /std:c++17 /W4 /WX /EHsc hofstadter_hammers_test.cpp && hofstadter_hammers_test.exe hofstadter_hammers_golden.txt
```

The header alone also builds with `-fno-exceptions -fno-rtti` and `/EHs- /GR-`. The test needs about 80 MB for the two full sequences.
No CI workflow builds this folder yet.