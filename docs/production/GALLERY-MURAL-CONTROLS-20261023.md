# Gallery City local mural controls — 2026-10-23

## Source contract

`docs/mechanics/GAL01-LIVING-PAINTINGS.md` explicitly lists **cell highlights** as
pending. It describes choosing pigments, painting individual cells, washing
smudges, mixing secondary colours after learning their primaries, and asking
Prism Sight for a colour hint. Its proposed thresholds, quantities, ability
effects and awards remain owner decisions; this slice changes none of them.

The existing `ADaedalusLivingPainting` already exposes `Paint`, `Wash`, `Mix`,
`Reveal`, `Units`, `Knows` and `ProgressPm`. Its ordinary `Use` always chooses the
first unrestored cell with the editor/Blueprint `SelectedPigment`. Its mixing
and hint APIs have no native player control outside Blueprint/console entry
points. The selected source gap is therefore a local control/presentation
surface for these existing operations, rather than another gameplay rules port.

## Added behavior

An explicitly placed `ADaedalusMuralRestorationConsole` references one existing
living painting. The console outlines its selected cell with a white border and
shows the cell, selected colour and remaining units, all six supplies, learned
colours, restoration percentage and the last result in plain language. Using the
console paints that specific cell through the painting's existing `Paint` method.

Explicitly placed `ADaedalusMuralToolButton` actors reference the console. Their
configurable actions are next/previous cell, next/previous pigment, mix selected
pigment, wash selected cell and ask Prism Sight. They use the established
`ADaedalusUsable` E / X interface. There are no new input bindings, automatic
spawns or changes to Hero or shared interaction dispatch. A level owner can place
only the controls needed for a particular prototype setup.

Cell browsing follows row-major order and wraps; it does not skip or reveal
unrestored cells. Pigment selection follows the existing six-colour enum and
updates the painting's existing `SelectedPigment` preference. Navigation consumes
no supplies and does not paint, learn or reset the mural. Mixing and washing
delegate to the existing rules, with readable refusal feedback. The console
does not provide Grind: that prototype API does not debit ingredients, and this
slice does not invent ingredient handling or a free-supply station.

Hints are obtained **only** through the painting's existing `Reveal` method.
There is no hidden target/palette-mask access. A refused hint clears previous
hint text. Changing cell, pigment, frame seed, dimensions or target painting also
clears it, as do stroke and awakening notifications. The white focus border
contains no information about the required colour.

Target replacement/destroy/end-play unbind delegates and detach/hide the border.
The console refreshes on actions and existing stroke/awakening events, plus one
UObject-bound next-tick refresh to settle differing BeginPlay order. It has no
recurring tick. Arbitrary external property changes are revalidated on the next
action/refresh; changing the painting's configuration still requires its existing
`Rebuild` contract. This console never calls `Rebuild` or resets progress.

## Ownership and exact additions

No existing actor/core or shared file is changed. Additions under
`engines/unreal/DaedalusLink/Source/DaedalusLink/`:

- `Public/DaedalusMuralToolCore.h`: portable local selection, bounds and wrapping.
- `Public/DaedalusMuralRestorationConsole.h`: console/tool-button declarations.
- `Private/DaedalusMuralRestorationConsole.cpp`: native controls and presentation.

Other additions:

- `engines/unreal/core-test/mural_tool_core_test.cpp`
- `engines/unreal/core-test/run_mural_tools_core.cmd`
- `docs/production/GALLERY-MURAL-CONTROLS-20261023.md` (this handoff)

All Gallery viewer and Portal checkpoints are preserved. RecordHunt, NPCs,
dialogue, Slate, Hero, shared Look-mode/placement, inventory/profile authority,
pirate/Ocean/Orrery behavior, arcade/minigames and Prismheart files are untouched.
The Orrery header is only reused for its existing usable base class.

## Important prototype limit

These are **local prototype controls**, not completed realm progression.
The existing mural actor owns a separate palette and colour knowledge per mural,
whereas Java's painting accepts caller-owned painter knowledge. The existing
parity fixture includes seed **317395817**, size **5 × 9**, containing only
ORANGE and VIOLET. Its fresh per-actor knowledge cannot learn Red and Blue from
that mural, so it cannot unlock violet mixing from its starting primary supplies.
The controls expose this refusal; they do not grant colours or bypass knowledge.

Sharing painter knowledge/supplies across murals requires coordination with the
existing painting owner and a host/profile/inventory contract. No player identity,
session store, disk save, reward, creature spawn, threshold or economy change is
introduced here. No restart persistence or universal seed solvability is claimed.

The next prioritized source task is to settle that caller-owned painter context
before changing `Public/DaedalusLivingPainting.h` and
`Private/DaedalusLivingPainting.cpp` (especially `Use`, `Paint`, `Mix`, `Reveal`,
`Units` and `Knows`). Those files are unchanged here. Its status is **pending
ownership/contract coordination**, not a denied operation. Shared Look-mode and
placement integration also remain pending; this slice does not implement either.

## Integration and acceptance

After editor access is released, compile/UHT the native source, place a living
painting plus console, assign `Painting`, and place tool buttons with `Console`
and `Action`. Labels face local +X. Place buttons with enough separation for the
existing nearest-usable interaction to select each one, and verify their reach
against the mural itself. Nothing automatically adds these actors to a realm.

Public `SelectCell(X,Y)` uses zero-based coordinates; player labels are one-based.
The border follows the existing painting actor's exact root-local cell geometry.
Verify row/column orientation, transform/scale, text legibility, border material
and packaged cooking in native play. Verify paint/smudge/wash, empty supplies,
primary/locked/full/missing-input mixing refusals, gated hints, hint clearing,
target replacement/destruction and both BeginPlay orders. A complete-realm
progression check must wait for the separate painter/profile dependency.

The small standalone test executes the actual portable selection header only.
It covers configuration bounds, identity reset/preservation, cell/pigment cycles,
invalid inputs, detached selection and signed 64-bit extremes. It does not execute
the native adapter, painting methods, delegates, material, timer, input or hints.
Focused source review separately checks delegation, enum bounds and hint gating.

```text
engines\unreal\core-test\run_mural_tools_core.cmd <scratch-output-directory>
```

The actual portable focus header compiled with MSVC C++17 `/W4 /WX` and passed
**31/31 checks**. The fresh resource guard reported **5.50 GiB free** before the
single small compile (minimum 3 GiB). Focused source preflight reported zero
errors in the three new implementation files. Targeted source review caught
BeginPlay ordering, stale-hint identity and external-stroke feedback edges; the
new console addresses those in source. These checks do not execute native code.

Unreal/UHT compilation and runtime
acceptance remain pending under the ingestion restrictions. No editor, live
project activation, heavy build, network request, push or merge was performed.

## Lessons learned

The portable painting already had its rules, but the native prototype's fixed
first-cell/red interaction hid most of them. A local control surface can expose
the specified operations without rewriting those rules or touching shared input.
Also, a stroke delegate without pigment identity cannot support a colour-specific
empty-pot message for another caller: only the console's own Paint result may name
that colour. Preserve that distinction in future multiplayer/profile integration.
