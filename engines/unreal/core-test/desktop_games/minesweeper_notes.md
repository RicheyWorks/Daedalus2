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

`minesweeper_test.cpp` runs 214 checks using real input transitions and resumed
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

## Native mouse play

Left press reveals, right press toggles a flag and middle press chords. The canvas
inverts the same native scale/letterbox transform used to paint; core hit testing
shares the rendered board geometry. Top/left bounds and the narrow cell gutters
are included; right/bottom bounds, letterboxing and nonfinite coordinates are
excluded. The selected cell follows a valid press. Existing first-reveal, flag,
flood, chord and win/loss rules are shared with keyboard/gamepad input.

The optional `Game::SourcePointerButton`/Driver hook consumes one press without a
fixed step. Paused, terminal and save-pending play is fenced. Accepted presses clear
prior semantic/held input through the existing presentation helper. Double-clicks
dispatch their physical second press once through Slate's double-click override;
there is no automatic retry or pause exit. Other games keep the default refusal.
Actor changes are limited to a pointer-input declaration and forwarding method;
save paths and file operations are unchanged.

Two immediate presses can safely plant and then lose at `activeTicks == 0`.
`DGM1` now accepts this valid later-loss state. It still requires safe cells already
open, exactly one open mine, the correct mine count and consistent terminal bits.
Impossible first-reveal losses and malformed records remain atomically refused;
no format/version change or artificial timer advancement is introduced.

`desktop_minesweeper_pointer` / `minesweeper_pointer_test.cpp` passed 197/197 strict
single-TU MSVC checks, using actual rendered cell centers across all presets and
three seeds, bounds/gutters, flagging, safe openings, successful/wrong-flag chords,
complete wins, zero-tick loss restoration, paused/terminal refusal and stale-input
cleanup across catch-up steps. The save/resume suite passed 214/214 after its
zero-tick assertion was updated and impossible-first-loss refusal retained.
Private controlled variants prove the new regressions: disabling the pointer
hook passed 51/156 (105 failures; planting-dependent checks skip), and restoring
the old zero-tick loss rejection passed 178/197 (19 failures). Both exited 1;
the repository sources were never reverted. Build/run only the named CMake target,
or compile the single test as C++17 against the plugin Public directory.

Two targeted source reviews found no blockers. Installed UE5.8 source confirms
double-click routing has no unhandled fallback to a second mouse-down dispatch.
This is source/API evidence, not native acceptance: UHT/compilation, DPI/viewport
hit alignment, mouse buttons/double-click timing, focus and mixed controller input,
paused/result clicks and actual save/continue still require runtime checks. No
engine/editor or full suite was run for this slice.

## Readable beginner guide

The cabinet's existing native help panel now serves Minesweeper as well as Star.
How to play / F1 / left-stick click pauses the current board and opens readable,
wrapped, scrollable rules: reveal every safe cell, first-opening safety, diagonal
number clues, flood/flag interaction, an estimated mine counter, optional chording
and its risks, physical controls, exact save/continue and explicit result replay.
No board action is required to dismiss the guide. Resume is explicit and fenced
against terminal/pending-save states; Return paused and exit keys preserve pause.
The panel captures the opening game ID and refuses to resume another active game.
Underlying cabinet controls and mouse canvas stay disabled while help is open.
This is native presentation only: no core, actor, timer, save operation or format
changes. Source review is separate from pending layout/scroll/focus/input and
save/replay runtime acceptance; no portable rule suite was repeated for UI copy.

## Fresh puzzles and replay

The native New puzzle button requests an unrevealed puzzle at the current size.
It uses Unreal's existing FGuid seed source and the Driver's existing Restart
lifecycle. The portable Mines-only transition bounds the candidate to a native
nonnegative int32 seed and avoids the active RNG stream, including the existing
zero-seed alias. Extracting Random::InitialState keeps that old mapping unchanged.
No RNG algorithm, board rules or DGM1 fields change. No save-file write occurs.

Ordinary Restart and terminal replay retain the active seed and size. Planting
also depends on the first revealed cell, so a matching layout requires the same
opening cell. Continue remains authoritative for the exact older saved board and
adopts its seed for subsequent replay. The new action clears old input and time
debt, and never forwards its activation into a first reveal. Other games refuse it.

The focused C++17 target is desktop_minesweeper_new_puzzle, or compile only
minesweeper_new_puzzle_test.cpp against the plugin Public directory. Native seed
generation, reflected API compilation, button layout/focus, mixed input and actual
save-slot preservation remain native acceptance work. The portable suite tests
real Driver, rendered targets, board rules and save/resume without engine headers.

Strict single-TU MSVC /W4 /WX /permissive- passed 857/857 checks across 75 seed/
size combinations, queued input/time debt, actual win/loss and other-game refusal.
A private old-Restart variant passed 767/857 (90 expected failures); removing only
the same-stream collision guard passed 836/857 (21 expected failures). Both
controlled variants exited 1, with repository sources unchanged. No earlier suite,
Unreal/UHT build, editor or service was run for this feature.
