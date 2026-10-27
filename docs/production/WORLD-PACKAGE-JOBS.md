# Frozen World Package jobs

`python -m tools.world_package.job_cli create REQUEST --output FRESH_JOB` copies
the explicit batch selection into a new local job directory. Relative package
paths bind to the request file's directory. The library interface is
`create_job(explicit_batch_request, fresh_output, explicit_base_directory)`.
Existing and partial output directories are refused without cleanup or overwrite.

Each whole ZIP is streamed into its own fixed `packages/0000.zip`-style file,
including exact-byte aliases. Only these copies pass through the existing batch
validator. Original request values, base directory and actual accepted receipts
are retained in `provenance.json`; `request.json` uses fixed job-relative package
references. `plan.json` preserves all raw identities, destinations, replay and
conflict rules, changing only item input-path references to job-relative paths.
This stores accepted receipt values; it does not create native acceptance evidence.

`job.json` is the publication marker. All pinned files are exclusively written,
flushed, synced and closed before its fully written candidate `job.pending.json`
is atomically linked into that final name without replacement. Both control
names remain. Local filesystems must support hardlinks; failures have no rename
or overwrite fallback. An interrupted prepublication leaves partial evidence and
no complete job. A failure after the publication point may have an uncertain
outcome: inspect the named job before taking further action, and never reuse it.

`python -m tools.world_package.job_cli inspect JOB` verifies exact bounded file
inventory, plain files/directories, byte pins, selection/receipt binding and a
fresh batch plan against the frozen ZIPs. It never opens original package paths,
extracts assets or changes the process directory. Moving the complete job or
changing/removing originals leaves its inspected plan unchanged.

Limits retain the batch's 16 inputs, 64 MiB per ZIP and 256 MiB conservative
source-read budget, with 64 KiB copy/hash chunks. Controls are limited to 1 MiB
request, 2 MiB provenance, 8 MiB plan and 64 KiB per manifest. Pinned data must be
regular single-link files; symlinks/reparse points, extra/missing entries and
escaping paths refuse. Input/output parent directories remain caller-trusted.
Hashes prove point-in-time retained-byte consistency, not authentication or
permanent filesystem protection against competing writers. A copy of a changing
original is validated as the copied byte sequence; no atomic original snapshot
is claimed. No native import, execution, lease or live-world command exists.
