# Kennel Isle: First Words (contest gap G61)

Owner: art-master-flex. Code: `daedalus-core/src/main/java/com/daedalus/world/companion/KennelTraining.java`, test `KennelTrainingTest` (6 tests). Builds on the G37 bond meter (`KennelBond`): the bond tier says which commands a pet will take, and training teaches them.

## Mechanic
- Each cue drill succeeds with odds of 40 + bond/2 - difficulty percent, clamped to 5-95. The drills are seeded.
- Difficulty: come 0, stay 10, fetch 20, guard 35, rescue 50.
- Three successes in a row teach the command and add +2 bond. A miss resets the streak.
- A command the pet's tier doesn't unlock can't be drilled yet ("bond too low"). A learned command isn't drilled again.

## Lore
The ark hounds came down knowing commands in a language nobody on Kennel Isle speaks anymore: ark-crew words, clipped and old. Pups born on the island know nothing at all. Every keeper picks their own words, and the pack learns them one drill at a time. The old keepers said a dog learns a word three times: once by luck, once by trust, and the third time for good.

## Quest: First Words
Pip wants the pup to answer to *something*.
1. Raise the pup's bond to Loyal (50). Stay is a Loyal command.
2. Drill "come" until it sticks (three in a row), then "stay".
3. Do it within 5 sessions of 4 drills. A more trusting pup learns faster.

## NPC lines
- **Pip** (start): "He looks at me when I say his name. That's a start, right?"
- **Marrow** (miss): "Don't shout it. Say it like you mean it the same way every time."
- **Pip** (learned come): "He CAME. On purpose!"
- **Marrow** (bond too low): "He won't sit still for you yet. Feed him for a week, then try."
- **Marrow** (passed): "Two words. The ark crews started with less."

## Later (editor)
A training interaction on the kennel yard: cue button, pup reaction animation per success or miss, a streak pip on the pet panel. Queued in BOARD\UNREAL-QUEUE.md.
