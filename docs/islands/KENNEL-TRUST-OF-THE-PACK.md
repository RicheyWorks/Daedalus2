# Kennel Isle: Trust of the Pack (contest gap G32)

Owner: art-master-flex. Code: `daedalus-core/src/main/java/com/daedalus/world/companion/KennelLitter.java`, test `KennelLitterTest` (7 tests). Composes `TonicBrewer` (tonic engine) and `TuringCoat` (G21).

## Mechanic
- Base pairing odds are 30%. If the pair drank a breeding brew (a recipe with `breedChancePct`, such as **Bond** = Dozeleaf + Starkibble at +20%), add that bonus times the brew's strength factor. Coat, drinker and stage all scale it, the same way they scale every other tonic. The odds cap at 90%.
- On success, a seeded litter of 1-3 pups. Each pup's genes come from `TuringCoat.breed`, and its coat grows from them.
- Parents need 7 days' rest between litters, and a pet can't pair with itself.

## Lore
Nobody owns a dog on Kennel Isle. The pack decides who it trusts, and it decides slowly. The keepers' trick was Bond: Dozeleaf to calm them, Starkibble because it's what they'd dig up anyway. A pair that shares a Bond trough is more likely to bring pups to the keeper's door. A Labyrinth pair's pups come out with the maze already in their coats.

## Quest: Trust of the Pack
Marrow wants a new litter before winter, and Tank won't settle.
1. Steep Dozeleaf + Starkibble in the kennel trough (Bond).
2. Let Tank and Luna drink, with Tank first because he's the Corso.
3. Try a pairing. If it fails, the pair rests (no cooldown on a failed try; try again tomorrow).
4. Name the pups. Their coats are whatever the genes grow.

## NPC lines
- **Marrow** (start): "Can't make dogs like each other. You can make the water nicer, though."
- **Pip** (after the Bond brew): "Tank put his head on Luna's back. He never does that."
- **Marrow** (failed try): "Not today. Dogs keep their own calendar."
- **Marrow** (litter): "Look at that coat. You can't paint that. The water and the genes drew it together."
- **Marrow** (resting parent): "She just had pups. Give her a week or give me a reason."

## Later (editor)
Pairing interaction on kennel beds; pup spawn uses the coat material from G21. Queued in BOARD\UNREAL-QUEUE.md.
