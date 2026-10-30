# DiskSaver: seed and draw spec (G581)

This spec says how the DiskSaver tools in `tools/streaming` seed Python's `random.Random` and which draws they make. A C++ (or any other) port that follows it gets the same seeded layouts and simulations as the Python tools, so the layout generators can move out of Python. It documents existing behaviour and changes none of it.

The spec is backed by three things:
- **Golden draw sequences.** `engines/unreal/core-test/disksaver_seed_spec_parity.txt` is written by `tools/streaming/disksaver_seed_spec.py` (`--write` / `--check`). The same script runs `--check` from `disksaver_cpp_parity.py`, so the existing engines.yml step catches a stale file.
- **A pure-Python reference.** `SpecRandom` in that script never touches the `random` module, and every golden line must agree with both CPython and `SpecRandom` before it is written. That shows the spec below is complete.
- **A C++ reference.** `DaedalusDiskSaverSeedSpecCore.h` is header-only, engine-free C++17. `disksaver_seed_spec_core_test.cpp` replays the golden file in the existing `disksaver_*_core_test.cpp` loop: gcc ASan/UBSan and clang in CI, MSVC `/W4 /WX /EHsc /GR-` locally.

## 1. Seeding

**Layout tools (G546, G549-G566)** build a key string and hash it:

    key  = f"{census_doc.get('snapshot_date')}|{','.join(LABELS)}|{seed}".encode("utf-8")
    rng  = random.Random(int(hashlib.sha256(key).hexdigest(), 16))

- `snapshot_date` is the census field as Python formats it. A missing field gives the text `None`.
- `LABELS` is the tool's own label list (see the table). Labels are `world:slot`, with slot as a decimal int, or world ids for G546/G552. They are joined with `,`, with no spaces and no trailing comma.
- `seed` is the `--seed` int in decimal, with a `-` sign when negative. So seed `-3` gives a different key than seed `3`.
- The seed passed to `random.Random` is the **256-bit integer** value of the SHA-256 digest, read big-endian. It is *not* the key string. `random.Random(key_str)` would take the str/bytes path, which appends SHA-512 and gives a different stream.

**Simulations (G166 Tide Clocks, G171 Lighthouse Leases, G175 Tidemark Chunks, G179 Bottle Census)** call `random.Random(c.seed)` with the config's integer `seed`. Tide Clocks only checks that it is an int, so a negative seed is allowed. The other three accept 0 to 2^31-1.

**Integer seeding (CPython `random_seed`, the same in 3.10 and 3.13):**
- The key is `abs(n)`, split into 32-bit limbs, least significant first. High zero limbs are dropped, and `n == 0` gives the key `[0]`. Negative seeds are therefore the same stream as their absolute value.
- The limbs go to `init_by_array`. A SHA-256 seed is up to 8 limbs: limb *i* is digest bytes `[28-4i, 32-4i)` read big-endian, and leading zero limbs are dropped.

## 2. MT19937 as CPython uses it

```
init_genrand(s): mt[0] = s; mt[i] = 1812433253 * (mt[i-1] ^ (mt[i-1] >> 30)) + i   (mod 2^32), i = 1..623; mti = 624
init_by_array(key):
  init_genrand(19650218); i = 1; j = 0
  repeat max(624, len(key)) times:
    mt[i] = (mt[i] ^ ((mt[i-1] ^ (mt[i-1] >> 30)) * 1664525)) + key[j] + j     (mod 2^32)
    i += 1; j += 1; if i >= 624: mt[0] = mt[623]; i = 1;  if j >= len(key): j = 0
  repeat 623 times:
    mt[i] = (mt[i] ^ ((mt[i-1] ^ (mt[i-1] >> 30)) * 1566083941)) - i            (mod 2^32)
    i += 1; if i >= 624: mt[0] = mt[623]; i = 1
  mt[0] = 0x80000000
genrand (getrandbits(32)): when mti >= 624 twist all 624 words in place, k = 0..623:
    y = (mt[k] & 0x80000000) | (mt[(k+1) % 624] & 0x7fffffff)
    mt[k] = mt[(k+397) % 624] ^ (y >> 1) ^ (y & 1 ? 0x9908b0df : 0);   mti = 0
  y = mt[mti++]; y ^= y >> 11; y ^= (y << 7) & 0x9d2c5680; y ^= (y << 15) & 0xefc60000; y ^= y >> 18
```

