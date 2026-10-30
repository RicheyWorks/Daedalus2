# Repository guidance

## UX, DX and AX

Assess these together when making design and implementation decisions:

- UX: player clarity, accessibility and a usable experience.
- DX: maintainable code that is easy to understand and debug.
- AX: discoverable, predictable tools, schemas and workflows with useful errors
  and resumable operations.

Prefer improvements across all three, native or existing capabilities, and
minimal reversible changes. Preserve working behavior and data; disclose
unavoidable tradeoffs. Use focused checks appropriate to changed logic and
actual production blockers.

## Craft: beautiful code is part of done

Verified is the floor, not the finish. Before a PR is opened, and again before it
is merged, read the diff as a reviewer who did not write it and make it beautiful:

- One idea per line. Split packed statements; name a value the moment it is used
  twice or means something (`AltarSlots`, not `3`; `SourceKey::Space`, not `7`).
- Pull repeated shapes into a shared helper with its own test instead of a
  third hand-rolled copy (for Unreal cabinets: `DaedalusDesktopSaveText.h` for
  save text, `EdgeLatch` for held buttons, `SourceKey` / `PadButton` for input).
- A function does what its name says and nothing else; a comment explains why,
  never what the code already says. Delete dead code, stale comments and
  no-op branches on sight.
- Keep the file's existing convention (indent, brace and naming style) rather
  than introducing a second one; the native cores are tab/Allman, the desktop
  cabinets are four-space K&R, both PascalCase.
- The cleanup is its own commit or PR with no behavior change, and the existing
  tests and parity fixtures are the proof that nothing moved. Throughput never
  excuses leaving the beauty pass for later: schedule it before the next feature.

## UI design

Prioritize clear hierarchy, layout and meaningful primary labels. Remove
redundant taglines, helper text and secondary labels; if explanatory copy is
compensating for a confusing screen, fix its layout and grouping first.
Retain essential interaction cues, accessibility information, error and recovery
messages, and kid-friendly guidance.


## Unreal native workflow first

Find and read the installed Epic tool/schema instructions, then use the native
workflow for the requested operation. Custom queues and full-corpus inventories
are specialized helpers, not universal prerequisites for ordinary native imports.
Only add custom implementation for a demonstrated gap. Keep exact source/target
checks, fresh destinations, originals and saved work, sole-writer/resource limits,
and genuine validation. Do not bypass a real denial or weaken mandatory safeguards.

Native success alone does not prove task requirements: retain actual geometry,
material/colour and save outcomes needed for the content. Use Unreal's explicit
native pipeline options when a convenience tool omits an essential setting; do
not replace native ingestion with another framework. Reconcile partial/uncertain
effects before retrying and correct only owned assets with recoverable evidence.

## Integration stages and native custody

Claim exact file paths with the current coordinator and use an isolated worktree.
Preserve existing checkouts, uncommitted work and other teams' claims. The shared
BOARD plan and workflow guide retain their own writers; repository documentation
does not authorize changing those live coordination files.

Report saved, committed, pushed, PR/checks, merged and native acceptance as separate
stages, with exact source/merge identities and applicable evidence. A merge or
portable test does not establish installed-plugin parity, native class loading,
gameplay, file I/O or saved/reopened behavior. Check the current source-to-native
delta and per-feature acceptance before claiming a batch complete. Reuse the
[realm dependency reconciliation](docs/realms/REALM-DEPENDENCIES-20261026.md)
rather than replaying every transfer-bundle ancestor.

Native builds, editor actions and shared resource jobs belong to the currently
verified sole custodian. Historical owner names, stale process IDs, empty locks and lease
expiry do not grant custody. Coordinate compatible source changes into the owner's
batched rebuild and preserve any active hold; source work does not resume ingestion.
Historical recovery advice does not authorize force-closing an editor or discarding
unsaved state. The verified custodian must reconcile saves, pending operations and
ownership before an editor transition.

At an operational checkpoint, stop the owned producer and its lease renewals,
preserve warnings/failed attempts/partial effects, normally release only owned
leases and verify the next owner's handoff. Record process exit separately from
the named failed or uncertain operation. Do not force-release a foreign lease,
edit lock files or discard failure evidence to manufacture completion.
