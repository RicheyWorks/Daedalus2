# Minesweeper saved-board slice

Minesweeper already had first-reveal safety, flood reveal, flags, chord, three
difficulties and terminal states. This slice adds exact-board save/resume through
the existing `Game`/`Driver` facilities and native cabinet, without changing its rules.

The cabinet offers Save board, Continue saved board and Save & Close. Saving uses
the existing bounded temporary-file replacement helper and the dedicated
`Saved/DaedalusDesktopGames/minesweeper.dgs` slot. Normal Close and starting another
board do not write that slot. A failed Save & Close stays open for recovery. The slot
is shared between Minesweeper cabinets on one installation; it is not an account or
cloud save. Star's `star_shooter.dgs`, `DGS1` format and leaderboard remain separate.
Keyboard F5 saves and F9 loads. While paused, gamepad X saves and Y loads; the
pause overlay names these actions. Active-play reveal/chord mappings stay unchanged.

## DGM1

The whitespace-separated record is:

```text
DGM1 seed option cursorX cursorY activeTicks planted lost won cellBits
```

`option` is 0 Beginner (9x9, 10 mines), 1 Intermediate (16x16, 40 mines), or 2 Expert
(30x16, 99 mines). `seed` is the original unsigned 32-bit seed, including zero.
`activeTicks` is a saturating unsigned 64-bit count of active 1/60-second steps.
Boolean fields are 0 or 1. `cellBits` is exactly one ASCII digit per cell, in row
order: bit 0 mine, bit 1 revealed, bit 2 flag. Adjacent counts are recomputed from
mines. Movement-repeat, held inputs and wall time are deliberately not restored.

Parsing is bounded to 4 KB and refuses signed/overflowing numbers, unknown versions,
extra tokens, invalid dimensions/coordinates, open flags, incorrect mine counts and
inconsistent terminal or unplanted states. All validation occurs on a separate board.
Before planting, the original seed reconstructs the untouched random stream; after
planting, the saved mine layout is authoritative. The driver adopts that saved seed
so Restart and later difficulty changes retain their established deterministic behavior.

## Focused verification

`minesweeper_test.cpp` runs 213 checks using real input transitions and resumed
boards: all three difficulties at seeds 0, 730 and UINT32_MAX; flags/cursor/timer;
first-reveal safety; completion and loss; rendered adjacency/result parity; malformed
save preservation; timer saturation; driver pause/input cleanup and seed adoption;
and compatibility with Star's existing save path through the driver.

Build only `desktop_minesweeper` in this directory's existing CMake project, then
run `ctest --test-dir <build-dir> -R ^desktop_minesweeper$ --output-on-failure`.
Alternatively compile only `minesweeper_test.cpp` as C++17 with the plugin Public
directory on the include path. Strict MSVC `/W4 /WX /permissive-` passed locally.
A separate tiny probe against baseline `b684100d8` failed as expected because its
Minesweeper `SaveState` was empty and `RestoreState` unavailable. No source fixtures,
game saves, services, editor sessions, UHT or engine builds were used.

Native acceptance still needs: Save/Continue after application restart; missing,
corrupt and unwritable slot behavior; Save & Close failure staying open; gamepad and
focus cleanup; independent Star files; Slate layout; UHT/link/packaging. The current
editor owner must schedule that work after the reserved ingestion window.

## Selected-cell guidance

The core derives readable row/column, covered/flagged/open state and adjacent flag
counts from visible board state. Context explains the safe first opening, unflagging
before reveal, open-cell flag refusal and the matching-count chord requirement.
Matching flags are explicitly not proof of safety. Guidance is not saved and adds
no new state: DGM1 fields, mine placement, actions and active time remain unchanged.

`desktop_minesweeper_guidance` / `minesweeper_guidance_test.cpp` passed 29/29 strict
single-TU MSVC checks, using real seed-730 actions, idle-clone comparisons for blocked
actions, successful and wrong-flag chords, and reset/restore/presentation save-byte
preservation. The same test against the prior header passed12/29 and failed17
missing-guidance checks as expected. Native footer layout and physical controls
remain acceptance work; no engine build or live session was run.

## Controller result replay

A fresh terminal pad A uses the existing source-controller event to reset with the
board's persisted seed and current difficulty. Start remains unconsumed for the
host pause/save controls, including saving a completed board. Held Step actions,
active raw events and Enter/Space do not replace a board. No save-file/schema or
host changes are involved. The existing native host forwards A into a new Jump
edge, so it can also reveal the fresh board's safe first cell; no suppression state
is added. This behavior is modeled offline and remains native acceptance work.

`desktop_minesweeper_replay` / `minesweeper_replay_test.cpp` passed37/37 strict
single-TU MSVC checks: real win/loss/expert loss, reset and deterministic planting,
repeat cleanup, restored seed/difficulty, paused refusal, stale-edge cleanup and
modeled A forwarding. The same test against the preceding header passed12/19,
failing7 missing-replay/guidance checks as expected; post-replay assertions skip
when the old core correctly cannot proceed. Original DGM1 snapshots stay restorable.
