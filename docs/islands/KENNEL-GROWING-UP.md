# Kennel Isle: Growing Up (contest G65)

Code: `daedalus-core/src/main/java/com/daedalus/world/companion/KennelGrowth.java` (+ `KennelGrowthTest`).

## Mechanic
- A pup ages a day every day but only **grows on care-days** (fed + watered, G37 `KennelBond.Care`).
- A bonded care-day (tonic or fetch) has a seeded 15% **growth spurt**: one extra care-day.
- Neglect stalls growth and costs bond (G37 rules).
- Stages: Newborn (0) -> Pup (3) -> Juvenile (10) -> Adult (21) -> Elder (60 care-days). Each sets model scale,
  stamina and the commands the pup can be trained on; G61 `KennelTraining` drills are refused with "too young".

## Quest: Growing Up
Raise a newborn ark hound to Juvenile within 14 days, with no more than 2 neglect days.

## NPC lines
- **Keeper Mara:** "They don't grow on days. They grow on care. Feed her, water her, and she'll show you."
- **Keeper Mara (spurt):** "Look at those paws! Play does that. A pup that's loved stretches overnight."
- **Old Tamsin (too young):** "Stay? She can barely sit up. Ask again when her ears stand."
- **Keeper Mara (Juvenile):** "There she is. Ears up, eyes on you. Now the real lessons start."

## Lore
When the planet shattered, the ark kennels ran on rationed days. The keepers learned that a hound fed on schedule
but never played with stayed small and skittish, so they kept a tally of care-days, not calendar days, carved into
the kennel posts. Kennel Isle still carves the tally: every notch is a day someone showed up.
