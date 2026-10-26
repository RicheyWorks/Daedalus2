# GAL01 Living paintings and colour knowledge

Contest gap **G13** (minigame contest 2026-10-19, owner 2hot2trot). Mechanics sheet row GAL01, "Living paintings
and colour knowledge", was "art validated; abilities proposed". This adds the rules as a source-only Java core next
to `GalleryOps`. All numbers are **proposed** and need owner tuning. No Unreal editor work was done.

Code: `daedalus-core/src/main/java/com/daedalus/world/gallery/`
(`Pigment`, `PigmentPalette`, `ColourKnowledge`, `LivingPainting`, `MuralRestorationAdapter`), with tests in the
matching test package (`LivingPaintingTest`, `ColourKnowledgeTest`).

## Story tie-in

The Grey Wash (the colour-draining boss proposal in the Gallery creature kit) has drained the city's murals. Every
mural still remembers its colours. Players and their companions grind pigments from Gallery City chemistry, then
repaint the murals cell by cell. Painting teaches colour, and a colour you know becomes useful in the city. When a
mural is fully restored it comes alive: its subject steps out as a friendly Gallery creature (Paper Crane, Prism
Finch, Crayon Gecko, Inkpup, Lamp Moth or Brushtail Squirrel from the existing creature kit).

## Pigments come from realm chemistry

| Pigment | Ground from (Chemistry sheet, GALLERY-CITY) | Mixed from |
| --- | --- | --- |
| RED | beet, cherry | - |
| YELLOW | dawnleaf | - |
| BLUE | cobalt | - |
| ORANGE | orange | RED + YELLOW |
| GREEN | copper (verdigris) | YELLOW + BLUE |
| VIOLET | - | RED + BLUE |

`PigmentPalette.grind(ingredient)` turns one ingredient into one unit. `mix(secondary, knowledge)` spends one unit of
each primary, but only once the painter **knows** both primaries.

## Living painting rules

- A mural is `width x height` cells (1..12 each). `LivingPainting.forFrame(frame)` uses a `GalleryOps.Frame`'s own
  seed and gives 2x2 cells per wall cube, so each gallery frame has one stable mural that every client restores the
  same way.
- The seed picks a palette of 2..4 colours and each cell's colour. No clock and no global random are used.
- `paint` with the right pigment restores the cell and teaches that colour. The wrong pigment is still spent and
  **smudges** the cell (a Smudgeling stirs); a smudged cell needs `wash` (turpentine) before it can be repainted.
- States: `DRAINED` -> `RESTORING` -> `LIVING` (every cell restored). `progressPm()` is per-mille progress.

## Colour knowledge (make colour useful)

A painter knows a colour after `KNOW_AT = 3` correct strokes. Knowledge is never lost; smudges cost pigment only.

| Ability | Needs | Use in the city (proposed) |
| --- | --- | --- |
| EMBER_LANTERN | RED | warm lantern that keeps the Grey Wash off a cell for a while |
| CANAL_TINT | BLUE | tint canals and fountains so canal routes show on the map |
| SUNWASH | YELLOW | brighten dim galleries so hidden frames are seen |
| TRELLIS_VINE | GREEN | grow a climbable painted vine on a frame street |
| DUSK_READING | VIOLET | read the curator's dusk inscriptions (GAL03 proof notes) |
| PRISM_SIGHT | RED + YELLOW + BLUE | split light through a colour prism to reveal the colour a grey cell needs |

`LivingPainting.reveal` refuses to answer unless the painter has PRISM_SIGHT, so a host cannot leak the solution.

## Progression (G12 tie-in)

`MuralRestorationAdapter` is a G12 `ActivityResultAdapter` (activity `gallery.mural-restoration`). Companions that
helped (profiles animal, bird, social_insect; roles restoration, carrying, observation) are credited once per
session through `ActivityResultReceipt` and `ProgressionLedger`. Measures: `cells_restored`, `smudges`,
`colours_used`, `mural_living`. A fully restored mural is `COMPLETED`; a session that ends before the mural wakes is
`FAILED` (still settleable for partial work if a policy allows); leaving is `ABANDONED` and pays nothing.

## Still pending (not in this change)

- Unreal: the painting actor, cell highlights and the subject's walk-out animation (UNREAL-QUEUE, after landing).
- Art: a "grey" material variant for `Prop_Gallery_MuralPanel` and pigment pots (BLENDER-ASKS if wanted).
- Owner decisions: thresholds, palette sizes, ability effects and award policy numbers.
