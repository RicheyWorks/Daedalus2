# Padovan Plinths (G526), native C++17 core

Header-only port of `daedalus-core/.../world/forge/PadovanPlinths.java`, written for a thin Unreal wrapper.

- `padovan_plinths.h`: plain `constexpr` functions over `int64_t` with a portable checked add. It uses no `__int128`, no exceptions, no RTTI and no Unreal headers. Failures come back as `Status {Ok, BadArgument, Overflow}`.
  `Padovan(n, &out)`, `IndexOf(v)`, `IsPadovan(v)`, `RunSum(a, b, &out)`, `GradeClaim(n, claimed)`, `ForgemasterLine(g)`, `kMaxIndex` (156).
- `padovan_plinths_golden.txt`: golden vectors generated from the Java version by `GenPadovanGolden.java`. They cover every term up to the int64 limit, a membership and position scan, overflow edges and sums of runs.
- `padovan_plinths_test.cpp`: standalone test.

```
g++     -std=c++17 -Wall -Wextra -Werror padovan_plinths_test.cpp -o t && ./t padovan_plinths_golden.txt
clang++ -std=c++17 -Wall -Wextra -Werror padovan_plinths_test.cpp -o t && ./t padovan_plinths_golden.txt
cl /std:c++17 /W4 /WX /EHsc padovan_plinths_test.cpp && padovan_plinths_test.exe padovan_plinths_golden.txt
```

The header alone also builds with `-fno-exceptions -fno-rtti` and `/EHs- /GR-`.
No CI workflow builds this folder yet.