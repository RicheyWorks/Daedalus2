# Unicorn guide collection

500 static Blender variants built from the existing seven-part `Mob_Horse.glb`,
with a forehead horn, ears, mane and ten restrained pastel palettes. Fifty body
proportions per palette give 500 distinct palette/proportion combinations. This
is a modular variation collection, not 500 independently sculpted characters.
The original horse is read only. Shared meshes keep the Blender scene small.

Run in a **separate factory-startup background process** (the script clears its scene):

```text
blender --background --factory-startup --python tools/blender/unicorn_guides.py -- --source data/creatures/unicorn-guides/source/Mob_Horse.glb --output /absolute/output
python tools/blender/validate_unicorn_guides.py /absolute/output
```

Outputs: editable `unicorn-guides-500.blend`, 500 separately named GLBs exported
at the ground origin, `manifest.json`, `all-500.png`, `palette-preview.png`.
Meters, +Y forward after correcting the source horse's observed -Y orientation.
Preview-grid positions are display placement only and are not in the GLBs.
The manifest records source and output SHA-256 hashes and triangle counts.
Static meshes have no skeletal rig, animation clips, collision setup or NPC AI.
Do not spawn all 500 simultaneously: these are catalog variants, not a population budget.

The bundled source is an unchanged copy of the shared art library's horse so
generation does not depend on a teammate's local directory. Recorded evidence
is in `data/creatures/unicorn-guides/`. The completed run took 54.18 seconds,
including both renders; all 500 exports passed the existing pipeline GLB reader,
with 1,016 triangles each, three materials, distinct palette/proportion pairs,
verified source/output hashes and complete non-overlapping group membership.
Both rendered sheets were visually inspected. Live behavior remains unproven.

## User rules and explicit interpretation

- Friendly NPCs help, defend and point the player toward the appropriate rainbow.
- Ordinary unicorns fear and flee burning bulls. The mountain alpha stands its ground.
  Fear takes precedence over ordinary defense while that threat is present.
- 250 individuals form 125 male-female pairs. This interprets "50 percent" as
  individuals, **not** a 50% encounter probability. Spawn weighting is still pending.
- The other 250 are female-only: 73 ordinary herds totaling 238 individuals,
  plus the exceptional twelve-member quest herd. No all-male groups.
- Ordinary herd sizes: 16 pairs, 33 trios, 18 fours, three fives, two sixes and
  one eight. The eight is uncommon in the catalog; live rarity needs spawn weights.
- The twelve-member herd is the user's explicit exception to the usual maximum
  of eight. After driving ten burning bulls to the sea and finding that herd,
  the player receives a chest of the realm's strongest legendary items.

Provisional content assignment: `Mob_Unicorn_488` is the mountain alpha, a female
in the eight-member herd. Alpha sex and identity were not specified by the user;
this keeps the requested grouping intact and can be changed without changing rules.
The twelve quest members are IDs 489–500. Quest location and discovery frequency
are not specified. No final weapon names or stats are invented here.

## Unreal handoff (not implemented by these assets)

Reuse existing creature rendering/navigation and realm travel, keeping these
unicorns friendly rather than inheriting hostile mob behavior from a naming convention.
The owning host must verify ten distinct bull-to-sea events attributed to this
player, verify discovery of the designated twelve-member herd, and grant the
chest atomically. Persist progress; reject replayed events and repeated reward
requests. A one-time reward is the proposed anti-duplication default, pending
quest reset/repeatability design. Never trust a client-supplied bull count.

Acceptance: demonstrate friendly guidance, defense against another threat,
ordinary fear of a burning bull, the mountain alpha's exception, valid grouping,
and both quest conditions followed by the realm-specific legendary chest.
Blender generation and screenshots alone do not prove any of these behaviors.
