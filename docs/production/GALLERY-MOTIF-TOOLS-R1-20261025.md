# Gallery Motif artist tools — edition 1, 25 October 2026

## Purpose and ownership

Extend the existing Motif Studio's useful creation loop with connected area
fill and whole-picture rotation/reflection. This is original design within the
authorized creative campaign and Gallery City's colour/light theme
(`REALM-CASTS.md`), not a newly claimed requirement of ADR-035. The accepted
server maze-frame contract stays separate from these local `.dgm` studies.

Base: `e28655268c4e908fea3010e279dce2165e923900` (Motif Study plus Studio R1).
Branch: `codex/gallery-motif-tools-20261025-r1`.
Deadline: **2026-10-26 06:56:50 UTC**.
Only the owned Motif Core, Studio header/cpp, focused core test and this new
handoff change. Every earlier commit and packet remains intact. No Hero,
dialogue, shared input, Build.cs, island, live source or asset is edited.

## Player behavior

The default brush remains **Point**. A new **Brush: Point / Area fill** utility
switches only the next square action, without changing pixels or drawing
history. Area fill starts with the four-neighbour connected patch matching the
clicked square's original colour. Diagonal corners do not join; rows do not
wrap. The selected symmetry copies that original patch to its mirror/rotation
positions. Their union is painted in one edit. It never floods again through
newly coloured or copied squares. A same-colour click may still change an
asymmetric mirrored copy; only an entirely unchanged result is a no-op.

The square prompt states the current target count and ink. The last selected
square's outlines show the next operation's targets on the current canvas.
Paper / erase works as ink zero. Fill may change the whole blank background;
one Undo restores the full previous image.

Three explicit tools transform the entire draft, independently of brush and
symmetry choices:

- **Rotate picture / Clockwise 90:** `(row, column) -> (column, 7-row)`.
- **Flip picture / Left-right:** `(row, column) -> (row, 7-column)`.
- **Flip picture / Near-far:** `(row, column) -> (7-row, column)`.

Each changed fill/transform is one existing drawing-history entry. No-op
operations keep Redo. A changed operation branches history in the existing way.
Ink, symmetry and brush choice remain outside pixel Undo/Redo. Export still
creates a fresh local artifact with existing lineage and preservation checks;
these tools never replace a kept export or modify a captured Study actor.
The last-kept pixel baseline still determines dirty state, including after Undo.

## Native layout and compatibility

The eight existing action ordinals and Cell ordinal remain unchanged. New
Brush/Rotate/FlipColumns/FlipRows actions are appended at 9..12. The original
64 square origins and eight utility origins remain unchanged. Four additional
utilities use X=610 cm, Y=180/60/-60/-180, Z=65, bringing the owned count to 76.
There is no new actor class, input binding, tick, physics or network behavior.
The existing exact tool binding/readiness and LocalPlayer/reach checks apply.
Using any new action cancels an armed Save + Load/Clear confirmation through
the existing action-change rule.

No file reader/writer, directory enumeration, codec, document version, ID,
checksum, filename, canonical profile, parcel, supplies, ownership, reward or
payment policy changes. The original Windows-only local I/O acceptance remains
pending; no I/O is executed by portable checks.

## Evidence and pending acceptance

Focused portable checks exercise the changed core with independent component
and coordinate oracles, source-snapshot symmetry behavior, transform identities,
colour preservation and one-step history. The single serial MSVC C++17
`/W4 /WX` run passed **41 checks, 0 failed**, including 1,536 original-region
selection comparisons and 192 one-pixel transform permutations. Its fresh
guard reported 10.50 GiB free physical memory and 38.25 GiB free commit. The
unchanged original checks were included once because Session changed; no other
realm suite was rerun. Focused native source preflight reported **0 errors in
two files**. Root and bounded native/core peer reviews found no remaining source
blocker. Source review/preflight are separate from native compilation.

Native UHT/module compilation, actual E/X, 76-tool selection/reach, visual
orientation/legibility and cooking remain **uncompiled/unexecuted**. No editor,
live activation, engine build, push or merge occurs in this delivery.

For the sole Unreal writer's later dedicated acceptance:

1. Confirm default Point and unchanged original tools, then switch Area fill
   and fill an enclosed region, background and diagonally separated patches.
   Verify target count, symmetry copies, Paper erase and one-step Undo/Redo.
2. Rotate a visibly asymmetric picture four times and each flip twice. Verify
   rendered direction, all colours, no-op Redo and last-kept dirty status.
3. Arm Save + Load/Clear, use a new tool, and verify confirmation was cancelled.
   Export a transformed version and confirm earlier file bytes, lineage and a
   previously captured Study remain intact. Record actual I/O separately.
4. Inspect the added bank beside the preview, label/readout readability,
   missing-tool refusal, EndPlay notifications and cooked behavior. Do not
   promote portable evidence to native acceptance.

## Lesson and next task

Improve an existing creative loop before adding another disconnected prop.
Freeze fill membership before symmetry writes, use one history transaction,
and make preview/count semantics share the same portable target selection.
Native acceptance stays queued with the sole writer; continue substantial
non-island source work within the campaign deadline.
