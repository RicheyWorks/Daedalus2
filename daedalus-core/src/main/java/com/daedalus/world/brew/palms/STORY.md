# The Tall Palms: Youtube Master Island, chapter 65 (youtube-master, contest G378)

Chapters 1-64 run from melody brewing (G25) to the treasure scales (G368) and the lucky hives (G374). With the hives
ribboned, the children want coconuts.

## Story

Palms of different heights stand along the shore path. The climber is up one palm and wants to hop to the first palm
further along that stands taller. Keeper Oriel asks which palm that is (or none, if no palm further on is taller). A
palm of equal height is not taller, and the tallest palm is not always the first; a WRONG palm earns no credit.

## Beats, mechanics and tests (`TallPalmsTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The shore | `seeded`: 1-15 palms of height 1-9, climber on any palm | `seededShoreIsDeterministic` |
| Next taller | `nextTaller(i)` for every palm with a monotonic stack; equals a brute-force forward scan (30 seeds) | `nextTallerMatchesBruteForce` |
| Equal and tallest are traps | heights 4, 2, 4, 5, 9 from palm 0: palm 2 is equal, palm 4 is tallest, palm 3 is right | `equalAndTallestAreTraps` |
| Wrong | `name` a wrong palm (or a palm when none is taller) is WRONG, no credit | `wrongEarnsNoCredit` |
| Shore rules | `name`: DUPLICATE, IGNORED (blank id or no such palm) | `guards` |
| Quest `q_tall_palms` | colony `QuestProgress`: walk shore x1, name taller x1 (retries allowed), talk keeper_oriel | `questWrongThenRightThenKeeper` |

## Keeper Oriel's lines (`KeeperPalmLines`)

- Greeting: "5 palms along the shore path. The climber is on palm 0 and wants to hop to the first palm further along
  that stands taller. Which palm is it?"
- Wrong: "Palm 2 isn't the first taller one. It's palm 3." (or "It's no palm at all.")
- Quest done: "That's the one. Up she goes!"
- After: "Coconuts for everyone."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A row of palms of mixed heights along a sandy path, a climber with a rope loop, and coconuts. Source-only here.
