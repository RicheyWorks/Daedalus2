# DiskSaver: Buddy Berths (G597)

Quest `q_buddy_berths`. NPC: **Dockmother Imelda**, who chalks the long quay into halves, quarters and eighths every dawn and will not let a ship straddle a chalk line.

**The game.** The long quay has 16 berth units, split buddy-style the way a buddy allocator splits memory.
- A ship of size 1, 2, 4 or 8 may only moor on an aligned run of that many free units: its offset must be a multiple of its size. So a size-4 ship fits at 0, 4, 8 or 12, never at 2.
- Ships arrive one at a time. Ship k sails just before arrival k + stay, and its run is free again.
- For each arrival you name an offset or turn the ship away (`-`). A ship with no aligned free run must be turned away. Your score is the number of ships turned away.
- Imelda chalks three dock habits beside your plan:
  - the lowest free offset;
  - the tightest fit: the offset whose largest aligned free block is smallest (the classic buddy best fit);
  - the highest free offset.
- She also keeps the exact best plan. It comes from a memoised search over every offset and every turn-away; the memo key is the arrival plus, for each unit, when it frees. Ties go to the first choice in offset order, with turning away last. Turning a ship away early can be the best move, because it keeps a big aligned run whole for a later ship.
- Verdicts: **snug** matches the best plan; **fair** is no worse than the best habit; **crowded** is worse than every habit.
- Refusals: a plan with the wrong length, an offset that is misaligned or off the quay (`align`), or an offset over a moored ship (`busy`).

**The seed.** A quay is laid from `random.Random(seed_string)`. Those are exactly the draws `DaedalusPyRandomCore.h` (on main) reproduces:
- `n = 7 + randrange(4)`;
- for each ship, `size = 1 << int(random() * 4)` and `stay = 1 + randrange(5)`;
- the ship names: a CPython `shuffle` of 12 names, built from the header's `_randbelow`, keeping the first `n`.

Seeds are strings (the header's CPython str path), for example `buddy-berths|2026-10-26|42`. Hand-laid quays are used for edge cases: up to 10 ships, sizes that are powers of two up to 16, stays from 1 to 16, and **at most 4 ships moored at once**. Ship k is moored for arrivals k to k + stay - 1.

The moored cap bounds the exact search. Before it existed, ten size-1 ships staying 16 arrivals each ran the search for minutes. That quay is now refused as `overlap`. The largest legal search (`worst_legal_ones`: ten size-1 ships, four moored at once) visits 29,194 states, and the test fails if any case passes 60,000. Seeded quays are not capped, because their stays are 1 to 5.

Hand-quay refusals are `no_ships`, `too_many_ships`, `size`, `stay` and `overlap`, answered as `hand_refused kind`.

**How it plugs into Daedalus.** The island streaming pool is a buddy quay:
- each island chunk that streams in asks for a power-of-two slab of the fixed streaming pool;
- it holds the slab for a few later requests, then is evicted.

The hook (`data/islands/disk-saver/buddy-berths-v1.json`) lets a pool trace be replayed as a Buddy Berths quay. Imelda then says whether the slab placement the pool really used was snug, fair or crowded, measured against the best plan and the three habits, and how many chunk requests fragmentation turned away. It is the one DiskSaver game about *where in a fixed pool* a live block goes:
- Defrag Tide (G63) moves blocks that are already placed;
- Tide Chart Cache (G70) chooses what to keep;
- Gantry Sweep (G590) chooses what to read next;
- Buddy Berths chooses the aligned slot each new block takes.

**Code.**
- `engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusDiskSaverBuddyBerthsCore.h`: header-only C++17. No Unreal includes, no exceptions or RTTI. Errors are return codes. It uses the shared `DaedalusPyRandomCore.h` without changing it.
- `tools/streaming/buddy_berths_parity.py --write/--check` writes `engines/unreal/core-test/disksaver_buddy_berths_parity.txt` from CPython. Python is only the fixture generator.
  - 51 cases: 36 seed strings (empty, one-letter and Unicode seeds among them), 7 hand quays and 8 refused hand quays.
  - The hand quays: one dinghy, a whole-quay ship, four eights, halves then the whole quay, size-1 ships that fragment the quay, ten long stays, and the worst legal search.
  - The refused quays: the old slow quay, five moored at once, no ships, eleven ships, two bad sizes and two bad stays.
  - Each laid case has 10 plays, with refusals among them.
- `engines/unreal/core-test/disksaver_buddy_berths_core_test.cpp` replays every line. The existing engines.yml loop over `disksaver_*_core_test.cpp` runs it under gcc ASan/UBSan and clang, and `disksaver_cpp_parity.py --check` keeps the golden file fresh.
