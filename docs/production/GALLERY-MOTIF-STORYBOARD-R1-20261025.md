# Gallery Motif Storyboard Press — edition 1, 25 October 2026

## A durable picture of the local clip

Keep a static contact sheet of an existing Flipbook's two to four captured
sketches, in original order, with full frame IDs/parents, palette indices and
preview settings at capture. This completes a useful local artist path from
kept pictures to a flipbook to a human-readable artifact while preserving every
original. Gallery art/colour context and the campaign's creative freedom support
the tool; it invents no canonical image, ownership, publication, payment,
profile, timeline-import or save-game contract.

Base: `e5029420ec175facc460387ace04dfd85936c462`.
Branch: `codex/gallery-motif-storyboard-20261025-r1`.
Campaign deadline: **2026-10-26 06:56:50 UTC**.
Eleven paths: new StoryboardCore, Press header/cpp, private LocalSvgFiles
header/cpp, test/runner/XML verifier and this handoff; a tiny Flipbook header
copy getter; and the owned BlueprintPress cpp writer extraction. No Studio,
Rack, Study, old core/codec/renderer, Hero, shared dialogue/input, Build.cs,
other worker, board or live source/assets change. All predecessors remain.

## Frozen content and artifact identity

SourceFlipbook defaults null/inactive. Explicit standalone LocalPlayer E/X
copies its actual private captured Player by value. The getter requires Alive
and Book.Active; it deliberately permits valid captured content after controls,
views or partial button setup have failed. It consults neither SourceRack nor
an artist/controller as content authority, reloads no file, pauses no playback
and mutates no source. A copy remains independent while rendered/written.

The contact sheet preserves original frame order even when playback is reversed.
Current index,2/4fps, forward/reverse and playing/paused describe **at capture**;
the SVG never animates or resumes a clip. Frame metadata keeps each original
DGM ID, DGM parent and all64 original palette indices. Frame ancestry need not
match animation order. The native adapter supplies eight sRGB colours derived
from the existing PaletteColour function through ToFColorSRGB, explicitly
formatting R/G/B into six hex digits. There is no alpha byte or external palette
lookup. Native lighting/tonemapping or rendered colour matching is not claimed.

Each sheet has a fresh local artifact GUID. Its artifact parent is this Press's
previous successfully verified sheet, empty on first success. That local print
lineage is distinct from all frame DGM parents. IDs carry no creator/ownership
authentication or global provenance. The first successful sheet freezes the
exact source actor for this Press; another source needs another Press.

The fixed destination is
`<ProjectSavedDir>/Daedalus/GalleryMotif/Storyboards/Storyboard_<32lowerhex>.svg`.
No path input, automatic snapshot, enumeration, import/load, deletion, overwrite,
timeline restoration, external service or network publication is added. Original
DGM files stay the original durable sketches; this is a new one-way descriptive
artifact, not a new saved-game framework.

## Renderer and shared native writer

The portable renderer emits static ASCII SVG bounded to64KiB. Two-column cards
show all pixels and full IDs/parents; current border and text are supplementary
state cues. Full metadata version1 stores artifact identity, separate frame
identity/order/raw indices, all eight supplied palette values and playback
state. The namespace is `urn:daedalus:motif-storyboard:1`. There are no scripts,
SVG animation, external images/hrefs, font resources, DOCTYPE or network fetches.
Input IDs/palettes/state are validated, and output commits only after completion.

The existing Blueprint Press's exact exclusive-write recipe is extracted into
one narrow same-module private helper, now used by both presses. It accepts
only Kind::Blueprint or Kind::Storyboard, strict nonzero32-lowercase-hex IDs
and1..65536bytes before directory IO. Callers cannot supply a root, path,
extension or maximum. Blueprint retains EXACTLY its previous
`Saved/Daedalus/BlueprintPrints/Blueprint_<id>.svg` mapping and error messages.

Windows uses CREATE_NEW, complete WriteFile/count, FlushFileBuffers, checked
close, read-only reopen, exact length BEFORE allocation, full read/count,
checked close and byte equality. Every old/failed fresh file stays intact;
partial files are never reused/deleted. Other platforms refuse explicitly.
The old generic NoReplaceExisting flag is not substituted and no platform hash
call is introduced. The extraction adds no persistence registry or service.

