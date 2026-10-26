# Gallery Motif Study — edition 1, 25 October 2026

## Purpose and lineage

A read-only local display for the Motif Studio's actual `.dgm` exports. A level
designer binds a sketch ID; the player deliberately reads it through E/X, and
the framed mosaic remains a fixed snapshot for that actor lifetime. This closes
the local creation/export/display loop without adding a new drawing format or
pretending to integrate Gallery City's server frames or parcel permissions.

Base/dependency: `dbf0f946b94c97a4a68a3e86ae61545ac0ca7285` (Motif Studio R1).
Branch: `codex/gallery-motif-study-20261025-r1`.
Campaign deadline: **2026-10-26 06:56:50 UTC**.
The original Studio commit/packet and all predecessors remain preserved.

Only five source paths are owned: new `DaedalusGalleryMotifStudy.h/.cpp`, a
private `DaedalusGalleryMotifNative.h` adapter, a narrow change in the already
owned Studio cpp and this handoff. No Hero, dialogue, input, Build.cs, server,
canonical art viewer, painting supplies, board or live source/asset is edited.

## Explicit binding and display contract

Place `ADaedalusGalleryMotifStudy` deliberately on existing ground and provide a
32-hex local Motif ID. The default empty binding remains inactive. Placement
does not grant parcel ownership, publish or hang a server frame, mint anything,
or read an arbitrary file path. Only the fixed local export folder from Studio
R1 is used. The existing standalone LocalPlayer/Usable interface supplies E/X.

Constructor and BeginPlay do no disk I/O. On the first deliberate valid read,
the same existing reader enforces Windows support, filename/decoded identity,
the 512-byte cap, strict document/version/checksum rules and atomic outputs.
Unsupported platforms or missing/corrupt/incomplete files refuse clearly.
No directory enumeration, writer, deletion or new persistence framework is added.

After a successful read the actor copies pixels, decoded ID and parent into an
actor-lifetime snapshot. Further Use shows metadata without rereading or replacing
the image. Editing the placement ID afterward does not retarget that snapshot;
use a new actor identity for another version. The source export is never changed.
The cache is not a canonical world save or durable player profile; the original
local artifact remains the durable source, and world-placement binding stays explicit.

The noncolliding +X-facing frame displays the 8×8 image at 240 cm square, roughly
Z=20..260 above its floor origin. A separate metadata placard keeps text off the
art. Geometry/material assignment belongs only to this new actor. Existing art,
actors, transforms and shared material assets remain untouched.

## Reuse and preservation

The private same-module adapter exposes only `ReadLocalExport` and `PaletteColour`.
It delegates to the Studio's existing bounded reader/palette, then validates the
document ID against the filename ID before committing output. Studio's previous
`ReadChosen` now calls that same adapter; its behavior and export transactions
are unchanged. There is no second codec, filesystem policy or palette copy.

Views and participant lifetime are checked before capture and across notification
boundaries. A failed read/render-readiness check retains prior state; completion
metadata is committed before observers are notified. Rendering/capture must not
continue writing after EndPlay. This read-only prop has no rewards, resources,
network calls, imported images or canonical ownership authority.

## Evidence and queued native acceptance

The Motif core/codec is unchanged; its existing **28/0** portable result is reused,
not rerun or presented as a new test count. The new adapter/actor is checked by
bounded source review and focused preflight. Native UHT/module compilation,
Windows reading, actual E/X, frame/placard legibility and cooking remain
**uncompiled/unexecuted**. No editor, live activation, file export, engine build,
push or merge occurs in this code-only delivery.

Final evidence: root and two bounded peer reviews found no remaining source
blocker; the unsupported-platform message was corrected for this read-only prop.
Focused source preflight reported **0 errors across the four changed native
paths**. This pattern check does not compile or execute Unreal code, and no
file loading or actor interaction was performed. Unchanged core tests were not
rerun.

Packet metadata records exact files/hashes, base/head and new patch order. Apply
Motif Studio R1 first, then this patch. Other campaign actors are preserved
ancestors rather than functional dependencies. The shared reader's previously
documented Windows-only boundary and pending file-I/O acceptance still apply.

Minimal acceptance for the sole native writer, queued behind current production:

1. Compile/stage a dedicated prop with a known valid exported ID. Confirm the
   empty/default case does no I/O, normal E/X reach works and the first capture
   matches all 64 palette cells and decoded identity/parent.
2. Reuse the prop, change its placement ID and alter/remove the source externally.
   The existing captured image must remain fixed. A new actor can deliberately
   read another version; no source export is rewritten.
3. Test missing, malformed, oversized and mismatched-ID files, unsupported platform
   refusal, lost views/participant and EndPlay during notification. No failed
   operation may fake a capture or change another actor's data.
4. Inspect front/back orientation, margins, metadata at player distance, source
   reader errors, reload/duplication and cooked behavior separately. Record actual
   evidence without promoting earlier source checks to runtime acceptance.

## Lesson and next task

A saved creation needs a small reliable consumer, not another codec or a broad
gallery manager. Reuse one bounded reader and palette, freeze the captured value,
and distinguish local study references from the canonical parcel/server contract.
Continue useful non-island source work within the same campaign deadline;
native acceptance remains with the sole Unreal writer.