## 3. Draw methods (CPython 3.10 and 3.13 make identical draws)

| method | draws |
|---|---|
| `random()` | `a = genrand >> 5`, `b = genrand >> 6`, result `(a * 2^26 + b) / 2^53`: two words. The golden file stores the integer `a * 2^26 + b`. |
| `getrandbits(k)` | `k == 0` gives 0 with no draw. `k <= 32` gives `genrand >> (32 - k)`. `k > 32` draws `ceil(k / 32)` words, least significant first, and the last word is shifted down by `32 - (k mod 32)` when `k` is not a multiple of 32. |
| `_randbelow(n)` | `k = n.bit_length()`, `r = getrandbits(k)`, repeated while `r >= n`. `n = 1` still draws one word per try, until the top bit is 0. CPython's `_randbelow(0)` never returns, so the public methods check their arguments first. |
| `randrange(stop)` | `_randbelow(stop)`. `stop <= 0` raises ValueError with no draw. |
| `randrange(a, b, step)` | width = `b - a`. With `step == 1`: `a + _randbelow(width)`. Otherwise `n = (width + step - 1) // step` (step > 0) or `(width + step + 1) // step` (step < 0), and the result is `a + step * _randbelow(n)`. `n <= 0` or `step == 0` raises ValueError. |
| `randint(a, b)` | `randrange(a, b + 1)`. |
| `choice(seq)` | `seq[_randbelow(len(seq))]`. An empty sequence raises IndexError with no draw. |
| `shuffle(x)` | `for i = len(x)-1 down to 1: j = _randbelow(i + 1); swap x[i], x[j]`. The result depends only on `len(x)`. |
| `sample(pop, k)` | `n = len(pop)`; `0 <= k <= n` or ValueError. `setsize = 21`, plus `4 ** ceil(log(3k, 4))` when `k > 5`. `3k` is never a power of 4, so the integer "smallest power of 4 >= 3k" is equal; the script checks this for k up to 100,000. If `n <= setsize`, take from a pool: `j = _randbelow(n - i)`, `result[i] = pool[j]`, `pool[j] = pool[n - i - 1]`. Otherwise, set branch: `j = _randbelow(n)`, redrawn while j has already been taken. The picks depend only on `n` and `k`. |

**Python-version notes (3.10 vs 3.13):**
- The streams for every method above are the same. The golden file written by Python 3.10 on Windows (the CI version) and by 3.13 is byte-identical.
- The differences are argument checks, and the tools never hit them:
  - 3.11 removed `shuffle(x, random)` and sample from a `set`.
  - 3.12 made `randrange` reject non-integer floats (3.10 only warns).
  - 3.11+ `seed()` accepts only None, int, float, str, bytes and bytearray.
- One trap for anyone recording draws: a `random.Random` subclass that overrides `random()` but not `getrandbits()` makes `__init_subclass__` switch `_randbelow` to the float-based `_randbelow_without_getrandbits`, which gives a different stream. The recorder in the script overrides both.

## 4. Per-tool draws

Draw counts are from the golden cases: the real `tools/world_census` fixture census (3 islands: `alpha:2`, `alpha:9`, `beta:4`) with seeds 0, 1, 7, 42 and -3; synthetic censuses `syn7` (7 islands) and `syn14` (14 islands) with seeds 0 and 42, skipped where the tool refuses more islands; and the shipped configs for the simulations with seeds 1, 7, 42 and the shipped seed. The golden file records each tool's first 400 draws exactly as the tool makes them.

