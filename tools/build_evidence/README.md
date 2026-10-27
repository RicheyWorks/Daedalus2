# Offline build evidence capture

This explicit-command wrapper retains observations around one newly launched
foreground command. It produces the existing `daedalus.build-inputs.v1` and
`daedalus.build-provenance.v1` receipts for offline handoff sealing. It does not
start an Unreal build, select a build command, activate hooks, inspect running
applications, acquire custody or change historical receipts.

Python 3.10+ and the standard library suffice. Run from the repository root:

```sh
python -B -m tools.build_evidence capture --request /path/request.json --workspace /path/synthetic-workspace --output /path/fresh-capture
python -B -m tools.build_evidence inspect --output /path/fresh-capture
python -B -m unittest tools.build_evidence.test_capture -v
```

The workspace must already exist. The output's parent must exist, its destination
must be absent, and workspace/output must be disjoint. No retry reuses a failed
or interrupted capture. Preserve that directory and reconcile the observed
effects before any separately authorized new invocation.

A synthetic request looks like this (replace the executable with its real path):

```json
{
  "schema": "daedalus.build-capture-request.v1",
  "source_commit": "1111111111111111111111111111111111111111",
  "toolchain": {"engine": "synthetic fixture", "compiler": "Python fixture"},
  "command": ["/absolute/path/to/python", "-B", "-c", "from pathlib import Path; Path('result.bin').write_bytes(b'fixture')"],
  "inputs": [{"path": "Source", "kind": "directory", "category": "source"}],
  "artifact": "result.bin",
  "timeout_seconds": 5,
  "notes": {"external_dependency_inventory": null, "purpose": "synthetic example"}
}
```

`command` is an argv array passed with `shell=False`, with inherited environment
and workspace as the working directory. This is **not a sandbox**: only supply
an already authorized, trusted command. The wrapper neither restricts its file
writes nor establishes executable/environment identity. Logs and argv can contain
sensitive data; keep captures private and inspect them before sharing. No upload,
network fetch, environment change or provider operation is built in.

Every declared directory is recursively inventoried, including empty directories;
file roots cover only the named files. Files added outside declared roots are
outside coverage. Categories are `source`, `header`, `descriptor`, `config` and
`generated`. Roots cannot overlap or differ only by case. Paths use the existing
handoff portable-path rules; traversal, reserved names, links/reparse points,
hard-linked files and artifact/input overlap are refused.

Before launch, exact input bytes are copied under `inputs/`, a canonical source
manifest is retained, and the artifact must be absent. After the actual child
exits, the wrapper rechecks membership, hashes, size and endpoint metadata and
copies any observable artifact. Any input change, incomplete observation,
nonzero exit, timeout, interruption, missing artifact or output overflow prevents
success publication. A preexisting artifact is preserved and stops launch even
if the command might have replaced it.

The capture records real UTC observations, raw request bytes/hash, exact argv/hash,
raw combined stdout/stderr, actual direct-child outcome, before/after inventories
and artifact pins. `notes` is preserved as opaque JSON, including unknown/null
fields. Unknown top-level contract fields are refused. Callers cannot supply an
exit code, success flag or build-time timestamp.

```text
fresh-capture/
  request.json                 original request bytes
  capture.json                 incomplete, failed or captured observations
  inputs-before.json           canonical existing source-manifest format
  inputs-after.json            observed endpoint inventory, when available
  identities-{before,after}.json
  inputs/...                   frozen before-command input copies
  command.log                  bounded raw combined output
  artifact.bin                 retained after-command artifact, when available
  receipts/                    complete bundle published last on success only
    source.json                exact canonical input manifest
    build.json                 strict existing provenance contract
    success.json               pins all required capture and receipt files
```

`inspect` requires the final bundle and verifies all pinned bytes, frozen source
membership, observed success and existing consumer binding. It reads no original
workspace, does not refresh timestamps and never executes the command. Missing,
partial or corrupt captures fail inspection. Interrupted publication can leave
unadvertised `.receipts-*` staging directories and partial observations; these
are evidence, not success. Files use exclusive creation and flush/fsync; the
complete bundle is renamed last within the fresh owned directory. This is a
cooperative single-writer protocol, not protection against a hostile writer or
a whole-machine power-loss guarantee. Do not bypass inspection by consuming a
staging receipt.

Limits are fixed: 64 KiB request, JSON depth 64, 64 roots, 1,024 files, 2,048 inventoried entries,
depth 16, 8 MiB per input, 32 MiB total input, 16 MiB artifact, 1 MiB retained log,
64 argv items/16,384 total characters, and 1–60 seconds requested child timeout.
Reads use 64 KiB chunks. Termination/reaping and pipe drain use bounded waits of
at most two further seconds each. Only the observed direct child is killed;
descendants are never discovered or terminated. An inherited pipe still open
after the bounded drain is an incomplete observation, never success. These
limits do not cap the trusted command's CPU, memory, disk writes or descendants,
and file I/O is not a hard real-time guarantee. Tests use serial disposable
fixtures only; no native integration is exercised.

Path and handle metadata are each checked for stability using their own before
and after observations, including `ctime_ns`. Cross-API identity compares device,
inode, size, mtime, mode and link count; Windows Python 3.12 can expose different
ctime meanings through those two APIs. Content hashes and both stability checks
remain required.

Equal endpoint content/metadata does not prove continuous immutability during
execution. Declared coverage does not discover compiler dependencies. Commit and
toolchain labels remain declarations; external dependencies, environment,
descendant completion and source/editor/runtime parity remain unknown. An artifact
absent before and present after is observed between those checks; its causal
producer and exact creation time remain unknown.

`recorded_at_build_time=true` is emitted only by this wrapper after its own newly
observed successful invocation, with unchanged declared inputs and the exact
retained artifact hash. It is not inferred from current files. Existing handoff
validation checks these producer assertions, not their authenticity. The strict
receipt cannot hold additional metadata, so limitations and observed timestamps
remain separately pinned in `capture.json`. Native adoption during a later
authorized build requires the responsible owner's dependency/command review and
normal runtime acceptance. No historical false flag is rewritten.

To consume a successful capture, first inspect it, then reference
`receipts/source.json` and `receipts/build.json` in a separately constructed
checkpoint's source/build evidence roles. Bind source commit/manifest hash and
build receipt/artifact hashes exactly, then use the existing
`tools.team_handoff.packet.seal` and `read_packet` on a fresh disjoint store.
This wrapper creates no checkpoint, campaign/runtime assertion or takeover plan.
The compatibility test constructs only an explicitly synthetic checkpoint.

CLI exits: `0` for a complete capture or successful inspection, `3` for a retained
failed capture, `2` for invalid requests, existing destinations or integrity/I/O
errors. A hard wrapper termination may leave `status=incomplete`; that state is
never automatically resumed. A storage failure may prevent the final failure
record itself from being written; all already-created files remain intact.

CI runs serial synthetic tests on Linux/Python 3.10 and Windows/Python 3.12,
validates the request and compatible receipt schemas, and applies the existing
pinned Ruff error/Pyflakes policy only to this namespace. Existing handoff,
snapshot, journal, package and quality workflows remain unchanged.
