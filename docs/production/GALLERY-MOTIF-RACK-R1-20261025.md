# Gallery local Study Rack — edition 1, 25 October 2026

## Purpose and ownership

Connect Motif Studio's kept local sketches to Study frames through player input,
without copying a 32-character ID into the editor. This completes a useful
creation/export/display path inside the existing Gallery colour/light theme.
It is an original local affordance under the creative campaign, not Gallery
City's canonical parcel Hang Art, ownership, world-save or server-image protocol.

Base: `163b73e495c60f31593d8ce36fde27af1f038c24`.
Branch: `codex/gallery-motif-rack-20261025-r1`.
Campaign deadline: **2026-10-26 06:56:50 UTC**.
Only five paths change: new Rack header/cpp, a read-only getter in the owned
Studio header/cpp, and this handoff. Core/codec, Study, I/O functions, shared
input, Hero, dialogue, Build.cs, other lanes and live source/assets are untouched.
All predecessor commits, originals and immutable packets remain preserved.

## Player and binding contract

A designer explicitly binds the Rack to one local Studio. The default null
binding is inactive. After keeping or loading a sketch in Studio, E/X at the
Rack prepares a Study reference in the next of four slots. The player walks
to that frame and deliberately uses E/X to read/capture it through Study's
existing bounded matching-ID reader. Preparation performs no disk I/O and does
not claim that a source file still exists or has remained unchanged externally.
Missing/corrupt/unavailable-file handling remains at the actual Study read.

`CopyLastKeptSketchId` returns only a canonical nonempty kept/loaded lineage
reference from an alive active Studio. It leaves caller output unchanged on
failure. It does not expose the current dirty draft as a kept picture, enumerate
files, export automatically, read a file or introduce another persistence model.
An unsaved draft remains available in Studio with its existing history.

The Rack never replaces an earlier prepared Study or duplicates the same ID.
Four prepared references fill the Rack; use a separately placed Rack for more.
Each slot retains its expected ID and exact owned actor identity. An externally
removed or altered slot is not silently reused. Deliberate subsequent Rack
operations check ownership, binding and pose; there is no background tick.
After the first successful preparation, the Studio identity and Rack placement
are frozen for this Rack. A later change stops new preparations and retains the
existing slots. Observed faults stay latched; row labels then say reserved /
unavailable instead of claiming that a stored ID has a valid captured copy.

Study's existing `MotifId` remains designer-editable before capture. A prepared
reference is not a sealed binding against later designer/C++ changes. The Rack
detects a binding mismatch on its own operations and refuses new preparations.
After capture, Study itself preserves the captured image/metadata for its actor
lifetime, including after a later property edit. The Rack does not claim to
authenticate a file or infer that an uncaptured placeholder is already loaded.

Both Rack and prepared Studies are actor-lifetime local views. The original
`.dgm` files remain the durable artifacts, with Studio's unchanged create-new
and verified readback behavior. No canonical creator/profile, supplies, parcel,
reward, minting, payment, multiplayer or world-placement persistence is inferred.

## Native placement and preservation

The Rack owns only its own noncolliding view components and the new native
Study actors it prepares. Its control origin is separate from their origins so
normal E/X selection can choose each one. The four proposed mounts are a 2×2
arrangement: X=-350/-1000 cm, Y=-300/+300 cm, Z=0, with Study scale 0.7.
That spacing accounts for Study's side metadata placard as well as the image.
The sole writer must confirm actual reach, sight lines and ground placement.

Deferred creation sets the reference before FinishSpawning. A pending owned
candidate remains tracked across callbacks. Only a fully begun, still-owned,
correctly bound/posed candidate may commit a slot, after Rack/Studio/participant
lifetime checks. Failure removes only the new exact-owned candidate and leaves
earlier slot records and files intact. Reentry is blocked during preparation
and notification. Teardown removes callbacks before destroying only Rack-owned
ephemeral Studies; actors whose ownership moved elsewhere are not destroyed.

No BeginPlay file lookup/read/write, source image capture, tick, physical light,
pawn movement, world-door operation, external service or network policy is added.
Binding a Rack is one local source-reference choice, not a claim on a parcel.

## Evidence and native acceptance queue

The portable Motif core and all existing file I/O are unchanged. Its prior
**41/0** core result is reused, not rerun or represented as native Rack coverage.
This native-only adapter receives focused source review/preflight rather than
tests that merely mirror its bookkeeping. Exact results/hashes are in the
packet. Native UHT/module compilation, spawning, file capture, E/X, rendering
and cooking remain **uncompiled/unexecuted**. No editor, live activation, engine
build, push or merge occurs in this delivery.

Final source evidence: root and two bounded peers found no remaining blocker.
Review corrected staged-versus-returned spawn cleanup and faulted row wording.
Focused preflight reported **0 errors across four changed native paths**. No
portable core test was rerun and no native spawning or file operation executed.

Functional patch order: Motif Studio R1, Study R1, artist tools R1 (current
Studio source baseline), then Rack R1. Spectrum and other campaign ancestors
are preserved for object transfer but are not functional Rack dependencies.
Never replay previously integrated mural work from a bundle's ancestor list.

Minimal acceptance queued for the sole native writer after current production:

1. Bind Rack to Studio on safe existing ground. Verify default-null refusal,
   no preparation before a kept/loaded sketch, and no startup I/O.
2. Export, prepare, walk to the new frame and capture through E/X. Verify all
   pixels/metadata and clear distinction between preparation and actual read.
   Edit the draft, prepare the same kept reference and confirm no duplicate or
   draft loss; export a new version and use the next slot.
3. Fill four slots, confirm full refusal, then remove/retarget/move a slot and
   confirm no replacement or slot reuse. Check source-file removal/corruption
   at Study capture without changing previous captures or original files.
4. End Rack/Studio/participant during creation or notifications; verify candidate
   cleanup, no partially committed slot and no foreign-actor destruction. Check
   frame spacing, captions, reach, duplication/reload and cooking separately.

## Lesson and next task

A small explicit reference bridge can remove an editor step without creating
another reader or save system. Distinguish preparation from capture, account
for the whole framed object when spacing mounts, and keep captured snapshots
separate from canonical world placement. Native acceptance stays queued; keep
useful non-island source work within the campaign deadline.
