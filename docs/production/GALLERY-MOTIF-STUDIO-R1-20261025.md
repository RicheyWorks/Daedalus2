# Gallery Motif Studio — edition 1, 25 October 2026

## Purpose and boundaries

An original Gallery City creation tool: paint a small floor mosaic, explore
colour and symmetry, recover edits, preview earlier sketches and explicitly
keep independent local exports. This follows the realm's colour/light/art theme
in `REALM-CASTS.md` and the current creative campaign. It does not change
ADR-035's server-only maze PNGs, seed frames, parcel permissions or ART protocol.
No third-party images are loaded and no frame is hung or published.

Base: `a8a270cf424977c11fb254d319bdf99d159e1883`.
Branch: `codex/gallery-motif-studio-20261025-r1`.
Campaign deadline: **2026-10-26 06:56:50 UTC**.
Every prior checkpoint, original, export and branch remains preserved.

The `.dgm` format below is an explicitly new **local sketch artifact**, not a
canonical player save/profile, ownership proof, NFT, painting-supplies ledger,
reward, Gallery server import or inventory contract. Those integrations remain
separate. No original LivingPainting, Hero, dialogue, shared input, WorldActor,
build configuration, server, board or live project file is edited.

## Player creation loop

Explicitly place `ADaedalusGalleryMotifStudio` on existing flat ground in a
standalone world. The 8×8 floor canvas uses 60 cm cells and opaque colours:
Paper/erase, Ink, Coral, Gold, Emerald, Azure, Violet and Teal. Walk onto a square
and use the existing E/X interaction to paint. The Studio is an AActor, not a
Usable at the grid origin that could steal selection from central cells.

Six brush symmetries provide one square, left/right mirror, near/far mirror,
half-turn, quarter-turn and full D4 reflection/rotation. An orbit is deduplicated
and painted as one edit. Palette and symmetry changes do not spend history.
Undo/Redo retain the latest 64 drawing edits; a real new edit branches history,
while an identical stroke preserves Redo. Paper erases without a supply cost.

Sixty-four pixel tools plus eight utilities total 72 exact-owned runtime tools.
Cell origins are `((row-3.5)*60, -(column-3.5)*60, 0)`, and the mosaic is at Z=3.
Utilities occupy two rows at X=350/480, Y=180/60/-60/-180, Z=65:
colour, symmetry, Undo, Redo, Export, Next sketch, Save + Load, Save + Clear.
All owned geometry is noncolliding and the tools' own glows have zero intensity.
This is functional native artwork/UI, not new Blender production geometry.

The chosen-sketch preview is a separate 80 cm mosaic at (650,270,90), with a
caption facing the utility row. Browsing changes only that prepared preview;
it never paints over the floor. Load requires a second deliberate use of the
same unchanged preview. Painting or using a different tool cancels confirmation.
The last used control provides bounded near-tool feedback.

## Explicit preservation contract

There is **no directory lookup, read, export or autosave in BeginPlay**. An
actor-life draft needs explicit Export to keep it across actor/game teardown;
the readout says so. No unsaved draft is claimed as protected. Saved files are
never deleted during tool or actor cleanup.

On Windows, E/X Export creates a fresh `Motif_<32lowerhexid>.dgm` under:

`<ProjectSavedDir>/Daedalus/GalleryMotif/Exports/`

IDs come from a fresh native GUID. Parent metadata records the last loaded or
exported sketch ID (or `-` for a new root). It is lineage information, not creator
authentication. Each export is independent; repeating Export creates a new
identity instead of replacing an earlier file. No arbitrary input path is used.

The writer uses actual Windows `CREATE_NEW`, requires a complete write,
`FlushFileBuffers`, successful close and a bounded raw readback exactly equal to
the prepared record before reporting success. A failed fresh/partial export is
retained. Failure leaves the draft, drawing history, baseline and lineage intact;
retrying Export generates another ID. Native write/failure behavior is still
unexecuted and must be accepted before making a runtime preservation claim.

Save + Load first reads and validates the chosen record into a value, confirms
the exact preview, prepares a candidate model, then exports any dirty draft.
It rereads the selected source after preservation before committing. A changed
source refreshes the preview and cancels loading. Save + Clear similarly keeps
a dirty draft before committing a blank model. Both actions require confirmation
and refuse destructive changes on failure, retaining any newly created export.

Dirty is an exact comparison with the last actually loaded/exported 64-cell
baseline. Clearing a kept nonblank picture creates a dirty blank draft; Undo
back to the kept image becomes clean again. Clear never invents a blank saved
baseline. Kept blank exports also report “matches kept sketch” correctly.
Undo/Redo and successful Load/Clear remain model edits, separate from immutable
files. A committed load updates the active lineage to the selected record.

