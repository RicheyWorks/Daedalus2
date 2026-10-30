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

**Worked examples.** These come straight from the golden file.

- **Late idle** (`late_idle`). The crane starts at berth 20. Ships wait at berths 10, 30 and 25, all arriving at tick 1000, and at berth 20 arriving at tick 2000.
  - **sweet**, order `1,2,0,3`: the crane is at 30 at tick 1000, then 25 (5 ticks waited), then 10 (20 ticks waited), then back to 20 by tick 2000. That is 25 waiting ticks, as good as the best order.
  - **fair**, order `2,1,0,3` (nearest ship, elevator sweep and one-way sweep all choose it): 30 waiting ticks. That is worse than the best order, but no worse than the best habit.
  - **jammed**, order `0,1,2,3`: 45 waiting ticks, worse than every habit.
- **Scan turns** (`scan_turns`). The crane starts at berth 20; ships are at 25, 15, 30, 5 and 35, arriving at ticks 0, 0, 1, 2 and 9.
  - The elevator sweep `0,2,4,1,3` (up to 35, then back down) is also the best order: 98 waiting ticks, **sweet**.
  - First come, first served gives 148 ticks and the nearest ship gives 128. Played as your own order, each of those is **jammed**, because the best habit gives 98.
- **Refusals** on the same rail: `0,1,2,3` is `short`; `0,1,2,3,4,0` is `long`; `0,1,2,3,5` is out of `range`; `0,1,2,3,0` is a `repeat`; an empty order `-` is `short`.
- **Refused hand rails** answer `hand_refused` and have no plays:
  - no ships: `no_ships`;
  - 11 ships: `too_many_ships`;
  - a start, berth or arrival past 10^9: `coord`.

**API surface for a future Unreal boundary layer.** This section is docs only; there is no Unreal code here. Everything sits in `DaedalusDiskSaver::GantrySweep`, has no exceptions or RTTI, and returns `Error` codes. A UE wrapper (for example a `UGantrySweepSubsystem`) would only convert types at the edge.

| Call | In | Out | Errors |
|---|---|---|---|
| `FromSeed(seed, profile, layout)` | UTF-8 `std::string` (up to 4096 bytes), `Profile::{Calm, Rush, Spread, Storm}` | `Layout` (start, ships with label, pos, arrive) | `Seed` |
| `MakeHand(start, {pos, arrive}..., layout)` | 1 to 10 pairs, every value in 0..10^9 | `Layout` | `NoShips`, `TooManyShips`, `Coord` |
| `Fcfs`, `Sstf`, `Scan`, `Cscan`, `Best(layout)` | `Layout` | `Order` (ship indices) | none |
| `Run(layout, order, waits, travel)` | a valid order | waits and travel as `int64` (under 2^40) | none; call `CheckOrder` first |
| `CheckOrder(layout, order)` | any order | | `Short`, `Long`, `Range`, `Repeat` |
| `Play(layout, order, result)` | any order | `PlayResult{Waits, Travel, Verdict}` | as `CheckOrder` |
| `ErrorName`, `VerdictName`, `ProfileName` | enum value | a stable lowercase string | none |

Boundary notes:
- Use `FString` to UTF-8 for seeds and `int64` to `int64` for berths and ticks.
- Map `Order` to `TArray<int32>` only after `CheckOrder`.
- `Best` on a storm rail of 10 ships is still exact. Run it off the game thread, or cache it per layout.
- The strings are what the hook JSON and the golden file use, so keep them as the wire values.

**How it plugs into Daedalus.** The world streamer's load queue is a crane rail:
- each island that asks to stream in is a ship at its pack offset, arriving at the tick it was requested;
- the loader's read head is the crane.

The hook (`data/islands/disk-saver/gantry-sweep-v1.json`) lets a streaming trace be replayed as a Gantry Sweep rail. Ossian then says whether the order the loader really used was sweet, fair or jammed against the best order and the four habits, and how many ticks of island pop-in the sweep cost. It is the one DiskSaver game about the *order* of reads on a single head over time. Defrag Tide (G63) moves the blocks, Tide Chart Cache (G70) chooses what to keep, and Gantry Sweep chooses what to fetch next.

**Load-queue mapping (sample).** The world streamer's island load queue maps onto a rail like this. These notes are for the integrator; nothing is enqueued by this repo.

| Load queue | Gantry Sweep | Example |
|---|---|---|
| island stream request | ship | `isle_lanternfen` |
| pack offset of the request, in 64 KiB pages (clamped to 0..10^9) | berth `pos` | 1840 |
| request tick (frames since the streamer started) | `arrive` | 312 |
| loader read head offset at trace start | `start` | 1795 |
| read order the loader actually used | the played `order` | `2,0,1` |
| frames from request to read | waiting ticks | |
| loader policy: FIFO, nearest-offset, elevator, one-way | the `fcfs`, `sstf`, `scan` and `cscan` habits | |
| queue depth: up to 8 is `calm`, `rush` or `spread` by request spacing; 9 or 10 is `storm` | profile | |
| more than 10 queued requests | split into windows of up to 10 (`too_many_ships` otherwise) | |

A replay takes a trace window, builds it with `MakeHand(start, {pos, arrive}...)`, then calls `Play(layout, loader_order)`. Ossian's verdict line and the waiting-tick gap to `Best` are reported back as `verdict` and pop-in ticks.

**Code.**
- `engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusDiskSaverGantrySweepCore.h`: header-only C++17. No Unreal includes, no exceptions or RTTI. Errors are return codes. It uses the shared `DaedalusPyRandomCore.h` without changing it.
- `tools/streaming/gantry_sweep_parity.py --write/--check` writes `engines/unreal/core-test/disksaver_gantry_sweep_parity.txt` from CPython. Python is only the fixture generator.
  - 81 cases: 59 seeded rails (33 calm seed strings, empty, one-letter and Unicode among them; 9 rush, 9 spread and 8 storm, with one seed laid under calm, rush and spread), 17 laid hand rails and 5 refused ones.
  - The hand rails: one ship, two ships at the crane's berth, a 10^9 rail, all ships at once, staggered arrivals, a sweep that must turn, and tie-break and edge rails (equal-distance twins, every ship under the crane, a one-way sweep that wraps, both rail ends, a late idle crane, an equal fallback, a ten-ship hand), guard rails (the largest coordinates, ten far ships, duplicate arrival ticks), and 5 refused hands (`no_ships`, `too_many_ships`, three kinds of `coord`).
  - Each laid case has 13 plays, with `short`, `long`, `range` and `repeat` refusals among them.
- `engines/unreal/core-test/disksaver_gantry_sweep_core_test.cpp` replays every line. It also checks invariants that hold whatever the golden file says: waits are never negative; travel covers the rail span; playing a habit or the best order agrees with the run and its verdict; no swap of two neighbours beats the best order; and on every rail of up to 8 ships, the pruned search equals an all-orders oracle. The existing engines.yml loop over `disksaver_*_core_test.cpp` runs it under gcc ASan/UBSan and clang, and `disksaver_cpp_parity.py --check` keeps the golden file fresh.
