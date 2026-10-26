# Bricks Blueprint Print Press — edition 1, 25 October 2026

## Player-facing slice and ownership

An explicitly bound Press lets a player keep the current Bridge or Skyline
creation as a new local SVG blueprint. In-progress work is useful too: prints
show current metrics, conflicts, givens and the complete rule specification.
This extends the building/blueprint-library theme in REALM-CASTS.md without
inventing canonical inventory, quest, profile, ownership or payment contracts.

Base: `4755bbe69d6b911048af78bf2e13a011f33a4eae`.
Branch: `codex/bricks-blueprint-prints-20261025-r1`.
Campaign deadline: **2026-10-26 06:56:50 UTC**.

Nine paths: new PrintCore header, Press header/cpp, test/runner/XML verifier,
this handoff, and read-only snapshot getters in the two owned Workshop headers.
Existing rules, Workshop cpp, Trail, shared input/dialogue, Hero, Build.cs,
Obby and other workers' files remain unchanged. Every original packet remains.

## Explicit artifact contract

The designer selects Bridge or Skyline and binds one current source actor.
Null bindings are inactive. BeginPlay performs no file I/O. A deliberate E/X by
an actual standalone LocalPlayer captures a ready source into an immutable
local snapshot, generates the complete SVG in memory, and attempts one fresh
file. Source rules/state, history, first-study facts and progress never change.
The source's full readiness remains required; this is not a recovery importer.

The fixed output is
`<ProjectSavedDir>/Daedalus/BlueprintPrints/Blueprint_<32-lowercase-hex>.svg`.
Each file has a fresh nonzero GUID ID. The parent is this Press's previous
successfully verified print; it is empty for the first print. These IDs describe
local lineage, not authentication or global provenance. No path input, load,
import, enumeration, game-save restore or automatic retry is introduced.

After the first successful print, source kind and exact actor are frozen. A
changed, lost or retargeted source requires a new Press. Later prints preserve
all predecessors. The snapshot records CURRENT completion derived from the
existing core, not an earlier first-study flag. Skyline contradictions remain
printable if heights and givens are valid; Bridge masks obey allowed links and
length allowance. Every print records full R1 rules alongside raw state.

The pure renderer emits deterministic ASCII static SVG, bounded to 64 KiB,
with integer geometry, escaped text, accessibility title/description and exact
metadata. Bridge art labels pads/links/lengths and closed links; Skyline art
labels heights, fixed cells, conflicts and all side clues. No scripts, external
images, fonts, resource links, DOCTYPE or generic platform hashing are used.
The SVG namespace URI is a namespace, not a network request. These are local
practice illustrations, not engineering certificates or ownership claims.

## Preservation and native boundaries

Native writing reuses the proven Windows CREATE_NEW recipe. The generic UE
NoReplaceExisting flag is not substituted: earlier inspected UE5.8 code did
not implement it as exclusive creation. A complete bounded WriteFile, flush,
close, reopen, exact size check and byte-for-byte readback must all succeed
before this actor advances lineage or sends its saved-print event. Existing
files are never overwritten or deleted. Partial/failed fresh files stay for
review, and previous lineage remains intact. Non-Windows hosts refuse honestly.

Actor/source/world/owner/controller lifetime, ready views, reach and epoch are
rechecked across virtual/callback boundaries. State commits before events.
Once writing starts, ending an actor can leave a file: no false no-effect claim
is made. If the source changes during verified writing, the frozen artifact is
still kept and feedback requests a new Press for the changed source.

The snapshot getters copy only current rule/mask or rule/grid. They cannot
mutate history, source rules, persistent state or prior artifacts. Press geometry
is noncolliding and does not change pawn/camera, shared dispatch, floor or gates.

## Focused evidence

One guarded serial MSVC C++17 /W4 /WX run, with 10.34 GiB physical and 36.95 GiB
commit headroom, passed **12 groups, 0 failed**, producing **19 SVG snapshots**
(largest 14,061 bytes). Independent stdlib ElementTree verification passed all
19: exact full specifications/current metrics, independent graph/visibility
oracles, all six valid Skyline alternatives, static ASCII/schema restrictions,
and two exact example files. No prior portable suite was repeated.

Root and bounded peer source reviews found no remaining blocker. Focused
preflight reported **0 errors in four changed native paths**. The checks parse
generated SVG bytes and execute portable rules only; they do not render images
or execute native actor/file behavior. Examples have NOT been visually rendered.
Native UHT/module compilation, Windows file I/O, E/X, callbacks, rendering and
cooking remain **UNCOMPILED / UNEXECUTED**. No browser file-route denial was
retried or bypassed. No editor, live staging, heavy build, push or merge occurred.

Functional order: Bridge `907c173008bf00d7a6b366003de60c1ca299f35a`, Skyline
`a05fed265496c3bed2d0695440d6c2219560e902`, Trail/readiness getters
`4755bbe69d6b911048af78bf2e13a011f33a4eae`, then this patch. The Press does not
require the Trail actor to be placed. Earlier objects in the transfer bundle
preserve ancestry; do not blanket-replay old mural/backlog changes.

Minimal queued acceptance for the sole native writer:

1. On safe ground outside protected obby/runway, bind one fresh Press to each
   ready source. Check no startup I/O; unbound/wrong-world/invalid views refuse.
2. Print unfinished and finished current states, Undo then print, and inspect
   labels/side clues/links plus full metadata. Each explicit use creates a fresh
   file; no source mutation and no fictional first-study/current equivalence.
3. Compare file bytes with frozen snapshot, verify parent chain, collision-safe
   CREATE_NEW, short-write/flush/readback refusal and intact predecessor files.
   Failure files remain; no partial success event/lineage advancement.
4. Exercise source retarget/move/end, controller/end callbacks and shutdown while
   printing. Keep already-created artifacts, honest feedback and exact event
   ordering. Confirm native reach, layout, SVG viewing and cooked behavior.

## Lesson and next task

A saved creation needs its rules and current state, not only a flattering
completion flag. Keep the export one-way and immutable until canonical player
save contracts exist. An exclusive native writer and exact readback preserve
originals more reliably than a convenience flag with unverified implementation.
Next: a substantial source-only player loop in an established non-island realm;
native acceptance for these Bricks stations remains queued, not a reason to idle.
