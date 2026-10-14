# Lumenwake island standard

The user commissioned an original Blender showcase, a second reusable island,
and four connected purchased plots as a Super Island. This package is the crew's
visual and authoring reference: **four or more distinct connected plots form a
Super Island**. Two or three connected plots are ordinary groups.

## Open the delivered work

The complete local package lives in `artifacts/islands/lumenwake/`.

| Deliverable | Editable source | Purpose |
|---|---|---|
| Lumenwake Sanctuary | `final/Lumenwake_Sanctuary.blend` | Copper observatory, ivory beacon, a lived-in workshop village, medicinal garden, planted groves, spring, lagoon, waterfall and exposed Heartstone |
| Riverjoin Commons | `template-final/Riverjoin_Commons.blend` | Orchardkeeper's cottage, public cistern, boathouse/workshop, central water and open building areas, four connection mouths and a tug pose |
| Lumenwake Super Island | `super-final/Lumenwake_Super_Island.blend` | One Sanctuary and three oriented Commons modules under four independent plot roots, with four physical bridge connectors |

Each source has a matching GLB and an exact production manifest. `index.html`
shows the actual Blender images. `Lumenwake_Standard_Package.zip` collects the
three unique editable scenes, exports, views, recipes, design and blueprint.
`Lumenwake_Package_Manifest.json` records the final artifact hashes and measured
geometry. Earlier revisions stay outside the delivery ZIP.

These are original mesh/curve environments, rendered in actual Blender 4.3.1
using Cycles CPU with four threads and 48 samples. No image textures or generated
bitmap mockups stand in for the models. The compressed `.blend` sources retain
editable modifiers, curves, materials and organized collections. Export copies
bake modifiers and curves and carry plot, socket and tow-anchor metadata.

## What the crew should aim for

The visual bar was read from the published `VISUAL-QUALITY-BAR.md` in the
`island-mesh-pool` worktree. The detailed source citations and realm palettes are
in [Super Island design](SUPER-ISLAND-DESIGN.md).

Make the skyline memorable before adding variants. The Sanctuary combines a
single principal observatory, a supporting beacon, small architectural clusters,
different ground elevations and deliberate groves. Leaf crowns, willow curtains,
flower beds, ferns, meadow blades and stone ledges are actual geometry. Water has
a spring, basin, outlet and falling flow; the Heartstone belongs beneath the
fractured shard. The Commons keeps room for subsequent owner builds while
demonstrating compatible approaches and repeated use of the same template.

Production visual inspection led to concrete revisions: water clips against the
same explicit terrain triangles; shore colour varies continuously by vertex;
paths sample their terrain densely; the Sanctuary waterfront has a level terrace
and supported stream crossing; the observatory has a fitted switchback stair,
continuous stringers, closed risers, piers and handrails; shared workshop route
legs are emitted once; detail cameras sit above nearby canopies; connector posts
have outer sills and transverse brackets.

Inspect the day/dusk overview, normal player-height approach, village detail,
template plan, group overview and bridge joint. Stills show the authored visual
appearance. The source's descriptive `walkable` roles do not establish collision,
navigation, movement acceptance or frame rate in the game.

## Build another connected plot

1. Duplicate the Commons plot collection into a new scene or append it from the
   editable source. Assign a fresh authoring label and retain a single named
   `PlotRoot`. Live IDs must come from the authoritative realm ledger.
2. Move and rotate the entire root, including terrain, buildings, water, plants,
   sockets and anchor. Quarter-turn rotations preserve the cardinal profile.
3. Keep the E/N/W/S mouths clear. Use a 240 m mature art envelope, centres 256 m
   apart, sockets at local coordinates ±120 m, an 8 m clear walking width and
   nominal 10 m deck datum. The authored board surface is 10.065 m.
4. Span the 16 m gap between adjacent compatible sockets with a separate bridge
   collection. Keep its posts, rails, sills and truss together; joining does not
   change either island's ground or deed.
5. Preserve each member's identity, seed, edits, permissions and ownership. Store
   placement and connection edges separately. A connected group reaches the
   Super Island classification when it contains at least four distinct members.

The delivered 2×2 group uses `DEMO-A/B/C/D`, root centres `(-128,-128)`,
`(128,-128)`, `(-128,128)` and `(128,128)` metres, and rotations 0°, 0°, 90° and
180°. Its mature land extent is 496×496 m inside four 256 m cells. These are local
authoring examples; no NFT, wallet, ownership or allocation record was changed.
The mature 240 m profile illustrates the proposed growth tier. It does not
silently resize deployed 92 m starter lands.

[`super_island_layout.py`](../../tools/blender/super_island_layout.py) derives
member transforms, cardinal sockets, graph edges, bridge endpoints and bounds
for 4+ plots. Its pure count predicate is separate from its connectivity check.
`--plots 5 --columns 2`, `--plots 6 --columns 2` or `--plots 9 --columns 3` use the
same profile. Manual connected cell layouts are also supported by the helper.

## Reproduce and hand off

Use Blender background mode in a fresh output directory; the authoring recipe
refuses to replace existing scenes or silently change a recipe snapshot. The
four recipe files in each stage's `recipe-source` are its exact production inputs.
Use the same directory for the hero/template sources before building a group,
or copy those two input `.blend` files into a fresh group directory. Input copies
are omitted from the ZIP because the unique editable sources are already present.

```powershell
& 'C:\Program Files\Blender Foundation\Blender 4.3\blender.exe' --background --factory-startup --threads 4 --python tools/blender/lumenwake_islands.py -- --output artifacts/islands/lumenwake/new-version --build hero --render
& 'C:\Program Files\Blender Foundation\Blender 4.3\blender.exe' --background --factory-startup --threads 4 --python tools/blender/lumenwake_islands.py -- --output artifacts/islands/lumenwake/new-version --build template --render
& 'C:\Program Files\Blender Foundation\Blender 4.3\blender.exe' --background --factory-startup --threads 4 --python tools/blender/lumenwake_islands.py -- --output artifacts/islands/lumenwake/new-version --build super --plots 4 --columns 2 --render
```

Run one Blender authoring/render process at a time on this shared machine. The
art crew did not take the live Unreal editor or change OS/resource settings.
Poot Scoot's coordinator receives source claims and the exact completed packet.

The current stage is **Blender source saved, GLB exported, views rendered and
inspected**. Tests were deferred under the user's instruction. No native build,
Unreal import, map placement, server deployment or chain transaction was run.

The whole-island scenes are presentation/authoring models. Some terrain and
combined foliage meshes exceed the legacy individual prop/building triangle
budgets. Before native ingestion, the owning team needs a terrain-specific route
or role splitting, LODs, collision/navigation, material translation and actual
native visual/performance evidence. Do not mark these scenes accepted by the
legacy per-asset judge merely because their `.blend` and GLB exist.

The tug is a visual ark with a grounded mooring eye and a named anchor empty.
Live ship towing still needs owner checks, reservations, destination vacancy,
movement authority, collision and an atomic placement commit. The group retains
four separate deeds; a single-deed estate is a different authoritative concept.
