# The Warm Crates (Kennel Isle chapter, contest)

Owner: art-master-flex. Code: `daedalus-core/src/main/java/com/daedalus/world/companion/KennelArkPens.java`,
test `KennelArkPensTest`. Follows G147 Landfall on the Cinder Shelf (same seed) and its rescued animals; receipts for
the voyage chapters are G161.

## Story

The ark came home to Kennel Isle low in the water and loud: a sky-crane complaining from the rigging, a salt goat
chewing the rope, an ember fox singed and furious in the hold. The logbook (G92) is plain about what comes next:
"Every soul the hounds bring aboard gets a roof before the hounds get supper."

Each animal needs a pen of its own kind, built from planks:

| Animal | Pen | Planks |
|---|---|---|
| sky-crane | perch | 2 |
| salt goat | pasture | 3 |
| ember fox, ark cat | warm crate (holds two) | 1 |
| reef otter | pool | 4 |
| cinder hare | burrow | 1 |

The keepers have 4 planks of Kennel stores. Every driftwood plank the hounds fetched on the Cinder Shelf beyond what
the hull needed comes home too.

### NPC lines

> Keeper Wren (docking): "Stores are thin. Whatever driftwood you didn't nail into the hull, bring it up the hill."
>
> Old Harl (warm crate): "Fox and cat in one crate. Either they'll be friends by morning or we'll hear about it."
>
> Keeper Wren (short of planks): "The otter waits on the pier tonight. Not every animal has a pen." (fail)
>
> Old Harl (empty ark): "No passengers this time. The hounds will be sorry." (fail: no animals came aboard)
>
> Keeper Wren (all penned): "Every one of them under a roof. Now the hounds eat."

## Mechanic

- `need(animal)`: the pen kind; `Pen` carries cost and room (a warm crate has room for two).
- `spare(arrivalHull, landfall)`: planks fetched on the shelf minus the hull they mended.
- `plan(rescued, planks)`: pens the cheapest animals first (rescue order breaks ties); a pen with room is reused for
  free, otherwise one is built if the planks allow, else the animal is unpenned.
- `theWarmCrates(hounds, seed)`: the chapter. G147 landfall with the same seed ("the ark never came home: ..." if it
  did not), then the plan with 4 store planks plus the spare driftwood. Complete when at least one animal came aboard
  and every one is penned.

## Later (UNREAL-QUEUE, behind GATE)

Pen props on the Kennel Isle hill (perch, pasture fence, warm crate, pool, burrow), animals walking from the pier to
their pens, a plank counter, and the unpenned animal waiting on the pier.
