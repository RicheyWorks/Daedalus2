# Willow stage runner r2 — source successor, not installed

Owner: Team Codex. Isolated branch `codex/willow-stage-r2`, base
`0beff67b25569b3b2b330a43667d68aca9f48c50`. This five-file successor addresses
two actual r1 failures without changing any frozen r1 source, thirteen pins,
attempts, images or GLBs. It is not another dispatcher or general harness.

## Changes and retained policy

`stage-runner.ps1` retains the existing explicit per-stage grant, UTC start/expiry,
manifest/pin, output-absence, competing-process, native-custody, exclusive compute
lease/readback, hidden process and bounded terminal/release policy. The caller now
passes the existing accepted `-ManifestPath` explicitly. New attempts go BELOW
the same pilot root at `stage-plan-r2/attempts/<grant>/`; r1 attempts stay intact.
Export/reopen remain one CPU; the frozen views producer still requires two.
No source adoption grants a real job or retries the blocked reopen.

`StagePolicy.psm1` writes fresh `prelaunch-memory.json` BEFORE deciding whether
to launch. It retains UTC, KiB readings, physical1700000/virtual2200000 floors,
grant/stage, outcome/reason, query error, launched=false and pid=null. A rejected
or unavailable reading throws only AFTER publication; a failed publication also
blocks launch. Exact floors are accepted, lower values rejected; there is no
floor parameter/override. Existing terminal, failure, uncertainty and release
receipts now use the same exclusive atomic publication (flushed sibling temporary
file, no-overwrite move). Existing results are never replaced.

The validator normalizes only slash direction before EXACT CASE-SENSITIVE role/
view allowlist comparison; it does not resolve away traversal or trim segments.
Rooted/drive/UNC/ADS/control, empty/dot/dot-dot and unsupported segments reject.
Filesystem root containment, reparse-point rejection, file existence, SHA256,
dimensions/settings, source binding and existing GLB checks remain. A separator
match is not permission to weaken file/hash guards or relabel visual acceptance.

An actual terminal process releases via normal unlock and lock-table readback;
an unlaunched failure also releases. An uncertain still-running process retains
its lease, emits uncertainty and requires owner reconciliation, never kill/replay.
The helpers perform no hub/process calls; production calls remain only in the
explicitly executed stage runner. No shared Poot, transport, native or source
asset files are edited by this package.

## Actual provenance and outcomes

R1 runner SHA256 `0866c7a15f20e454725498034d9a45f474b28f9edff9a1094be6edf389a5465c`
and validator `38bc9c28eafadf84768fc4bb00e2cb623ef6e182fab825d912df582cc5603d87`
were read/copied as the starting point; no external upstream code was imported.
Original Willow views PID59724 exited0 but post-validation failed on Windows
backslashes. ROOT's separately retained reconciliation receipt
`a7f6023888a280354d83d6d73454345a385e902b9bfcf999bfe5281a6b38bcdf`
already verified those retained images without rerendering. R2 is a future source
fix, not replacement evidence for that attempt. The three inspected images still
FAIL visual quality and native admission remains HELD.

R1 reopen2355 was blocked before any PID at a memory floor; exact numeric values
were absent. It released compute normally. R2 fills that diagnostic gap but has
NOT run a production preflight/reopen, exported/rendered or changed that history.

## Focused synthetic validation

Run `pwsh -NoProfile -File tools/blender/willow_stage_r2/tests.ps1` from this
worktree. The script uses unique retained temporary fixtures, no Pester/dependency,
and serial mocks for ALL hub/CIM/process/sleep boundaries. Header-only synthetic
PNG bytes are explicitly not renders. Full runner fixtures exercise memory
rejection with no process, completed exit+validation+release, failed exit+release,
and uncertain live-process lease retention. No production HTTP, OS query,
Blender/native process or actual lease is used by these tests.

