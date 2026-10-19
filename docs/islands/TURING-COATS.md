# Turing coats (contest gap G21)

Owner: art-master-flex. Code: `daedalus-core/src/main/java/com/daedalus/world/companion/TuringCoat.java`, test `TuringCoatTest` (8 tests).

## Mechanic
A pet's coat is a Gray-Scott reaction-diffusion field (64 x 64 wrapping skin, 4,000 steps, Du 0.16, Dv 0.08) grown from two genes, **feed** (0.010-0.080) and **kill** (0.040-0.075). The seed places 12 starting freckles. Pigment is where V > 0.2:
- under 3% pigment: **None**
- largest patch under 6% of pigment: **Spots**
- largest patch over 60%: **Labyrinth**
- otherwise: **Stripes**

These are the coat keys `TonicBrewer` reads, so tonic strength and the Labyrinth second roll now come from breeding, not a hand-set tag. G06 hatchlings use the same keys.

Breeding: pup genes = parent mean +/- up to 0.0015 per gene (seeded), clamped.

| Ark line | feed | kill | breeds |
|---|---|---|---|
| Spotted | 0.0367 | 0.0649 | patchy: Spots, now and then Stripes |
| Striped | 0.0340 | 0.0618 | not true: pups usually drift to Spots |
| Labyrinth | 0.0420 | 0.0590 | true |
| Plain | 0.0300 | 0.0700 | true; Plain x Labyrinth gives patchy (Spots/Stripes) hybrids |

## Lore
The Ark keepers didn't paint their dogs. They wrote down two numbers for every litter, how hungry the skin was and how fast it forgot, and let the coat draw itself. Striped dogs were the prize because they never bred true: a striped pair almost always threw spotted pups, so every striped dog in the kennel book is a small accident someone was lucky enough to keep. The keepers said a Labyrinth coat "remembers the maze," which is why it drinks a brew twice.

## Later
Coat material driven by the grown field (editor), via BOARD\UNREAL-QUEUE.md.