| tool | LABELS in the key | draws, in order |
|---|---|---|
| G546 Census Riddles | sorted world ids | `shuffle(9 kinds)`; then, for each `world_ram`/`world_disk`/`max_resident` riddle posed in shuffled order, `choice(worlds with islands)` |
| G549 Last Crate | sorted `world:slot` (all islands) | `shuffle(deck)` |
| G550 Quay Duel | sorted `world:slot` (all islands, max 400) | `shuffle(line)` |
| G551 Fleet Soundings | sorted `world:slot` of all ships | `shuffle(ships)`. Then up to 2000 tries of one `choice(placements)` per ship (longest first); then `choice(differing cells)` per hint until the solution is unique |
| G552 Harbour Cryptogram | sorted world ids | `sample(facts, min(3, n))`; `shuffle(26 letters)`, repeated until it is a derangement; `sample(used letters, min(max(2, u // 5), u - 1))` |
| G553 Smugglers Island | sorted `world:slot` (max 40) | `randrange(suspects)` |
| G554 Tide Lock | sorted `world:slot` (max 60) | `shuffle(fleet)`; `randint(0, 25)` per boat |
| G555 Watchfires | sorted `world:slot` (max 40) | `shuffle(world chains)`; `choice(c1)`, `choice(c2)` per adjacent pair of chains; if more than 2 islands, `randrange(n)` per island |
| G556 Manifest Match | sorted `world:slot` | if more than 12 islands, `sample(islands, 12)`; `shuffle(2 * pairs cards)` |
| G557 Twin Pilots | sorted `world:slot` (islands only, max 8) | `shuffle(chains)`; `choice(chain)` per chain; `sample(placed nodes, min(2, i))` per buoy; if more than 3 nodes, `randrange(nodes)` for nodes 1..n-1 |
| G558 Quayside Shove | the up-to-3 heaviest islands (by G206 RAM, then label), sorted | up to 200 tries of: `randint(2, 5)`, `sample(25 inner cells, w)`; `sample(floor, crates)`; `choice(free floor)`; 60 times `choice("UDLR")`, plus `random() < 0.7` when a crate is behind a legal step |
| G559 Sack Chute | sorted `world:slot` (max 6; spare bins are not in the key) | `randrange(3)` per bin, spares included (min 4 bins) |
| G560 Seal Roll | first 4 sorted `world:slot` | up to 100 tries of: `randint(3, 6)`, `sample(25 inner cells, w)`, `sample(floor, marks + 2)` |
| G561 Channel Dash | first 5 sorted `world:slot`, then `lane:k` pads to 3 | up to 200 tries of: per lane, `1 + assets % 3` times `randrange(9)`, `randint(1, 3)`; then `choice((-2, -1, 1, 2))`; then `randrange(9)` twice (dock, start) |
| G562 Boom Defence | first 6 sorted `world:slot` | `randrange(7)`; `randrange(7)` per even column (5 of 9); `sample(sites, min(12, n))`; `randrange(2)` per skiff |
| G563 Salvage Sale | first 6 sorted `world:slot`, then `spare:k` pads to 5 | `randrange(5)` per lot |
| G564 Rope Run | first 5 sorted `world:slot` | up to 100 tries of: `randint(3, 5)`, `sample(30 cells, c)`, `sample(free, cleats + 2)` |
| G565 Belfry Changes | first 6 sorted `world:slot`, then `spare:k` pads to 5 | `shuffle(bells)`, repeated while the row is still rounds |
| G566 Tram Shunt | first 6 sorted `world:slot`, then `spare:k` pads to 6 | up to 100 times `shuffle(6 wagons)`, until the yardman's greedy plan is not optimal |
| G166 Tide Clocks | int seed | `randint(-max_skew, max_skew)` per island; per step `randrange(1000)`; on an edit, `randrange(n)` and `randrange(saves)`; otherwise `sample(range(n), 2)` |
| G171 Lighthouse Leases | int seed | `randint(-d, d)` per keeper; `randrange(2)` per epoch; per epoch `randrange(n)` (first) or `randrange(n - 1)`; per tick after the first, `randrange(1000)` for the write, and if pauses are on, `randrange(1000)` and maybe `randint(1, max_pause)` |
| G175 Tidemark Chunks | int seed | `randrange(256)` per initial byte; per version and island `randint(0, edits)` edits, each `randint(1, max_run)`, `randrange(len + 1)`, `randrange(1000)`, then `randrange(256)` per inserted or overwritten byte |
| G179 Bottle Census | int seed | `randint(0, max_skew)` per island; per tick and island with a balance, `randrange(1000)`, and on a send `randint(1, min(max_amount, bal))`, `randrange(n - 1)`; each bottle and marker posted draws `randint(1, max_delay)` |

