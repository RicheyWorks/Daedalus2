# Gallery mural rebuild safety and painter-contract decision — 2026-10-23

## Painter contract: established rules and unresolved binding

The authoritative mechanics registry points to
`docs/production/Realm-production-2026-10-13.xlsx`. Read-only extraction inspected
**Mechanics!A32:E34** and **Chemistry!A6:L6**. GAL01 specifies restoring murals and
colour knowledge, with abilities proposed. Chemistry lists the realm ingredients.
Neither range defines native player identity, initial supplies, legacy-state
migration, inventory debits or persistence. The shared workbook was not modified.

The existing Java contracts establish these narrower facts:

- `LivingPainting.java`: the host owns identity, inventory and persistence;
  `paint` accepts caller-owned palette and knowledge, and `reveal` takes knowledge.
- `PigmentPalette.java`: a painter's pots start empty, pigment operations retain
  their existing ratios, and ingredient inventory belongs to the host.
- `ColourKnowledge.java`: a painter may be a player or companion, knowledge starts
  empty and correct strokes teach it. Its threshold is proposed for owner tuning.
- `MuralRestorationAdapter` records activity facts. Receipt participant IDs do not
  define which account/profile owns pigment supplies or colour knowledge.

The native actor's `StartingPrimaries = 6` is explicitly a per-mural prototype
stand-in. It is not evidence for a player starter grant, copying supplies between
murals, or merging existing knowledge. A supplied, initially empty transient
caller context would match Java's dependency injection, but would remain unbound.
This change does not add such a context or default identity lookup.

The narrow decision still needed is how the host selects the authoritative
player/companion context and provides its existing supplies/knowledge, including
the fate of any actor-local prototype state. Ingredient debits, persistence and
rewards also remain outside this slice. Status: **pending contract decision**;
no implementation of that binding was attempted or denied.

## Independent progress-loss bug selected next

The previous native `Rebuild` replaced `Mural`, cleared awakening state, destroyed
all live cells and reset their colours before checking whether the new seed and
dimensions were valid. A false return therefore discarded restored-cell work,
while the palette still contained the costs of those strokes. Mutable public
Width/Height also meant simply retaining the old core would not preserve safe
indexing. `SetFromFrame` multiplied signed 32-bit sides before capping them.

Successful deliberate rebuilding is already documented to reset the painting to
grey while retaining palette and knowledge. That successful behavior is preserved.
The source fix makes ordinary refusal retain the committed mural instead:

- Validate seed, dimensions and finite positive cell size before touching live
  state. Numeric float conversion/span overflow is refused without new tuning
  limits. Frame sides are capped before multiplication, preserving the existing
  positive-size cap-to-12 behavior even for large integer inputs.
- Stage a candidate core, plane/material assets, unique-named hidden transient
  cell components and their grey materials. The actor retains staged components
  during preparation. A failed stage destroys/removes only prepared components.
- Commit core, cell arrays, public settings, panel transform and cell size only
  after all prepared cells register. On rejection, restore public settings from
  the active core and its committed cell size, keeping indexing consistent.
- Retain restored-cell data, pigments, knowledge, awakening state and light on
  failure. A successful explicit rebuild resets awakening and its old glow to
  zero, then reveals the replacement grey cells.
- Preserve the original void `SetFromFrame` API. Add `TrySetFromFrame` for callers
  that need a boolean outcome; no caller or shared interaction file changes.

This is in-memory failure handling. It introduces no save format, identity,
starter grant, ownership, reward, new ability or inventory policy. It does not
promise recovery from a fatal process/OOM failure or implement disk persistence.

## Exact changed files

Under `engines/unreal/DaedalusLink/Source/DaedalusLink/`:

- `Public/DaedalusLivingPainting.h` (reserved actor declarations)
- `Private/DaedalusLivingPainting.cpp` (reserved rebuild/frame operations)
- `Public/DaedalusMuralLayoutCore.h` (new portable input/layout validation)

Other additions:

- `engines/unreal/core-test/mural_layout_core_test.cpp`
- `engines/unreal/core-test/run_mural_layout_core.cmd`
- `docs/production/GALLERY-MURAL-REBUILD-20261023.md` (this handoff)

Gallery viewer, mural control and Portal checkpoints are preserved. No Hero,
Speak, Talker, dialogue, Slate, NPC, RecordHunt, shared placement/Look mode, arcade,
Prismheart, pirate/Ocean/Orrery, inventory or ingestion files are changed.

## Evidence and next acceptance

The small standalone test executes the actual portable layout helper used by the
native actor. It covers layout/seed bounds, invalid numeric sizes, representable
float geometry, safe frame conversion and unchanged output on conversion refusal.
It does **not** execute the native rebuild, UObject/component lifetime,
registration, material code or progression-preservation behavior.

```text
engines\unreal\core-test\run_mural_layout_core.cmd <scratch-output-directory>
```

The actual layout header compiled with MSVC C++17 `/W4 /WX` and passed **30/30**
checks. The fresh guard before that single small compile reported **4.92 GiB
free**, above the 3 GiB minimum. Focused source preflight reported zero errors in
the three changed/new implementation files. Targeted source review checked
staging, lifetime retention/cleanup, public-setting rollback, safe conversion and
commit ordering. These are offline checks; they do not execute the native actor.

Native/UHT compilation and gameplay remain unverified. No editor, live project,
engine build, push or merge was used.

After editor access is released, compile the module and partially restore a mural.
Try invalid seed/dimensions, NaN/zero/invalid cell size and invalid frame sides.
Verify the exact progress, colours, palette, knowledge, active settings, panel and
glow survive rejection; then paint/wash another cell to exercise indexing. Check
missing-material/failed-preparation handling in a controlled native fixture and
confirm no orphaned staged components. Successfully rebuild an awakened mural:
it must become grey with zero glow while retaining palette/knowledge. Verify the
existing control console can continue on the committed layout. These runtime
checks are pending ingestion's exclusive editor access.

Next source priority remains the explicit painter-context contract decision;
this safety fix avoids inventing it. Shared placement/Look-mode integration and
reward authority remain reserved to their owners.

## Lessons learned

Retaining a core object is insufficient if mutable presentation fields still
index its arrays. Roll back the committed settings with the state. Native staging
also needs unique UObject names and hidden, retained transient components; reusing
a live Outer/name can replace an object before the intended commit point.