Next sketch streams only the fixed export folder, examines at most 128 entries
and refuses at the 129th rather than allocating an unbounded list. Valid names
sort deterministically; each selected file must match its decoded ID. The reader
caps file bytes at 512 before allocating/decoding. Unreadable/partial/foreign
files are kept and skipped. Overflow/refusal never deletes older sketches.
Other platforms refuse local-file I/O clearly while painting/history remain usable.

## Format and native API finding

A pattern is 74 ASCII bytes: `DGM1:`, exactly 64 digits 0..7, `:`, four hexadecimal
Fletcher16 digits over the first 69 bytes. The fixed palette/version is part of
that pattern. Fletcher detects accidental pixel edits; it does not authenticate
IDs, parent metadata, authorship or ownership.

An export has exactly four ordered fields, canonically LF-terminated:

```text
DGM-DOCUMENT 1
id:<32lowerhex nonzero ID>
parent:<32lowerhex nonzero ID or ->
pattern:<74-byte pattern>
```

Decode accepts an optional UTF-8 BOM, CRLF/mixed line endings and missing final
newline, but no extra field/payload. IDs normalize case; nil IDs, path characters,
self-parent lineage, unknown versions, invalid palette/checksum/length and records
over 512 bytes refuse without partially modifying the output.

The installed UE 5.8 source audit found a real built-in gap:
`Engine/Source/Runtime/Core/Private/HAL/FileManagerGeneric.cpp:95–127` only forwards
Append/AllowRead at lines 110/116; the declared NoReplaceExisting flag is ignored.
`Runtime/Core/Private/Windows/WindowsPlatformFile.cpp:1644` selects
`bAppend ? OPEN_ALWAYS : CREATE_ALWAYS`. Existence-check-then-write would not
protect predecessors. The isolated Windows `CREATE_NEW` helper is therefore
intentional; no shared filesystem framework or module dependency is added.
This is source/API evidence for that installed version, not native execution.

## Evidence and queued acceptance

Portable C++ compiled serially under MSVC C++17 `/W4 /WX`:
**28 checks, zero failed**. Coverage includes 384 independent centred-coordinate
symmetry orbits, exact stroke effects, 64-step Undo/Redo and no-op branching,
alias-safe preparation, independent weighted Fletcher calculation, all single
pixel-digit corruption refusals, strict/bounded document parsing, baseline Undo
and copy-before-commit model preparation. Fresh guard: 10.74 GiB free physical /
38.82 GiB available commit. Unaffected old suites were not rerun.

Bounded root/native/API reviews found no remaining source blocker after the
last-kept-baseline and caption/status corrections. Final three-file source
preflight reports zero known-pattern errors. The checked core was unchanged.

**Unreal UHT/module compilation, Windows export/read/fault execution, actual
72-tool E/X, rendering, legibility, lifecycle and cooking remain unexecuted.**
No editor, live source/assets, builds, installs, push, merge, deployment, external
network, clipboard, paid service, wallet or security action ran in this worker.
The only executed filesystem writes were isolated source/check/packet artifacts.

Six additive files: MotifCore, MotifStudio header/cpp, portable test, runner and
this handoff. Existing Core/Engine/Usable/Hero/ProceduralMesh facilities suffice;
no Build.cs edit or new plugin is required. Packet metadata gives exact paths,
hashes, base/head and new patch order. Other campaign actors are preserved
ancestors, not functional dependencies.

Minimal sole-writer acceptance, queued while skull/toter production continues:

1. Compile/stage on flat ground with room for the grid, 72 tools and preview.
   Paint all symmetry modes; inspect ordinary-distance colour/text, central cell
   selection, orbit outlines, Undo/Redo and palette behavior.
2. Export then verify real bytes/ID/parent/readback and an independent reload.
   Confirm Clear→Undo becomes clean, blank exports show kept status, and old
   files survive further edits, repeated exports, load, duplication and teardown.
3. Test denied/unwritable folder, existing target, short/failed write or close,
   malformed/oversized/partial file, 129 entries and source changes between
   preview/confirmation/commit. A failed operation must never fake preservation
   or mutate draft/history/baseline/lineage. Retain failed artifacts for evidence.
4. Remove/rebind tools/views or end the actor during notifications. Draft Export
   remains available through a remaining valid export tool where possible;
   only exact-owned transient tools are removed. Check cooking and unsupported
   platform refusal separately. No canonical painting/profile policy is implied.

## Lesson and next work

Treat editor/API flags as claims until their active implementation is checked.
An immutable artifact needs a genuine create-once primitive and confirmed bytes,
not a GUID followed by an overwriting writer. A drawing baseline must refer to
actually kept content, not merely the last cleared view. Separate user-confirmed
local artifact creation from canonical profile, inventory and ownership contracts.

Continue substantial non-island source work within the existing deadline;
native integration/file acceptance stays with the sole Unreal writer.