Tools that hash with SHA-256 but use their own 32-bit LCG rather than `random` (G151 Barnacle Scrub, Save Vault, Storm Season Archive) are outside this spec.

## 5. The shared RNG header (#1018)

**Where it is.**
- PR #1018 ("PyRandom parity: CPython fixture + core test for the PRNG on its own", branch `claude/pyrandom-parity`) is **still open and not merged**. Its fixture `engines/unreal/core-test/pyrandom_parity.txt`, its test `pyrandom_core_test.cpp` and its `tools/minigames/pyrandom_parity.py` are not on main.
- The header itself, `engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusPyRandomCore.h`, is already on main; it came in with the Prism cabinet commits. The PR branch's copy adds `Shuffle()`. This spec read both copies and changes neither.

**What matches.**
- Its MT19937 core (`init_genrand`, `init_by_array`, twist, tempering) matches section 2.
- `U32`, `Below` (for n < 2^32), `RandomDouble`, `SampleIndices` and the branch's `Shuffle` make the same draws as CPython. They were checked against CPython on string seeds while writing this spec.

**What differs, for these tools.**
1. **Seeding.** `PyRandom` only seeds from a **string**, through CPython's str path (utf-8 bytes plus SHA-512, `version=2`). The DiskSaver tools seed with an **integer** (the SHA-256 value, or the config int). The header has no integer or limb entry point (`InitByArray` is private), so feeding it the key string gives a different stream. A port needs an integer or limb seed, as in `DaedalusDiskSaverSeedSpecCore.h` `Seed(words)`.
2. **Range.** `Below`, `RandRange` and `ChoiceIndex` take 32-bit sizes. There is no `getrandbits(k > 32)`, no `randint` or `randrange(a, b, step)`, and no `choice` of a negative-offset range. These are simple to add on top of `Below`, as the spec shows.
3. **Errors.** `Below(0)` and `ChoiceIndex(0)` return 0 with no draw, and `SampleIndices(n, k > n)` returns empty. CPython raises in all three cases (and its `_randbelow(0)` never returns). The DiskSaver tools never make these calls with bad arguments.
4. **`Shuffle`** is only on the PR branch, not in main's copy.

The DiskSaver reference header is separate, so #1018 and the Prism cabinets that use `DaedalusPyRandomCore.h` are untouched.

## 6. Golden file format

```
C name                 case
K hex                  sha256 key bytes (tool cases; checked in Python)
S n                    the integer given to random.Random, hex, '-' when negative
D op args / O result   u32 | random (53-bit integer) | bits k | below n | range a b step | int a b |
                       choice n (index) | shuffle n (permutation of range(n)) | sample n k (indices) | skip m (last word)
                       a refused argument gives `O error ValueError` / `O error IndexError` and draws nothing
```

The spec cases cover:
- Seeds 0, 1, 7, 42, -42, 2^31-1, 2^32-1, 2^32, 2^64-1, 10^30, 2^255+12345, 2^256-1, and a 700-limb seed (more limbs than the 624-word state).
- Every method, with bits 0 to 64, `below` up to 2^63-1, steps of ±7, `sample` on both sides of the setsize edge (21/22 with k=2, 84/85/86 with k=6), refusals, and a skip of 620 words that crosses the first twist.

C++ reference caps: 2^16 seed limbs, populations up to 2^20, and |range bounds| up to 2^61 so widths and step products fit in 64 bits. Golden-file mutations: 16 of 17 sampled single-line edits fail. The one that passes, `S 0` to `S 00`, is the same seed. 300 random line mutations never crash.
