# Super Island: connected plots and the Blender exemplar

Owner direction, 14 October 2026: build one exceptional island, a second reusable
island template, and a four-island composition. **A Super Island is four or more
distinct connected islands.** People can use ships to bring purchased plots
together. This document defines the art and geometry standard for that package.
The Blender generator and actual artifact manifest record what was produced.

**Two or three islands may connect as an ordinary island group.** They become
a Super Island only at **four or more distinct, connected members**. A bridge
can connect any compatible pair; the reusable Super Island layout helper
deliberately requires at least four members. Its `is_super_island()` predicate
validates distinct labels and checks the count threshold; connectivity remains
a separate requirement.

## The three deliverables

1. **Lumenwake Sanctuary, showcase island:** an authored environment that sets the crew's target for
   composition, material finish and detail. Retain editable terrain, vegetation,
   buildings, water and lighting in separate collections.
2. **Riverjoin Commons, connectable template island:** a complete attractive island with explicit
   connection sockets, clear building areas, an independent tow anchor and a
   readable route. Its socket contract is reusable across realm palettes.
3. **Lumenwake Super Island:** a 2 by 2 assembly showing four independent land
   roots, four identifiers, connector pieces and a visible sky-ship tug example.
   Its four local plot labels are `DEMO-A`, `DEMO-B`, `DEMO-C` and `DEMO-D`.
   Further islands attach using the same sockets. Reusing template geometry does
   not make different deeds the same island.

These are an art/source commission. The example names and identifiers are local
authoring labels; a render or a `.blend` does not allocate a live parcel or mint a
token. The authoritative realm ledger and ownership service supply live IDs.

## Evidence used

- [Visual quality bar](C:/Users/730ri/.codex/worktrees/island-mesh-pool/Daedalus2/docs/production/VISUAL-QUALITY-BAR.md),
  published in PR140 at `da716327`: Adopt Me is the owner's minimum; finish one
  strong exemplar before multiplying variants. Its 17-image board is in the
  adjacent `reference/visual-benchmark-20261014/` directory. The main checkout did
  not yet contain that document when this audit ran.
- [Blender team brief](../BLENDER-TEAM-BRIEF.md): blocky geometry, metre scale,
  export naming, bottom-centre pivots, material and triangle contracts.
- [ADR-050](../adr/ADR-050-lands.md): shattered planetary fragments, layered
  mineable earth, winding caves, lake/stream/waterfall, ark dock and unmineable
  glowing Heartstone. Today's generated land can be 92 m across and 46 m deep.
- [ADR-065](C:/Users/730ri/.codex/worktrees/java-land-grid/Daedalus2/docs/adr/ADR-065-ten-thousand-lands-per-realm.md)
  remains proposed: 100 by 100 grid, 256 m pitch, 10 by 10 cell districts,
  immutable `(realm, number)`, independently saved placement, 240 m growth
  envelope, and identity-preserving tugging.
- [Realm layout store](C:/Users/730ri/.codex/worktrees/realm-land-api/Daedalus2/docs/production/REALM-LAYOUT-STORE.md)
  implements placement, reserved cells, revisions and identity-preserving moves.
  [Realm land API](C:/Users/730ri/.codex/worktrees/realm-land-api/Daedalus2/docs/production/REALM-LAND-API.md)
  documents named east/north coordinates and placement reads. Neither establishes
  wallet ownership or sale availability.
- [ADR-051](../adr/ADR-051-art-queue.md): the existing shared art queue and native
  ingestion pipeline. Blender source, exports, native imports, placement and
  saved maps are separate delivery stages.

## Art direction and the exemplar bar

Create a welcoming floating shard with an unmistakable silhouette: terraced
green ground above exposed fractured stone, a luminous Heartstone underneath,
one principal landmark and supporting lived-in clusters. Use original designs.
The showcase should feel authored from the arrival dock to its highest overlook.

Use the existing realm styles: warm storybook adventure; Gallery City's framed
art and sculpture; Parcels' orchards and fenced fields; Brick Realm's baseplates;
the Labyrinth's charcoal/violet stone and warm lanterns; underwater sea-glass and
coral; practical weathered Hearthwake materials. Shared socket geometry can
coexist with distinct local architecture, planting and palettes.

The principal landmark establishes the skyline. Place smaller structures at
different elevations, with intentional views between them. Group trees into
groves that frame the walking route. Mix canopy sizes, trunk angles and planted
understorey instead of spreading identical trees at regular intervals. Flowers
belong in beds, shoreline drifts and garden edges. Include quiet clearings with a
purpose, such as an overlook, building lawn or social space.

Give water a readable source, basin, outlet, stream bed, brink and waterfall.
Fit banks to the water; use restrained foam where current or drops justify it.
The fall should break into changing ribbons or droplets as it leaves the cliff,
with the floating-world destination visible below. Keep warm stone and timber
distinct from cool water and glowing crystal. Control emission and atmospheric
dust so they support the landmark and do not hide the terrain.

