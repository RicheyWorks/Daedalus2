# Owned-window minimize checkpoint

Initial hidden launch settings do not cover a secondary Slate window that appears
later. This helper provides a bounded checkpoint for the existing native owner:
minimize approved visible windows belonging to its exact editor process and
verify `IsIconic` before reporting readiness. Importing the helper is inert;
Win32 dependencies load only when an approved live caller constructs its adapter.
This package does not change or invoke the active native lifecycle.

The helper is an unchanged copy of the reviewed R2 candidate. The 22 focused
tests are unchanged except for two fixture paths. They inject fake adapters and
fake user32 metadata, never construct `Win32Adapter`, and never load ctypes,
touch a window, launch an editor, or contact an engine/service.

## Caller contract

```python
from owned_window_minimize import minimize_owned

# Existing authorized owner supplies its adapter and fresh process metadata.
checkpoint = minimize_owned(
    adapter, expected_pid, expected_start_utc, exact_main_window_title,
    identity=current_owned_process_identity,
)
```

`identity()` returns the owner's existing `pid` and `start_utc` observation. The
start token preserves all seven FILETIME fractional digits and accepts UTC
spellings only. The exact title must end in ` - Unreal Editor`; the only allowed
visible titles are that exact main title and `Message Log`, both `UnrealWindow`
windows in the owned process. The adapter supplies `snapshot(pid)`,
`window(hwnd, expected_pid=pid)` and `minimize(hwnd)`.

The checkpoint uses `SW_SHOWMINNOACTIVE` (7), polls `IsIconic` within bounded
limits, leaves hidden/already-minimized windows alone, and never closes, restores,
activates, focuses, clears logs, or minimizes all applications. Unknown visible
windows, disabled windows/owners, possible modal dialogs, stale process identity,
reused handles, failed requests, and failed postconditions raise `WindowHold`.
Callers must preserve HOLD as a readiness failure.

R2 also follows visible foreign windows' `GW_OWNER` chains using only
HWND/PID/thread/visibility/owner metadata. Reaching the target process or one of
its recorded window handles causes HOLD before minimization. It never reads
foreign title/class metadata. Cycles, depth beyond16, disappearing/reused links,
or owner reassociation fail closed. It repeats the whole-inventory preflight
before acting and checks expected PID before owned title/class reads.

These separate metadata queries and the eventual action are not an atomic OS
transaction. Revalidation narrows races and cannot eliminate them. This is a
caller-driven checkpoint, not a watcher or a general-purpose window manager.
Native adoption and any live validation remain with the existing native owner.

## Offline fixtures and source pins

| File/source | SHA-256 |
| --- | --- |
| Packaged R2 `owned_window_minimize.py` | `5744bbeeb3e164fc467c63ca15591f1094e796127c8b488cd2e8ee2e0911f7b0` |
| Original R2 `owned_window_minimize_test.py` | `55a468ad4e33ba7cbf583817861ca7aefd2bbd36150d22b5b110cebac1343ce6` |
| Packaged `test_owned_window_minimize.py`, two fixture paths changed | `c8ee911f7312ee64d4ab2db6442d87fded5426ebf5e23f2fad0f7b910dfabed1` |
| Frozen R1 `fixtures/owned_window_minimize_r1.py` | `8efe440e2f6e5feb264b2e7d17c890956438234996bffcdcf6fc0fcf6963dfc0` |
| Original unchanged lifecycle, not distributed | `1d77f6921f4a4190fb402d559abc095d079e072b3389719780b0f1b2bd95f821` |
| `fixtures/official_mcp_blueprint_lifecycle_check.py.txt`, repository LF endings | `cd011da0709fb50781dbd9f8a7a287ebe45f9ca285a50d102b3e199057fa3670` |

The frozen R1 helper is a negative oracle: its actual snapshot implementation
missed a visible foreign window owned by the target. The R2 tests demonstrate
that difference using fake metadata. The lifecycle fixture contains only the
unchanged `check()` function from original lines131-152, with CRLF normalized to
the repository's LF policy (raw excerpt SHA-256
`a3b101aedfc3f2d7e9780b2e1b327f59149d8dfdf0a98b664815000acd9ec620`). The integration test
extracts that AST and injects every dependency, verifying HOLD cannot report
ready or release. No complete machine-specific lifecycle executable is included.

Run only the focused suite from the repository root with existing Python3.10+:

```text
python -I -S -B tools/unreal_mcp/test_owned_window_minimize.py
```

## Evidence boundary

The retained R1 live checkpoint historically reported both the main editor window
and Message Log as `IsIconic=true`, with foreground unchanged. That earlier
terminal receipt has SHA-256
`22e1cccbbad4e06a5714f183d413370940ae9bed48a22ab13a00995a7cd11040`.
It predates the R2 foreign-owner-chain correction. It is historical R1 evidence,
not R2 live acceptance. Raw machine state and screenshots are not included here.

R2 validation for this package is **mocked/offline only**. No active lifecycle,
native branch, editor, UI, service, credentials, or transport has been changed.
The packaged focused command passed all22 tests in0.011seconds, exit0, using
existing Python3.10 with `-I -S -B`; it made no Win32 or engine calls.
