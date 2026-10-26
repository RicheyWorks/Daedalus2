# PC job snapshots

Claude's harness request #4 (hub 29886; `docs/AUTOMATION-LESSONS.md`, 02:25)
asks for the last N log lines and state without a blocking device-bridge wait.
`job_status.py` reads the existing `pc-job.ps1` artifacts once and prints one JSON
line. Pass the exact ID returned by the launcher:

```powershell
python tools/pc/job_status.py --id job-1014-024500 --lines 40
```

The default directory is `%LOCALAPPDATA%/Daedalus/jobs`. Use `--jobs-dir PATH`
for a synthetic fixture or an explicitly chosen artifact directory. The reader
does not create directories, select the latest job, or touch the launcher. It
does not wait, launch, stop, or retry anything.

| JSON state | Evidence | Meaning |
| --- | --- | --- |
| `completed` | Valid `.exit` containing `done <code>` | The producer recorded a terminal exit code. `exit_code` preserves zero, nonzero and Windows 32-bit codes. |
| `incomplete` | `.started` containing `pid=<PID>`, or `.log` without an exit marker | Artifacts exist, but no terminal record was found. A launch receipt does not prove the process is alive. |
| `unknown` | Missing, malformed or unreadable state evidence | The reader cannot establish the recorded state. `errors` explains the gap; never restart based on this alone. |

`schema` is `pc-job-status/v1`. `evidence` names the source, `terminal` means a
validated exit marker was found, and `process_verified` is always false. The
reader verifies neither process liveness nor the job's acceptance checks. In
particular, the legacy launcher on main has a known early `%ERRORLEVEL%`
expansion bug; the existing PR89 launcher fix owns that issue. Reading its
`done 0` cannot strengthen that record into proof of success. This change leaves
that launcher and its pending fixes untouched.

`tail` contains at most 200 lines from at most the last 128 KiB of the log
(plus one inspected boundary byte).
`--lines` defaults to 40. If the byte window starts within a line, that leading
fragment is dropped. `tail_truncated` reports either byte or line truncation.
UTF-8 log decoding replaces invalid bytes; an in-flight trailing line may be
partial. Markers are limited to 256 bytes (plus one overflow-check byte) and accept UTF-8, UTF-8 BOM or
UTF-16 BOM. Markers must end in LF (including CRLF); an unfinished digit prefix
cannot count as a terminal record. Nonregular artifacts are rejected before
reading. Temporary `.exit.tmp` records are ignored. Files can change between
reads; this is a bounded observation, not an atomic snapshot of a live producer.

The command exits 0 for a coherent observation, including a recorded nonzero
job code; 1 if `errors` is nonempty; and 2 for invalid arguments. The recorded
job code is a JSON field, not the observer's exit status. No missing value is
converted to zero. No process table, socket, Unreal endpoint, UI or security
log is queried.

Run the portable synthetic regressions without an editor:

```powershell
python -m unittest tools.pc.test_job_status -v
```

Source-only delivery: Claude accepted this scope in hub 29938. Device-bridge
usage and live job acceptance remain the current owner's follow-up; no
installation, shared checkout update, editor call or configuration change is
part of this patch. The play-guard lease/warning request remains separate work
in `studio-screen-connector/playguard.ps1` and its integration seam.
