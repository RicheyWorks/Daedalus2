# SHORE01 — Keystone Shore (contest G108)

*Code: `daedalus-core/src/main/java/com/daedalus/world/battlefield/KeystoneShore.java` (tests: `KeystoneShoreTest`, 10).*

## The lore

On the island's rocky shore, the Tidewife keeps a ledger with one rule written on the first page: *"Take the bait, but leave the stars."*
The fishers need ochre sea stars as bait for the deep lines. The stars, though, are the only thing on the shore that eats
mussels. If they are all taken, the mussels creep down and across the rock, smother the barnacles, and shade out the kelp.
A rich shore turns into a black mussel bed. This is Robert Paine's 1960s keystone experiment at Mukkaw Bay, played as a quest.

## The quest: *The Tidewife's Ledger*

1. The Tidewife asks for **two sea stars** of bait (`baitGoal`) for the fishers.
2. Pick how many stars to take before the run (`harvest(n)`). The shore then plays out over 30 years.
3. **DIVERSE**: barnacles, mussels and kelp each cover at least 6% of the rock *and* the bait was delivered. The ledger is
   signed and the Tidewife gives you the Kelp Cloak.
4. **MUSSEL_BED**: mussels cover 60% or more. The kelp is gone, and the Kelp Cloak can never be woven.
5. **THIN**: anything else. That includes refusing all bait, so the shore is fine but the island goes without.

## The model (one year)

| Step | Rule |
|---|---|
| Settlement | Bare cells in a species' zone settle with chance `settle` (mussels are tried first). Barnacles live in the top half, mussels from row h/3 to h−h/4, kelp in the bottom half. |
| Overgrowth | Each mussel overgrows each orthogonal barnacle or kelp neighbour with chance `overgrow`. |
| Predation | Stars × `starAppetite` mussel cells are eaten, starting from the lowest row, within the lower `starReach` share of the shore. |
| Storms | With chance `stormChance`, a `stormPatch`² square is scoured bare. |

Every draw comes from a splitmix hash of (seed, year, cell, salt), so the bait plan never shifts the dice.

`Settings.DEFAULT = (16, 12, 30, 6, 6, 0.7, 0.3, 0.25, 0.3, 3, 0.06, 0.6, 2)`

| Stars taken (of 6) | Typical result (seeds 1–5) |
|---|---|
| 0 | three species, but no bait → THIN |
| 2 | barnacles 7–12%, mussels ~30%, kelp ~40% → DIVERSE |
| 4 | barnacles squeezed under 6% → THIN |
| 6 | mussels 88–95% → MUSSEL_BED |

## Daedalus tie-ins

- `Report.band(i)`: a kelp cell maps to `Vegetation.WETLAND` and bare or shelled rock to `Vegetation.BARE`, so the shore
  can be painted on the battlefield ecology grid.
- **SALMON01**: the kelp at the river mouth is where smolts shelter. A mussel bed is a poor nursery.
- **CASCADE01**: the same lesson as the wolves, with one top predator holding a whole system open, told for the tide line.

## Unreal / Blender

- `Mob_Shore_SeaStar` (ochre/purple, 5 arms, Idle/Creep).
- `Prop_Shore_Rock` tiles with `SOCKET_Cell_00..`, plus clumps `Prop_Shore_Barnacles`, `Prop_Shore_MusselBed`,
  `Prop_Shore_Kelp`.
- `MI_Shore_<Rock|Barnacle|Mussel|Kelp>_<Wet|Dry>`. The tide line drives the Wet/Dry swap.