Fix the defects identified in the Copper Beacon review: empty flat terrain,
unstructured flower dots, repetitive planting, trees intersecting the cottage,
a rigid waterfall ribbon, and intersecting dock boards. Keep prior creator
assets and scene revisions intact; this commission adds its own names and files.

An aerial hero image is one view of the standard. Inspect a dock arrival at
player height, a route to the landmark, a shoreline close-up, the connection
joint and the underside. Render both day and dusk. Stills demonstrate visual
appearance; movement, collision and frame rate require later native evidence.

## Reusable plot dimensions

The following is a **proposed Blender assembly profile**, aligned with the newer
grid design. Record any changed values in the scene manifest rather than silently
scaling exports. It does not enlarge the live 92 m land generator.

| Property | Assembly profile | Reason |
|---|---:|---|
| Blender unit | 1 m | Matches one gameplay cube |
| Plot cell pitch | 256 m | Matches the recorded realm grid |
| Mature land envelope | 240 by 240 m | Leaves 8 m per cell edge for sky and connector interfaces |
| Local land centre | `(east=0, north=0)` | Keeps placement independent from immutable identity |
| Connector socket reach | 120 m from local centre | Matches the mature envelope |
| Adjacent socket separation | 16 m | `256 - 240` |
| Two by two cell footprint | 512 by 512 m | Four distinct adjacent cells |
| Two by two mature land extent | 496 by 496 m | `240 + 256`, before connector trim |
| Launch terrain envelope | 92 by 92 m | Existing generator; needs longer approach spans at the same pitch |
| District footprint limit | Keep inside one 10 by 10 district for initial adapter | Matches existing estate placement constraints |

Choose one scene route datum and one water datum. Store their exact heights in
the manifest and on every socket. The Lumenwake package uses a 10 m path
deck relative to the plot's authored zero plane. The authored water channel
height is recorded separately by the generator. Local
hills and terraces may rise above the deck; graded approaches bring routes back
to the datum before a connection. Water connectors are separate from paths.
An island that lacks a matching water socket joins by bridge alone.

The group root is a logical placement origin. Each exported prop/building keeps
the brief's bottom-centre pivot. Do not move individual export pivots merely to
make the whole island's group root coincide with the lowest stone.

## Connection sockets and seams

Place named local cardinal sockets:

| Socket | Local east/north position | Outward direction |
|---|---|---|
| `Connect_E` | `(120, 0)` m | east |
| `Connect_N` | `(0, 120)` m | north |
| `Connect_W` | `(-120, 0)` m | west |
| `Connect_S` | `(0, -120)` m | south |

Each socket stores its plot label, local transform, path height, clear width,
water height if present, connector profile version and current connection state.
Lumenwake's pedestrian clear width is 8 m, with a 12 m dressed landing.
Keep tall foliage and props out of the landing. Record dimensions on the actual
authored socket; these are proposed art values, not existing engine limits.

Keep terrain and connectors as separate meshes. Extend a path to its local
landing, then span the 16 m space with one connector piece. Fit the deck to both
landings and leave a visible intentional join line or expansion strip. Avoid
coplanar stacked surfaces and repeated posts on the same vertex. Connector
geometry must not silently alter another plot's soil or collision.

Use three compatible connector styles:

- A timber or stone bridge across a retained sky channel.
- A dressed earth causeway with stone side walls, distinct from the owned soil.
- A water flume/aqueduct beside a separate pedestrian deck, only where inlet and
  outlet elevations and flow direction agree.

At four-way intersections, retain a deliberate sky/water cross or add a separately
identified connector commons. Four touching plots must still read as a connected
place with individual histories. Carry paths, railing rhythm and palette through
the joints without cloning every landmark. A prominent landmark on the showcase
plot is balanced by an orchard, lake garden and buildable meadow on the others.

For a compact 2 by 2 assembly, land-root centres are `(-128,-128)`, `(128,-128)`,
`(-128,128)` and `(128,128)` metres in group space. Rotation is allowed in
quarter-turn increments for the template; transform its socket directions and
authored approaches together. Mirror geometry only when front direction, water
flow and building access remain meaningful.

The reusable source helper is
[`tools/blender/super_island_layout.py`](../../tools/blender/super_island_layout.py).
It has no Blender dependency or import-time operations. `layout_plots()` creates
row-major groups of any size from four upwards and centres the occupied bounding
box. Partial final rows remain connected through cardinal neighbours. The
returned `plots`, `memberIDs`, `connectors`, socket endpoints, metric bounds and
adjacency graph let the Blender authoring recipe place distinct roots and draw
their bridges using the same dimensions.

Examples to use from a Python or Blender script with `tools/blender` on its import
path:

```python
from super_island_layout import layout_plots, layout_cells

four = layout_plots(["DEMO-A", "DEMO-B", "DEMO-C", "DEMO-D"])
five = layout_plots([f"DEMO-{i + 1}" for i in range(5)], columns=2)
six = layout_plots([f"DEMO-{i + 1}" for i in range(6)], columns=2)
nine = layout_plots([f"DEMO-{i + 1}" for i in range(9)], columns=3)
l_shape = layout_cells(
    ["DEMO-A", "DEMO-B", "DEMO-C", "DEMO-D"],
    [(0, 0), (1, 0), (0, 1), (0, 2)],
)

for plot in nine["plots"]:
    # Append the appropriate editable collection, then place its member root.
    member_label = plot["plot"]
    root_position_metres = plot["position"]
for connector in nine["connectors"]:
    start_metres, end_metres = connector["start"], connector["end"]
    deck_length_metres = connector["length"]
    deck_width_metres = connector["walkWidth"]
```

