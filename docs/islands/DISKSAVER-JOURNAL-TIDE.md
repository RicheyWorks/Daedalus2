# DiskSaver Island: Journal Tide (contest G79, quest `q_journal_tide`)

## Story
Every island save reaches the coral shelf (G78) through the tide journal. Saves wait in the
keeper's satchel until a commit writes them down, and every line is sealed with a checksum.
Storm surges come without warning. Scribe Fsync asks the player to spend a season's ink
wisely: commit too often and the ink runs out, commit too rarely and the sea takes the saves.

## Mechanics (code: `tools/streaming/journal_tide.py`)
- Each step, a seeded island save goes into the buffer (the satchel).
- A **surge** (`surge_permille` after each save) loses every uncommitted save.
- A **commit** (one of `io_budget`) writes the buffer as records `seq|island|value|crc32`.
  With `torn_permille`, a surge strikes mid-commit: one record is torn in half, and that
  record and the rest of the buffer are lost.
- **Recovery** (`recover`) replays records in order, checks each CRC32 and sequence number,
  and stops at the first bad one. The torn tail is dropped. After every surge, the rebuilt
  state must equal the durable saves exactly (asserted in code and in the tests).
- Losing more than `max_lost` saves is **failed: too_many_lost**. At the season end, any
  remaining buffer is committed if ink is left, otherwise it is lost.
- With the shipped data on seeds 1-40:
  - `paced_policy` (commit when the buffer reaches ceil(saves left / commits left)) wins 40.
  - `every_k(2)` burns the ink by mid-season and wins 0.
  - `end_only_policy` wins at most 5.

## Daedalus tie-in
- `islands_from_coral()`: the saves riding this journal are the G78 Coral Wear saves (the
  G70 / G39 hot islands plus the G59 archives), with the same weights. The shipped data
  equals that.
- It uses the same LCG as the DiskSaver lane, and `receipt()` returns a G12-style activity receipt.

## Checks
`python -m unittest tools/streaming/journal_tide_test.py -v`; the CI job is `Journal Tide`.
Source only, with no editor work.
