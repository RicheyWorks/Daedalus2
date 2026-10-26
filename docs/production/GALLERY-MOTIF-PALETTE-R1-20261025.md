# Gallery Motif direct palette and ink pick — edition 1, 25 October 2026

## Purpose and ownership

The existing Studio draws eight palette chips, but selecting an ink required
cycling through colours. Make those same chips directly usable and add a
one-shot ink picker from the current floor draft. This improves the existing
creation/export/Study loop without another actor class, image format or save
system. It is an original affordance in Gallery's colour/light theme.

Base: `197cbeaf7e14fb7643602a4c2bcee8b3d4e55f2f`.
Branch: `codex/gallery-motif-palette-20261025-r1`.
Deadline: **2026-10-26 06:56:50 UTC**.
Only the owned Studio header/cpp and this handoff change. Core/codec, file I/O,
Study/Rack, saved sketches, shared input, Hero, dialogue, Build.cs, other lanes
and live source/assets are untouched. Every prior commit/packet is retained.

## Player behavior

E/X on a numbered palette chip selects its ink directly. The existing eight
colours and Paper / erase remain unchanged, and the original Next colour tool
still works. Each chip has a compact number; an asterisk and the existing
canvas outline indicate the selected ink. Full colour names appear in the
prompt and main readout, rather than requiring colour discrimination.

**Pick ink** arms one deliberate floor-square read. Its prompt names that
square's current draft colour. E/X picks that ink, including Paper zero, and
resumes the previous Point or Area fill brush. It never samples the saved
preview, paints a pixel, changes the dirty baseline, exports, or adds/clears
Undo/Redo entries. Clicking Pick again cancels; any other utility also cancels
the pick. Brush/symmetry state is retained except when explicitly changed by
its own utility. While armed, outlines represent one square rather than a
symmetry orbit or fill component. After picking they show the resumed brush.

Palette and Pick actions use the existing action-change rule to cancel armed
Save + Load/Clear confirmations. There is no silent load, clear, autosave,
source-file lookup or captured-Study update.

## Tool identity and native layout

Old action ordinals 0..12, all 76 existing control origins and the Cell field
schema stay unchanged. Append Palette=13 and PickInk=14. The new total is 85:

| Tool indices | Action | Parameter | Local origin |
| --- | --- | --- | --- |
| 0..63 | Cell | 0..63 | Existing floor pixel centres |
| 64..75 | Existing utilities | -1 | Existing three utility banks |
| 76..83 | Palette | 0..7 | `(-210+60*colour,-300,0)` |
| 84 | PickInk | -1 | `(610,-300,65)` |

Shared action/parameter/index helpers drive spawn, readiness and caller
validation. Palette bodies and glows stay hidden; the original procedural
chips remain the coloured view. Their small labels face upward at Z=8 and use
light/dark text selected from chip luminance. They deliberately avoid the old
vertical utility-label pose, which would occlude because the chips vary in X
at the same Y. These are source-defined placements; actual readability remains
native acceptance. Other tool component poses and label sizes are preserved.

The entry point now requires the exact spawned tool slot, owner, action,
parameter and pose. A reconfigured foreign/retargeted tool cannot operate a
different Studio. The existing real LocalPlayer/reach checks and full tool/view
readiness still apply. A remaining valid Export tool continues its existing
recovery path when another view/tool fails. Configuration validates owned
components before changing label geometry. No shared interaction dispatch changes.

## Evidence and queued native acceptance

The portable core and all I/O code are unchanged; prior Motif **41/0** evidence
is reused, not rerun or described as executing these native controls. This
native-only input/view change receives focused source review/preflight. Exact
results and files/hashes are recorded in the packet. Native UHT/module
compilation, E/X selection, label rendering, reach and cooking remain
**uncompiled/unexecuted**. No editor, live activation, engine build, push or
merge occurs in this delivery.

Final source evidence: root plus two bounded peers found no remaining source
finding. Focused preflight reported **0 errors in the two changed native files**.
This pattern check does not compile or exercise the 85-control native adapter;
no portable suite was rerun for unchanged code.

Functional prerequisites are Studio R1, Study's existing shared reader adapter
and artist tools R1. Rack is preserved in source history but is not required
by these controls. Apply only explicit new patch order from manifests, without
replaying unrelated campaign actors or already integrated mural work.

Minimal acceptance for the sole native writer after current production:

1. Use a fresh Studio actor; confirm all 76 original positions/actions and nine
   new controls. Select all eight chips from normal player reach and verify
   names, selected mark, contrast and flat-label direction at oblique distance.
2. With both Point and Area fill selected, pick every draft colour including
   Paper. Confirm one-shot return to the same brush, unchanged image, dirty
   status, Undo/Redo counts and saved preview. Pick again/other utilities cancel.
3. Arm Save + Load/Clear then use Palette/Pick; verify cancellation. Export the
   resulting drawing and check existing file bytes, lineage, Rack references
   and captured Studies remain intact through their existing acceptance paths.
4. Retarget a control to a second Studio, remove a view/tool or end an actor
   from a notification. Reject cross-session edits, preserve the draft and
   retain the valid Export recovery path. Check reload/duplication/cooking
   separately; actor-life drafts still require explicit Export to keep.

## Lesson and next task

Make visible affordances usable: direct swatches and a one-shot picker remove
cycle-counting and colour guessing. Once a tool index carries more than one
kind of parameter, centralize the tagged mapping and keep compact floor labels
out of the vertical utility feedback layout. Native acceptance stays queued;
continue substantial isolated non-island source work within the campaign.
