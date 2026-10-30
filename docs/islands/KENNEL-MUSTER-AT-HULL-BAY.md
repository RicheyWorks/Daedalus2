# The Muster at Hull Bay (Kennel Isle chapter, contest)

Owner: art-master-flex. Code: `daedalus-core/src/main/java/com/daedalus/world/companion/KennelArkMuster.java`,
test `KennelArkMusterTest`. Builds on G37 bond tiers, G61 drill odds, G65 growth stages and G92 The Last Kennel Log.

## Story

The last kennel log ends with "Keep them close." The keepers took it literally. In Hull Bay, where the plates ground
together and left a sheltered beach, they rebuilt a small ark from salvaged hull planks. No ark has lifted off the
shattered planet without hounds since the first one: the hounds find the springs, guard the hatch in the storm belt,
pull people out of the water and run messages between decks. So before this ark lifts, the keepers hold a muster.

Four posts must be named, one hound each:

| Post | Command | Who can take it |
|---|---|---|
| Hatch guard | guard | Adult or Elder, Devoted |
| Rescue swimmer | rescue | Adult (not Elder), Devoted |
| Spring finder | fetch | Juvenile or older, Loyal |
| Deck runner | come | Pup or older, Familiar |

At dawn each posted hound is called once. If at least three posts hold, the ark lifts. If not, the keepers try again
the next dawn. After three dawns the storm window closes.

### NPC lines

> Keeper Wren (start): "One hound per post, and no hound on two. Pick the crew the way the ark-keepers did: by who answers."
>
> Old Harl (an Elder put on rescue): "Not her. She has pulled her last swimmer. Put her on the hatch; nothing gets past her."
>
> Keeper Wren (crew short): "We cannot lift with empty posts. Raise them another season." (fail: crew short)
>
> Keeper Wren (launch): "Three held. That is how the first ark left, too. Hounds aboard, then us."
>
> Old Harl (window missed): "The storm belt is closing. We wait for the next one, and the hounds wait with us."

## Mechanic

- `fits(hound, post)`: stage allows the command (`KennelGrowth.canTrain`) and the bond tier obeys it (`KennelBond.obeys`).
- `assign(hounds)`: up to 8 distinct hounds. Exhaustive search for the roster that fills the most posts, then has the
  highest summed G61 odds (`KennelTraining.successPct`); ties keep the earlier hound. The test checks it against an
  independent brute force.
- `muster(roster, seed)`: each posted hound rolls once (`SplittableRandom`), holding when the roll is under its odds;
  the ark launches at 3 or more holds.
- `musterAtHullBay(hounds, seed)`: the chapter. Fails at once with `crew short: <posts>` if fewer than 3 posts can be
  filled; otherwise up to 3 dawns, complete on the first launch, else `the ark missed its window`.

## Later (UNREAL-QUEUE, behind GATE)

Hull Bay beach set (salvaged-plank ark, four post markers), a muster widget that shows each hound's odds per post
(the UE binding from G102 already exposes `CanDrill` / `DrillSuccessPct`), and the dawn roll call in Play.

## C++ twin (G128)

`engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusKennelMusterCore.h` mirrors `fits` / `assign` (same search order and tie-breaks) so the UE muster widget shows the crew the server picks. `KennelMusterParityFixtureTest` writes `engines/unreal/core-test/kennel_muster_parity.txt` (fit grid + 300 LCG crews) and must match the committed copy; `kennel_muster_core_test.cpp` replays it with gcc and clang in the Engines workflow. Dawn rolls stay server-side.