Initial focused result: **40 checks PASS**. After the independent review fixes
below, the final focused result is **75 checks PASS**. Final test sandbox:
`C:/Users/730ri/AppData/Local/Temp/willow-r2-tests-916ce58f9f7240f598b45b0eeb252ca7`.
Earlier sandboxed filesystem Move restrictions prevented atomic evidence writes;
the authorized focused run outside that restriction succeeded. Test-only mock
scope/parameter/interpolation defects were corrected before the passing result.
These results establish only the synthetic contracts, not real runtime support,
full PNG decoding, mesh collision, current memory or native quality. Independent
source review remains a separate gate before adoption/merge. The authorized
draft source may be published to permit remote review when local reviewer routes
are unavailable; publication is not independent acceptance.

## Existing-owner adoption, later

The normal owner reviews/pins these five files and retains the existing accepted
r1 manifest SHA for its unchanged inputs. Any successor source pin must be stated
in its new stage grant; the legacy manifest does not implicitly authenticate r2.
Example shape of a FUTURE command, not an allocation:

```powershell
& ./tools/blender/willow_stage_r2/stage-runner.ps1 `
  -Stage reopen -ManifestPath $existingAcceptedManifest `
  -ManifestSha256 $acceptedManifestSha -GrantId $freshGrant `
  -StartByUtc $explicitUtcStartBy -ExpiresUtc $explicitUtcExpiry -Execute
