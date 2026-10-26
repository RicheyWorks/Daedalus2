# Landfall on the Cinder Shelf (Kennel Isle chapter, contest)

Owner: art-master-flex. Code: `daedalus-core/src/main/java/com/daedalus/world/companion/KennelArkLandfall.java`,
test `KennelArkLandfallTest`. Follows G140 Crossing the Storm Belt (same seeds) and G107 The Muster at Hull Bay; odds
are the G107 post odds (G61 training, gated by G37/G65).

## Story

Past the storm belt the ark found land, though not much of it: the Cinder Shelf, a slab of the shattered planet still
warm under its ash, ringed with the driftwood of every ark that came before. The logbook (G92) calls it "the mending
beach". No ark leaves the shelf until her hull is whole again, and the casks only last so long.

Stranded on the shelf are animals the storm threw ashore: sky-cranes, salt goats, ember foxes, reef otters, cinder hares
and the odd ark cat. Three of them are out there each landfall. The rescue swimmer brings them aboard one at a time.

| Post | Each day on a hit |
|---|---|
| spring finder ("fetch") | 2 driftwood planks |
| deck runner ("come") | hauls 1 more plank |
| rescue swimmer ("rescue") | brings one stranded animal aboard |

Each plank mends 1 hull, up to 10. Water drops by 1 a day. At most 5 days.

### NPC lines

> Keeper Wren (beaching): "Ash underfoot and planks everywhere. Mend her before the casks give out."
>
> Old Harl (two planks): "That hound would fetch the whole beach if we let her."
>
> Keeper Wren (rescue): "An ember fox, singed and furious. Give it the warm crate."
>
> Old Harl (casks dry): "Dry casks on a dry shelf. We should have sailed sooner." (fail: the casks ran dry on the shelf)
>
> Keeper Wren (seaworthy): "Hull's whole. Count the hounds, count the passengers, and push her off."

## Mechanic

- `stranded(seed)`: three distinct seeded animals, in rescue order.
- `repair(roster, hull, water, stranded, seed)`: per day, fetch/haul/rescue roll once each (in that order) against the
  roster's post odds; an empty post always misses. Planks mend the hull (capped at 10), water drops by 1. Stops when the
  hull is full (seaworthy), the casks hit 0 ("the casks ran dry on the shelf"), or after 5 days ("the hull was not
  mended in time"). A full hull needs no days.
- `landfallOnTheCinderShelf(hounds, seed)`: the chapter. G107 lift and G140 crossing with exactly the seeds
  `crossingTheStormBelt` uses (the voyage is identical), then landfall with the hull and water the ark arrived with.

## Later (UNREAL-QUEUE, behind GATE)

Cinder Shelf beach set, a growing plank pile and hull bar, rescued-animal props boarding the ark, and a day-by-day
replay of the server's landfall. Rescued animals are good candidates for G12 creature receipts.

## C++ twin (G154)

`engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusKennelVoyageCore.h` replays the roll-driven rules
(`KennelArkVoyage.crossRolls`, `KennelArkLandfall.repairRolls`) from server rolls. `KennelVoyageParityFixtureTest` writes the
LCG parity table `engines/unreal/core-test/kennel_voyage_parity.txt` (300 crossings, 300 repair runs) and
`core-test/kennel_voyage_core_test.cpp` replays it under gcc (ASan/UBSan) and clang with `-Werror`.
