# Gallery Motif Flipbook — edition 1, 25 October 2026

## Connected artist workflow

Animate local pictures made with the existing Motif Studio. Keep two to four
original exports, prepare them on the existing Rack, and deliberately capture
each Study. A Flipbook explicitly bound to that Rack copies its ready studies
once, in rack order, into an initially paused preview. PLAY starts playback;
frame stepping, reverse, speed and thumbnails make the small animation readable.

Gallery colour/light and art viewing provide the theme (REALM-CASTS and the
Gallery/Studio/Rack handoffs). This is an original local artistic facility under
the creative campaign, not an authored canonical animation quest, parcel frame,
creator identity, publication, payment, ownership or persistence protocol.

Base: `5cb339ee00d005391937e2533875ed41f44f7f0c`.
Branch: `codex/gallery-motif-flipbook-20261025-r1`.
Campaign deadline: **2026-10-26 06:56:50 UTC**.
Nine paths: six new Flipbook core/native/test/runner/handoff paths, the narrow
Study header copy getter, and Rack header/cpp ordered-copy getter. No Studio,
file reader/writer, codec/core, shared input/dialogue, Hero, Build.cs, island,
other lane, live source/assets, transaction or network action changes. Every
original artifact, predecessor and packet remains preserved.

## Snapshot contract

SourceRack defaults null/inactive. First E/X requires all prepared rack slots
to be ready captured copies, and exactly2–4 frames. One frame refuses without
consuming the capture so an artist can add frame2; this avoids freezing a still
image while promising animation. Missing slots are named in recovery feedback;
there is no silent skip/reorder or world-actor scan to guess a source.

Study's new C++ getter copies its private immutable Captured Document, not the
editable MotifId property. Rack's getter reuses its existing ObservePrepared
and exact study binding/pose checks, copies every prepared slot in order, then
compares the ACTUAL captured document ID with its prepared reference. Caller
images/count commit only after the complete snapshot; errors leave them intact.
Neither getter performs IO, preparation, capture, callbacks, ownership transfer
or changes to existing drafts/artifacts. Existing Rack readiness policy remains.

The portable player validates canonical IDs/parents/pixels with the existing
codec and freezes used documents by value. IDs must be distinct; identical
pixels with distinct kept IDs are valid intentional holds. Unused array slots
are ignored. Parent metadata remains exact information: frameN.Parent need NOT
equal frameN-1.Id, because export lineage is not animation order. No new IDs or
invented authorship/authentication claims are attached to the copied frames.

After capture, later SourceRack edits, Study retargeting or Rack/Study ending
cannot change, reload or retract this preview. It never reads them again. A
different clip needs a new bench; original documents/files remain the durable
artifacts. There is no timeline export/import, replacement, auto-save, migration,
profile or canonical progress. The preview itself is actor-life state only.

## Playback and native assembly

The clip starts frame1, forward, PAUSED at2fps. Explicit controls are:

- Play/Pause toggles playback. Root E/X pauses or reads metadata; it never starts
  motion accidentally.
- Previous/Next step exactly one slot and pause. Their direction is explicit,
  independent of current playback direction.
- Reverse changes playback direction without jumping frame and retains playing
  versus paused state.
- Speed toggles2/4fps without jumping frame and retains playing/paused state.
- First Frame returns to frame1 and pauses without replacing any picture.

Each deliberate control clears fractional phase, so inspection resumes from a
full frame duration. Native sampling ticks only while playing. Advance uses
bounded modular arithmetic, even for huge finite elapsed values; it never loops
once per missed frame or publishes intermediate-frame events after a hitch.
Negative/nonfinite delta refuses without mutation. A complete cycle can leave
the same current frame while correctly advancing fractional phase. Game pause
follows normal world Tick; no clock/settings/movement changes are introduced.

The +X-facing mosaic uses Study's exact row-major orientation (columns progress
toward-Y, rows toward-Z) and the same PaletteColour function. Four thumbnails
show rack order and current selection. Full copied ID/parent plus frame number,
speed/direction and paused/playing text provide identity and state. There is no
new file reader: the shared private adapter is used for its palette only.

