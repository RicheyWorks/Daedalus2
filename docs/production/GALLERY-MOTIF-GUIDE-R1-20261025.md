# Gallery Motif kept-image Guide — edition 1, 25 October 2026

## Artist-facing slice

Help artists draw successive pictures for the new Flipbook using the Studio's
existing kept/loaded image as a guide. One appended tool cycles **Off -> Kept
Ghost -> Changes**. It starts Off. Hollow inset marks show reference ink or
changed squares while the actual draft remains visible and fully editable.
This is a local art aid under the creative campaign, not a canonical animation,
profile, world-save, material-supplies or image-ownership contract.

Base: `76ae32ee402d5efbfb9ae8b04275752558bc316c`.
Branch: `codex/gallery-motif-guide-20261025-r1`.
Campaign deadline: **2026-10-26 06:56:50 UTC**.
Exactly three paths: owned Studio header/cpp and this handoff. No new core,
file format/reader/writer, history, Studio pixel rules, shared input, dialogue,
Hero, Build.cs, other lane, live source/assets or board changes. Every prior
export, packet and original remains intact.

## Reference and display contract

The reference is the actual existing `Baseline`, only when `LineageId` is
canonical/nonempty and the image is valid. It is never the browse-only `Chosen`
preview, a dirty draft snapshot, inferred animation frame or a newly read file.
A kept blank image is a valid reference. With no kept/loaded reference, the
tool refuses without enabling a guide and explains how to obtain one.

Existing transaction semantics are reused unchanged:

- Verified Export commits its pixels/ID as Baseline/Lineage.
- Successful Save + Load commits the LOADED document's pixels/ID, including
  when a different draft was preserved first.
- Dirty Save + Clear commits the preserved pre-clear image/ID, then leaves a
  blank draft. Clean Clear retains the existing reference. It is not reset to
  blank just because the visible draft was cleared.
- Painting, transforms, Pick, Undo/Redo and Next Sketch do not change reference.
  Failed/cancelled operations keep it, including a refused Load after a fresh
  preservation file was created. It describes the Studio's committed reference,
  not the globally latest file on disk or a claim that a backing file still exists.

Kept Ghost places small hollow reference-colour marks only where Baseline has
ink. Actual tiles remain untouched; Paper0 stays actual Paper/erase, including
under a reference mark. Changes places inset dark-backed gold outlines only
where `Draft.Canvas()[cell] != Baseline[cell]`. These are opaque geometry marks,
without an unverified transparent-material assumption. Existing outer target
outlines remain separate and larger, so brush/symmetry/fill/Pick targets persist.
The readout names the kept/loaded reference ID prefix and says marks are not paint.
The chosen-sketch preview remains unchanged.

Guide does not modify actual pixels, Ink, Point/Fill, symmetry, selected square,
armed Pick, Undo/Redo, Baseline, lineage or files. Pick still samples the actual
Draft.Canvas value, and Fill uses the original actual connected-colour region;
neither samples display marks. Guide is exempted from generic Pick cancellation.
Like every other tool, it cancels an armed Save + Load/Clear confirmation under
the existing any-other-tool-cancels rule. Feedback/guide state is actor-life only.

## Compatibility and placement

Append `Guide` as enum ordinal15 and native slot85; count becomes86. Every old
ordinal0..14 and slot0..84 keeps its exact action, parameter, index and position.
Explicit special mappings avoid the former generic `63+Action` fallback mapping
Guide to palette slot78, or the old pose fallback overlapping Pick Ink.

The new utility stands at local `(480,-300,65)`, beside existing Pick and below
the previous utility row. Parameter is exactly-1, and existing exact owned-slot,
binding/pose/readiness guards remain. No world scan, shared dispatch, controller
binding, automatic reference capture or new IO path is introduced. Use a fresh
Studio for native acceptance; there is no automatic retrofit or duplicate spawn
into a running85-tool instance. Existing Export recovery remains unchanged.

## Focused evidence

One small guarded serial MSVC C++17 /W4 /WX compatibility run passed **10 groups,
0failed**, with11.13GiB available physical/37.44GiB commit headroom. The harness
embeds the EXACT old and new native helper/enum text, with only FVector/int32/
uint8 stand-ins, and compares all85 legacy slot coordinates/actions/parameters,
round-trip indices/validity and15 old enum ordinals. It also checks the unique
new85/15/86 mapping, pose and utility parameter bounds. Source text, extraction
metadata, runner and log are retained outside the repository and in the packet.

That check executes extracted pure mapping helpers, **not Unreal**, rendering,
painting/history or IO. No mocked Guide-operation test is claimed as evidence.
The existing41/0 painting/codec result is unchanged and was not rerun. Root and
bounded diff review confirmed actual tile/Pick/Fill/history and transaction
update points have no changes. Native preflight reported **0 errors in two paths**.

Native UHT/module compilation, actual tool spawn/selection, view contrast,
reference updates during real Windows IO, rendering and cooking remain
**UNCOMPILED / UNEXECUTED**. No editor, live staging, engine/full build, browser
denied-route retry, push, merge, external publication or financial action occurred.

Minimal acceptance for the sole native writer:

1. Fresh Studio: all85 old tools plus one Guide at the documented position.
   Verify old saved/Blueprint ordinals and palette/Pick placements, exact-slot
   guards, default Off and no-reference refusal. A kept blank image is valid.
2. Keep a nonblank picture, enable Ghost and draw a shifted next frame. Check
   hollow marks versus actual Paper/ink and contrast on every palette colour.
   Armed Pick on Paper under a mark must choose Paper; Fill ignores marks.
   Guide cycles must preserve Undo/Redo, brush, symmetry and selected square.
3. Check Changes for one recolour/erase, matching pictures, Undo/Redo and whole
   transforms. Existing outer target outlines remain distinguishable. Next
   Sketch does not change reference; verified Keep and successful Load do.
4. Dirty/clean Save + Clear, cancelled/failed Load after preservation and export
   failure must preserve the documented reference and originals. Guide must not
   serialize into an export or spend history. Confirm layout, duplicate/load,
   recovery, native rendering and cooking with no auto-retrofit assumptions.

Functional dependency is the current Studio through Palette/Pick checkpoint
`7f8fa1b28dde3e0d5b62981f93d4d37ad91e3a9c` and its declared predecessors.
Flipbook is a useful workflow companion, not a runtime Guide dependency. Other
objects in a bundle preserve ancestry; apply explicit patches, not old mural
or unrelated backlog changes.

## Lesson and next task

An artist's reference and actual paint must stay visibly and logically distinct.
Reuse verified committed state rather than browse previews, and preserve old
tool mappings explicitly when appending a utility. Next: select another
substantial supported non-island feature; keep native acceptance queued and
canonical profile/ownership/save contracts unchanged.
