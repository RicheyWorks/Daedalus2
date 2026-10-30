# DiskSaver: Gantry Sweep (G590)

Quest `q_gantry_sweep`. NPC: **Railwright Ossian**, who keeps the one gantry crane on the counting-house quay and greases its rail with the same tin since the shattering.

**The game.** The quay has one rail of 40 berths, and the gantry crane rides it the way a disk head rides its cylinders.
- Ships ask for the crane. Each ship has a berth and an arrival tick.
- The crane moves one berth per tick. If it reaches a berth early, it waits there until the ship arrives, then serves it at once.
- You choose the service order. Your score is the total number of ticks the ships spend waiting (serve tick minus arrival tick).
- Ossian chalks four yard habits beside your plan:
  - first come, first served;
  - the nearest ship that has already arrived;
  - the elevator sweep: keep going the same way and turn round only when nobody is waiting ahead;
  - the one-way sweep (C-SCAN): serve the nearest waiting ship at or above the crane, and when none is above, run back to the lowest waiting ship and sweep up again.
- He also keeps the exact best order: fewest waiting ticks, and on ties the first order in lexicographic order. It is a depth-first search in index order that drops a prefix once its waits reach the best found, or once its (ships served, last ship) state has been reached before at no later time and with no more waits. The search is exact for up to 10 ships and agrees with trying every order on every rail of 8 or fewer.
- Verdicts: **sweet** matches the best order; **fair** is no worse than the best habit; **jammed** is worse than every habit.
- Refusals: an order that is too `short` or too `long`, a ship index out of `range`, or a `repeat`ed ship.

**The seed.** A rail is laid from `random.Random(seed_string)`. Those are exactly the draws `DaedalusPyRandomCore.h` (on main) reproduces:
- `start = randrange(40)`;
- `n = 5 + randrange(4)`;
- `pos = sample(range(40), n)`;
- `arrive[i] = int(random() * span)`, where the seed's tide profile sets the span: **calm** 24 ticks, **rush** 6 (ships pile up at once, so order matters most), **spread** 60 (the crane often idles) or **storm**, the harder tier: 24 ticks but `n = 8 + randrange(3)`, so 8 to 10 ships;
- the berth names: a CPython `shuffle` of 12 names, built from the header's `_randbelow`, keeping the first `n`.

The header only seeds from strings, so the seed is a string, for example `gantry-sweep|2026-10-26|42`. Hand-laid rails, up to 10 ships with berths and arrivals up to 10^9, are used for edge cases.

**How it plugs into Daedalus.** The world streamer's load queue is a crane rail:
- each island that asks to stream in is a ship at its pack offset, arriving at the tick it was requested;
- the loader's read head is the crane.

The hook (`data/islands/disk-saver/gantry-sweep-v1.json`) lets a streaming trace be replayed as a Gantry Sweep rail. Ossian then says whether the order the loader really used was sweet, fair or jammed against the best order and the four habits, and how many ticks of island pop-in the sweep cost. It is the one DiskSaver game about the *order* of reads on a single head over time. Defrag Tide (G63) moves the blocks, Tide Chart Cache (G70) chooses what to keep, and Gantry Sweep chooses what to fetch next.

**Code.**
- `engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusDiskSaverGantrySweepCore.h`: header-only C++17. No Unreal includes, no exceptions or RTTI. Errors are return codes. It uses the shared `DaedalusPyRandomCore.h` without changing it.
- `tools/streaming/gantry_sweep_parity.py --write/--check` writes `engines/unreal/core-test/disksaver_gantry_sweep_parity.txt` from CPython. Python is only the fixture generator.
  - 72 cases: 59 seeded rails (33 calm seed strings, empty, one-letter and Unicode among them; 9 rush, 9 spread and 8 storm, with one seed laid under calm, rush and spread) and 13 hand rails.
  - The hand rails: one ship, two ships at the crane's berth, a 10^9 rail, all ships at once, staggered arrivals, a sweep that must turn, and tie-break and edge rails (equal-distance twins, every ship under the crane, a one-way sweep that wraps, both rail ends, a late idle crane, an equal fallback, a ten-ship hand).
  - Each case has 13 plays, with `short`, `long`, `range` and `repeat` refusals among them.
- `engines/unreal/core-test/disksaver_gantry_sweep_core_test.cpp` replays every line. It also checks invariants that hold whatever the golden file says: waits are never negative; travel covers the rail span; playing a habit or the best order agrees with the run and its verdict; and no swap of two neighbours beats the best order. The existing engines.yml loop over `disksaver_*_core_test.cpp` runs it under gcc ASan/UBSan and clang, and `disksaver_cpp_parity.py --check` keeps the golden file fresh.