Place upright at unit scale on existing safe ground, yaw allowed. Main preview
centre is local(0,0,230), pixel field240x240cm; metadata panel is at Y=-330.
Six floor buttons are at X=180,Y=-225,-135,-45,45,135,225. Their short labels
avoid paragraphs on controls. Actual sight lines, font scale and E/X reach are
native acceptance, not established by source geometry.

BeginPlay creates no controls, source capture, file IO or autoplay. First
successful snapshot makes one explicit setup attempt, creating six fresh exact
native button actors. The frozen frame and original actual standalone local
artist/controller are checked around creation and use. Buttons are owned but
unattached; exact slot/class/owner/world/binding/pose/readiness precedes input.
No shared dispatch, input action, Slate or dialogue changes are required.

Staged and returned effects stay tracked across callbacks, including course end
before late owner assignment. Live partial failure preserves copied frames and
partial buttons; no automatic retry/replacement discards or duplicates them.
Buttons decline mutation until complete setup. State commits before view events,
and reentry is blocked. Changed placement, artist/controller, views or controls
pause playback and keep copied images/metadata. Source endings are independent.
Normal teardown removes callbacks and destroys only exact new owned buttons,
never source studies, the Rack, a Studio, files or a pawn. All geometry is
noncolliding; no physical light, gate, reward, inventory or network action exists.

## Focused evidence and queued acceptance

One guarded serial MSVC C++17 /W4 /WX run passed **15 groups,0failed**, with
10.61GiB physical/37.00GiB commit headroom. Tests cover frozen2–4 documents,
canonical/duplicate/invalid snapshot refusal and atomicity, same-pixel distinct
IDs, unused slots, unrelated parents, source-document scope ending, exact2/4fps
boundaries and fractional phase, manual/reverse wrapping, paused controls,
huge finite/modular deltas and negative/nonfinite refusal. The old41/0 Motif
codec/painting suite was not repeated. This executes the new portable player;
it does not execute native Study/Rack actor ending or render the animation.

Bounded source review found no blocking issue in native copy/identity, six-button
setup/preservation, input guards, palette/orientation and paused startup.
Focused preflight reported **0 errors across five changed native paths**.
Native UHT/module compilation, original file capture, actor spawning/lifetimes,
real controls, animation/rendering, camera/readability and cooking remain
**UNCOMPILED / UNEXECUTED**. No browser file-route denial was retried/bypassed,
editor or live staging used, or engine build/push/merge performed.

Functional dependencies: original Studio `dbf0f946b94c97a4a68a3e86ae61545ac0ca7285`,
Study `e28655268c4e908fea3010e279dce2165e923900`, Rack
`197cbeaf7e14fb7643602a4c2bcee8b3d4e55f2f` and their existing declared header
dependencies. Artist tool/Palette ancestors enable the current workflow but
are not new persistence contracts. Other realm ancestors in bundles preserve
transfer history; apply explicit patches rather than old mural/backlog replay.

Minimal queued acceptance for the sole native writer:

1. Create/keep2–4 distinguishable native sketches, prepare Rack slots and capture
   Studies. Null Rack, one frame and an uncaptured slot must refuse without
   consuming Flipbook capture; feedback names the missing slot. Confirm actual
   captured ID versus a changed-and-restored requested MotifId is checked.
2. Explicit capture starts paused at frame1 with six buttons and zero file IO.
   Inspect pixels, orientation, thumbnails, full IDs/parents and legible controls.
   Play/Pause, steps, reverse, speed and first-frame must preserve every image;
   repeated root E/X only pauses. Check game pause/hitches and real2/4fps timing.
3. End/change source Studies/Rack after copy: playback and metadata stay. Change
   bench/controls/artist during callbacks, fail/end midway through button setup,
   and reown a new button. Preserve partial/captured effects and foreign actors;
   no replacement, duplicate capture, unbound activation or autoplay.
4. Check exact original LocalPlayer input, teardown, duplicate/load construction
   references, material/camera/text and cooked behavior. No reward/save changes.

## Lesson and next source priority

Copy actual immutable content and identity rather than mutable request fields.
Animation order and artifact ancestry answer different questions; preserve both
without inventing a relationship. Default paused motion, bounded timing and
short labeled controls turn saved art into an understandable creative loop.
Next: improve iterative frame drawing inside the existing Studio with an opt-in
last-kept-image guide, preserving actual pixels/history/IDs and old tool ordinals;
assess its exact source contract/ownership before any edit.