```

Never invoke against an already completed/partial stage or a consumed grant. A
new job requires current exact allocation, fresh floors and exclusive queue/
custody checks. Changed accepted source requires a new reviewed version, never
editing frozen artifact input pins to make a stale manifest pass. R2 does not
install a source, override visual holds, submit native intake, or alter original
source/GLB/attempt bytes. Sole Unreal operator remains codex-play-guard.

Lesson: keep the failed outcome immutable, make rejection evidence as durable as
success evidence, and normalize portable serialization without relaxing identity.

## Independent PR167 review corrections

Review5542885212 at published83786a49 identified three P2 source-boundary gaps.
This follow-up preserves the same five-file scope and all original r1 evidence:

- WILLOW-R2-01: the runner checks consumed GrantId paths in BOTH r1 and r2
  before any HTTP, lease, attempt write or launch. Synthetic retained attempts
  reject with zero mocked HTTP/process calls and unchanged original bytes.
- WILLOW-R2-02: lifecycle phase and known PID/start/argv/grant/executable survive
  a failure publishing started.json after launch. Durable failure evidence is
  attempted; if that publication also fails, WILLOW_FAILURE_FALLBACK emits the
  same context plus the publication error to the console warning stream. No
  terminal acceptance, kill, retry or lease release follows an uncertain launch.
  Tests cover prelaunch write failure (zero launches/normal release), started
  write failure, and simultaneous started/failure publication failure. The
  pre-existing evidence bytes are preserved in every case.
- WILLOW-R2-03: root, authored.json, selected stage receipt and expected retained
  reopen scene are resolved through the existing reparse policy BEFORE pilot
  content/hash reads. Synthetic metadata mocks reject each reparse case with
  zero authored/stage content reads; a normal reopen receipt still validates.

All75 serial checks passed with only synthetic files and mocked boundaries.
The metadata tests create no actual symlinks and call no native API. Parser-only
checks cover all four PowerShell source files. These results do not establish
real OS/process fault recovery, production adoption, current memory, editable
reopen or visual/native acceptance. The changed source requires independent
re-review; no prior review acceptance is silently transferred to this head.

## Optional real-junction module conformance (test/docs only)

Source-cleared implementation checkpoint is
`cac2d85bc7e6f129115c1361f6a9b7e7549a7786`. This addendum changes ONLY tests.ps1
and README.md; StagePolicy/module, runner and validator bytes remain respectively
`b29a626b4f4f44660004c7692b33809c96a5f33ee23b66b9120d16937a857eca`,
`53e0f1befdba118f417f3fb230dd88710d353a7f90ea6f4ed822638c030e88d2`,
`6c59d979dbfa411a8ef31fd22b97a17b73b2754623e893ad5515ab3e52f0d93f`.

Default invocation retains the original75 mocked checks. Optional invocation:

```powershell
pwsh -NoProfile -File tools/blender/willow_stage_r2/tests.ps1 -RealJunctionConformance
```

This separate module-only mode is placed after the default suite's mock cleanup;
it does not rerun the mocked runner suite or install its mocks. It calls the REAL
Resolve-WillowPath for a junction declared as root, a junction below an ordinary
root, and an ordinary-directory control. Its consumer read counter increments
ONLY after successful resolution. Junction rejection requires the exact intended
Reparse-point guard AND zero reads; an arbitrary exception is a FAIL.

Everything is inside one newly allocated Temp GUID directory. Creation uses only
normal New-Item -ItemType Junction. Denied/unsupported creation is a specific
SKIP, not a pass; no escalation, alternate API, settings change or retry workaround.
Target sentinel hashes and entry names are compared before/after; final source
also emits both snapshots. Link cleanup first validates exact owned location,
expected target, ReparsePoint and Junction kind, then uses only
[IO.Directory]::Delete(link,false). No recursive deletion occurs. Uncertain
cleanup is FAIL/incomplete with the fixture retained. Successful ordinary target
directories and sentinels are retained too. PARTIAL_SKIPPED returns a nonzero
status, never a conformance PASS.

Actual unprivileged run, 16 October2026 UTC / 15 OctoberPacific:

- PowerShell7.6.5, Microsoft Windows10.0.26300, sandboxed Temp directory
  `willow-r2-junction-e4a14bcd4efa4aaf86b14ebe69316e3a`.
- Declared-root junction: SKIP, New-Item returned 'Access is denied.', zero reads,
  no link created/cleanup needed, target sentinel/hash and entries preserved.
- Intermediate junction: same SKIP/denial/zero reads/target preservation, no link.
- Ordinary directory: PASS, exactly ONE consumer read, exact sentinel match,
  unchanged target hash/entries. Overall PARTIAL_SKIPPED; host returned nonzero.
- No privilege escalation or creation retry followed either denial. An earlier
  parser error was corrected before any fixture execution; it created no links.
  The subsequent snapshot-output-only addition was parsed, not rerun around the
  denial. Original75-check results are from the accepted checkpoint above; the
  optional mode does not claim those checks were newly executed.

This establishes the ordinary control only in this environment. Actual junction
rejection/unlink remains UNVERIFIED here because creation was denied. It is
module conformance, not new validator-wide ordering, above-root/race-resistance,
OS safety, production adoption or native evidence. Any real source defect found
by a future separately authorized run must be reported before expanding scope.

### Test-only creation-error classification correction

Independent review at c396a802 found that the creation catch labelled every
exception SKIP. This follow-up changes only tests/docs: the catch now retains
exception type, category, error ID, message, HRESULT and target context and
classifies narrowly recognized permission/capability errors as SKIP. Recognized
evidence is UnauthorizedAccessException (including wrapped causes), Win32 error
5/1314 for permission, Win32 error1/50/120 or PlatformNotSupportedException for
capability, or NotSupportedException WITH NotImplemented category. Unexpected
I/O/setup errors, or a permission-looking message/category without specific
exception evidence, FAIL. Unrelated fixture setup remains outside that catch.
Existing target snapshots and guarded nonrecursive cleanup are unchanged.

The prior real AccessDenied SKIPs and ordinary control result remain historical;
no real junction creation was retried or newly classified from absent metadata.
The post-run correction was validated only with:

```powershell
pwsh -NoProfile -File tools/blender/willow_stage_r2/tests.ps1 -JunctionClassificationOnly
```

Actual result: **9 pure synthetic classification cases PASS**, plus source parse
0 errors. Covers recognized permission/capability and wrapped permission, versus
unexpected I/O/setup and message/category-only failures. This mode returns before
module import, mocked runner suite, fixture creation or junction operations.
No filesystem fixture, production call, privilege escalation or settings change
occurred. The three implementation blobs remain the accepted cac2 bytes. Pure
classification success is not real junction conformance, cleanup or runtime proof.