The helper refuses fewer than four members, duplicate/blank labels, repeated
cells, nonfinite profile values, invalid dimensions and disconnected manual
groups. Every result is labelled `AUTHORING_GEOMETRY_ONLY`. A caller still needs
the future authenticated group authority before applying these example layouts
to purchased land. The helper's source was written without running a separate
test suite under the current deferred-testing instruction.

## Identity, ownership and Super Island grouping

Each member retains its original immutable `(realm, landNumber)`, seed, owner,
builder permissions and edits. Store current placement separately. A group may
reference four or more members and connection edges; a group label must not
replace their deeds. The example artifact uses local labels for its four roots.

ADR-065 also describes a larger **estate** sold as one deed. That existing
single-deed concept is different from this newly requested group of four or
more independently purchased islands. A visually identical 2 by 2 assembly
could represent either arrangement; the authoritative records must distinguish
them. Do not reissue, burn, collapse or renumber member deeds through an art build.

Treat connectors as separately tracked structures with explicit participating
plots and build/remove permission. A cross-plot bridge does not grant build
permission on the neighbour's land. Shared-owner islands can connect after the
authority verifies all members; mixed owners require agreement for the affected
members. Disconnection removes the relevant links while preserving each island.

The server/layout adapter still needs an authenticated grouping and tug contract.
The current placement API is read-only and carries no wallet owner. The Blender
manifest can demonstrate the proposed geometry and grouping without presenting
it as deployed multiplayer functionality.

## Ship tug presentation and movement design

Give every island its own visible tow anchor below the shore, outside the walking
route and away from the waterfall. A distinct anchor empty records its local
position and grapple direction. Use the original ark concept: approximately
20 m hull with a large separate front claw, sails or balloons. Reserve a clear
approach corridor; a proposed starting clearance is 30 m wide by 60 m long,
recorded in the scene metadata.

The visual sequence is: arrive and align, attach claw/cable, retract connectors,
move the entire plot root, slow near the destination, align compatible sockets,
lock the plot transform, restore connectors, detach the cable. Land, buildings,
water, flora and contained props travel together under the same root. Ropes
should sag slightly and avoid clipping the hull, trees and fractured stone.

The eventual authority checks owner permission, reserved cells, district/grid
bounds, footprint collision, conflicting moves and destination vacancy before
committing an identity-preserving move. Swaps need both owners' agreement. A
failed or cancelled tug restores the last committed placement. Source animation
or a posed tug vessel demonstrates the concept; it does not prove that these
server mechanics already exist.

## Source, export and presentation package

The generator source is `tools/blender/lumenwake_islands.py`; artifact output is
`artifacts/islands/lumenwake/`. Use its actual manifest for exact filenames and
completed render/export stages. The original vector
[Connection Standard blueprint](../../artifacts/islands/lumenwake/Connection_Standard.svg)
shows the four member roots, envelopes, socket gap, walking width, deck datum
and the distinction between ordinary groups and Super Islands.
The intended user-facing package contains:

- Editable Blender scenes for the showcase, connectable template and four-plot
  composition, with named plot roots and grouped terrain/water/props.
- Day and dusk hero renders, a template plan view, an assembly overview, a
  connection detail and at least one player-height showcase view.
- The reproducible Blender generator/recipe, exact source hashes and a manifest
  of units, plot labels, member transforms, sockets, art dimensions and exports.
- GLB single-island and kit delivery meshes separated by role for reuse. Exports are listed only when
  actually produced; preview-only shaders and helpers are identified separately.
- A handoff note identifying inspected visual views and remaining native steps.

Continue using the existing art pipeline. Export one collection per named asset,
apply scale, face the asset toward Blender -Y, and keep 1–3 flat-colour/vertex-colour
material slots per native delivery asset. Budget props at 3,000 triangles,
creatures at 6,000, vehicles at 12,000 and buildings at 15,000. A full multi-plot
presentation scene has many such assets; measure its own total independently.
Procedural Blender preview shaders do not establish equivalent Unreal materials.

Work headlessly/offline within the current machine limits and shared owner turns.
Preserve resource settings, existing saved islands and source provenance. The
14 October board records 32 GB RAM and 22 GB pagefile as team-reported limits,
and identifies another crew as the sole active Unreal editor operator. This
commission does not require taking that editor. Queue the strongest reviewed
delivery assets for the acknowledged ingestion owner with exact artifact hashes.

Separate statuses: source saved, render inspected, export written, native imported,
native placed, map saved and gameplay accepted. Report the actual stage reached.
Tests remain deferred under the user's current instruction; authored renders and
visual inspection are part of producing the requested Blender artwork.
