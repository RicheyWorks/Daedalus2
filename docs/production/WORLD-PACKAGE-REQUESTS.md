# Form an explicit World Package batch request

`python -m tools.world_package.batch_request north.zip south.zip` prints a v1
batch request to stdout. Select package paths explicitly; this command does not
open packages, search directories, expand globs, extract archives or run imports.
Feed the resulting request to `python -m tools.world_package.batch_cli request.json`
for actual bounded validation and planning.

Repeat `--prior-receipt accepted.json` to load explicit accepted v1 receipt files.
Each receipt is limited to 64 KiB, decoded as strict JSON and validated with the
existing receipt contract. Duplicate receipts for one raw world ID refuse, as do
saved single/batch plans. No missing or invalid receipt falls back to inferred
acceptance. Only owner-supplied accepted evidence can yield a later `no_op`.

Relative package and receipt paths bind to `--base-directory`, or the current
working directory when omitted. Output package paths are absolute and normalized
without following links, so moving the saved request cannot redirect them.
Generated keys are full SHA-256 bindings of those normalized path strings;
packages are sorted by path and receipts by raw world ID. Reordering the same
selection produces the same JSON. Selecting an identical normalized package
path twice refuses; different paths are validated/deduplicated by the planner.

The command accepts at most 16 package paths and 16 receipt files, with the same
1 MiB request limit and local-path guards as the batch contract. URL, UNC/device
and drive-relative forms refuse before path normalization/open. Paths are explicit
local selections; filesystem links and parent directories remain caller-trusted.
The command only writes stdout/stderr. Saving or redirecting stdout is the caller's
choice; the ready-plan export command separately provides exclusive file creation.
Request creation does not prove that any package exists or is valid, and never
establishes native acceptance.