The Press advances its parent/filename/source binding and emits its saved event
only after that writer returns verified success and its own lifetime/epoch
still matches. Failures retain prior lineage. If source/actor changes after
writing begins, a fresh file may already exist; feedback never falsely promises
no effect or removes it. A verified frozen sheet can remain valid even when the
source ends afterward. Views/lifetime/local player/reach are rechecked before
IO; state commits before callbacks, with reentry blocked. No Tick/startup IO,
owned collision, pawn movement, reward or canonical progress write exists.

## Focused evidence

One guarded serial MSVC C++17 /W4 /WX run passed **14 groups,0failed**, producing
8 static sheets, largest31,777bytes. Independent stdlib ElementTree verification
passed all8, checking **1,536 exact row-major pixel rectangles**,2/3/4 original
frame order, full IDs/parents/raw palette indices, current borders and all capture
state/palette metadata. Two exact example files are included. Guard headroom was
11.46GiB physical/37.91GiB commit. Old codec, playback and Blueprint rendering
suites were unchanged and not rerun as new/native evidence.

Source comparison confirmed the Windows critical write/read block is identical
after normalizing only the added kind argument. The entire Blueprint actor
implementation is identical after its writer/filename call replacements;
LocalReach/Wrap, fixed path, limits, lineage/notification logic and old errors
are retained. Bounded independent writer and new-Press/getter review found no
blocking remainder. Source preflight reported **0 errors in six native paths**.
The installed public ToFColorSRGB API was inspected read-only; this was not a
colour conversion run. All comparison/API records remain in the packet.

These checks execute portable generation and parse files under the worker's
check folder. Examples have NOT been visually rendered. Native UHT/module
compilation, new/shared Windows writer execution, readback faults, actual
palette conversion, actor input/callbacks, file viewing and cooking remain
**UNCOMPILED / UNEXECUTED**. No editor, live staging, browser denied-route retry,
engine/full build, push, merge or external publishing occurred.

Minimal acceptance for the sole native writer:

1. Compile isolated sources with both presses and shared helper. Verify old
   Blueprint path/bytes/error/success/failure/parent behavior remains. Exercise
   CREATE_NEW collision, short write/flush/close/readback failures and retained
   previous/failed files; no earlier file may be replaced or deleted.
2. Bind a captured2–4-frame Flipbook and use the new Press. Check no startup IO,
   source-read-only/playing-at-capture behavior, exact order/pixels/palette/IDs,
   repeat sheets with distinct GUIDs, separate artifact/frame parent roles,
   full filename getter and the documented folder. SVG is static, not playback.
3. Fault/end controls or partial setup after valid frame capture: the data copy
   can still preserve it. Wrong/unbound/ended source refuses. Retarget source
   after first success and during callbacks/IO; prior files stay and source
   locking/late saved-copy feedback remain honest. No clip/pawn/reward mutation.
4. Inspect SVG readability/colours in an approved normal viewing context, real
   E/X/local player/actor lifetimes, unsupported-platform refusal and cooking.
   No denied browser route is a validation workaround.

Functional order: Flipbook `76ae32ee402d5efbfb9ae8b04275752558bc316c` and its
Studio/Study/Rack dependencies, Blueprint Press
`553e1dc3eaba25f08d97e4ad437189448f653003` and its declared prerequisites, then
this patch. The shared helper extraction means both native callers must be
included together. Guide is an artist-workflow companion, not runtime required.
Other bundle ancestors retain transfer history, not blanket integration scope.

## Lesson and next task

Keep actual frozen content separate from a mutable request or live preview.
Contact-sheet order and artifact versus frame lineage answer different questions;
record them explicitly. Extract an established IO protocol only when a concrete
second caller needs it, preserve its exact behavior and distinguish source
comparison from execution. Next: assess adaptive local Parcels street guidance
as a complete exploration aid, without changing canonical host/settlement rules.
