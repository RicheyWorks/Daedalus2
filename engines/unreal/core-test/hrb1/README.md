# HRB 1 portable decoder

`DaedalusHerbChordCore.h` decodes replies from `POST /api/v1/audio/herb-chord` (contract: `docs/contracts/hrb-v1/README.md`)
into root, quality, effect, strength and frequencies. Plain C++17, header-only, no Unreal dependencies, so a future
UE component (next to PR44's AUD 1 consumer) can include it unchanged. Any grammar deviation fails the whole decode
and leaves the caller's previous chord untouched.

Parity: `hrb1_test.cpp` decodes the fixture `mint-yarrow-sage.hrb`, whose bytes `IslandHerbChordTest` pins to the
Java controller output, plus 30 accept/reject cases (bounds, order, encoding, size, unknown records).

Run: `python engines/unreal/core-test/hrb1/run_hrb1_core.py --compiler g++ --sanitize` (or `--compiler cl.exe` on Windows).
Not included: Unreal wiring, effect execution or audible playback.
