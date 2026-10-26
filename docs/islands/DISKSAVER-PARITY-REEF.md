# DiskSaver Island: Parity Reef (contest G67, quest `q_parity_reef`)

## Story
The caches are packed (G63), the vault is kept (G59), and the spring is steady (G39). But
the Reef is where DiskSaver Island stores everything, and the storm season is coming.
Reefwarden Xor carved the caches into five stones with a parity block in every row, so any
one stone can be read back from the other four. The quest is to rebuild every smashed stone
before the next storm, for a whole season.

## Mechanics (code: `tools/streaming/parity_reef.py`)
- `stones` stones by `stripes` rows. Each row holds stones-1 seeded data bytes plus one XOR
  parity byte. The parity stone rotates per row (left-symmetric RAID 5: `parity_slot`).
- Each tick:
  1. The keeper rebuilds up to `rebuild_per_tick` missing blocks. Each one is the XOR of
     its row's other blocks and is checked against the original byte.
  2. If the sky is not recharging, a storm strikes with `storm_permille` chance and smashes
     a seeded stone. Every block on it goes missing, then the sky recharges for `calm_ticks`.
  3. If any row has two missing blocks, the game is **failed: data_lost**.
  4. After `season_ticks`, the game is **won**.
- The shipped tuning is tight on purpose: 8 blocks at 2 per tick take 4 ticks, which is
  exactly the calm. A keeper that rebuilds only 1 block per tick loses on some seeds.
- Score on a win = storms weathered x 100.

## Daedalus tie-in
- `stripes_from_defrag(defrag_cfg, stones)`: the Reef stores every G63 Defrag Tide cache
  block once (31 blocks / 4 data per row = 8 rows), and those caches are the G39 Byte
  Spring islands in DSB 1 KiB units.
- It uses the same LCG as G39, G59 and G63, and `receipt()` returns a G12-style activity receipt.

## Checks
`python -m unittest tools/streaming/parity_reef_test.py -v` covers validation, XOR parity
and rotation, reconstructing every block, double-loss refusal, verified rebuilds, tick
errors, the calm window, the keeper winning and idle losing on seeds 1-40, the slow keeper
losing, determinism, the LCG golden, the G63 tie-in and the CLI. The CI job is `Parity Reef`.
Source only, with no editor work.
