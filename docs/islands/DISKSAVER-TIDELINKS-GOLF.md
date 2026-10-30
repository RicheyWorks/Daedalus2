# DiskSaver: Tidelinks Golf (G598)

Quest `q_tidelinks_golf`. NPC: **Greenkeeper Talwyn**, who mows the links on the dunes above the harbour and keeps the club rack, the wind sock and the scorecards.

**The game.** A seeded links course has 4 to 6 holes, each laid out on a straight line from tee to pin.
- Each hole has:
  - a length in metres, a multiple of 10;
  - a par: 3 up to 220 m, 4 up to 400 m, otherwise 5;
  - a wind from -3 (head) to +3 (tail);
  - often a 20 m water band.
- Each shot picks one of eight clubs:

  | Code | Club | Carry |
  |---|---|---|
  | `D` | driver | 220 m |
  | `W` | 3-wood | 190 m |
  | `5` | 5-iron | 160 m |
  | `7` | 7-iron | 130 m |
  | `9` | 9-iron | 100 m |
  | `S` | wedge | 60 m |
  | `C` | chip | 20 m |
  | `P` | putter | (rolls; see below) |

- The ball flies the carry plus 10 m per wind step (never under 10 m) toward the pin, and can go past it.
- Landing in the water, or more than 50 m beyond either end of the hole, costs a penalty stroke and the ball stays where it was.
- A shot that lands on the pin holes out (an ace from the tee). The putter holes out from 10 m or less; otherwise it rolls 10 m toward the pin and ignores the wind.
- A hole is capped at 10 strokes, penalties included.
- Your score is total strokes, shown against par (`E`, `+2`, `-3`).
- Talwyn chalks three caddie habits beside your card:
  - **safe**: the longest club that lands no more than 10 m past the pin and out of the water;
  - **bold**: the same, but ignores the water until it has found it once on the hole;
  - **lay-up**: the longest club that does not pass the pin, avoiding water.
- She also keeps the exact best card: fewest strokes per hole, found by a fixed-point search over every ball position (multiples of 10 m). Shot by shot, ties go to the first club in club order.
- Verdicts: **masterful** matches the best card; **steady** is no worse than the best habit; **rough** is worse than every habit.
- Refusals, with the hole number:
  - `holes`: the wrong number of holes on the card;
  - `club`: an unknown club;
  - `cap`: over 10 strokes;
  - `short`: the clubs end before the ball is holed;
  - `extra`: clubs after it is holed.
- Hand-course refusals:
  - `no_holes`;
  - `too_many_holes` (more than 9);
  - `length` (not 30 to 600 m in tens);
  - `wind` (not -5 to +5);
  - `water` (not a multiple of 10 between 10 m and 30 m short of the pin).

**The seed.** A course is laid from `random.Random(seed_string)` with draws `DaedalusPyRandomCore.h` (on main, unchanged) reproduces:
- `n = 4 + randrange(3)`;
- for each hole:
  - `length = 100 + 10 * randrange(41)`;
  - `wind = randrange(7) - 3`;
  - `wet = random() < 0.7`;
  - `water = 30 + 10 * randrange((length - 70) // 10)` (used only when wet);
- then the hole names: a CPython `shuffle` of 12 names, built from `_randbelow`.

Seeds are strings, for example `tidelinks-golf|2026-10-30|42`.

**How it plugs into Daedalus.** The links are a file read planner on DiskSaver Island:
- each hole is one asset file to fetch, and its length is the bytes still to read;
- each club is a read block size;
- the wind is I/O load, which makes every block land a little longer or shorter;
- the water is a bad-sector band that forces a retry;
- the putter is the small final read.

The hook (`data/islands/disk-saver/tidelinks-golf-v1.json`) lets a streaming trace of block reads be replayed as a card. Talwyn then says whether the loader's block choices were masterful, steady or rough, and how many requests above the best plan they cost. It is the one DiskSaver game about choosing *read sizes* to reach an exact length:
- Gantry Sweep (G590) orders reads on one head;
- Buddy Berths (G597) places blocks in a pool;
- Tidelinks Golf chooses how big each read is.

**Code.**
- `engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusDiskSaverTidelinksGolfCore.h`: header-only C++17. No Unreal includes, no exceptions or RTTI. Errors are return codes. It uses the shared `DaedalusPyRandomCore.h` without changing it.
- `tools/streaming/tidelinks_golf_parity.py --write/--check` writes `engines/unreal/core-test/disksaver_tidelinks_golf_parity.txt` from CPython. Python is only the fixture generator.
  - 53 cases: 36 seed strings (empty, one-letter and Unicode seeds among them), 9 hand courses and 8 refused hand courses.
  - The hand courses: a 30 m hole, aces at 220 m and in a tailwind, long holes into and with the wind, water at a club's carry, water just short, nine holes, putter only, and a shot past the pin.
  - Each laid case has 12 cards with every refusal among them.
- `engines/unreal/core-test/disksaver_tidelinks_golf_core_test.cpp` replays every line. It also checks invariants whatever the golden file says: no habit beats the best card; the best card plays masterful; every best hole is 1 to 10 shots; and a hole that can be aced is aced. The existing engines.yml loop over `disksaver_*_core_test.cpp` runs it under gcc ASan/UBSan and clang, and `disksaver_cpp_parity.py --check` keeps the golden file fresh.
