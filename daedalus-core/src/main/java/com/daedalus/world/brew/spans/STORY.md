# The Drum Lines: Youtube Master Island, chapter 72 (youtube-master, contest G404)

Chapters 1-71 run from melody brewing (G25) to the counting circle (G398) and the middle catch (G401). The huts are
spread out, and a call to supper is not always heard.

## Story

The villagers will string drum lines (taut ropes that carry a drum beat) between huts. Each possible line takes some
rope. Keeper Oriel asks for a set of lines so a drum at any hut is heard at every hut, for the least rope. Taking all
the cheapest lines can leave a hut out. A DEAR net, a BROKEN net that misses a hut, or a bad pick earns no credit,
and if no set can reach every hut the village is CUT_OFF.

## Beats, mechanics and tests (`DrumLinesTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The village | `seeded`: 1-5 huts, 0-8 possible lines of rope 1-9 | `seededVillageIsDeterministic` |
| Least rope | `cheapest()`: Kruskal (sorted lines, union-find); equals brute force over every subset of lines (30 seeds) | `cheapestMatchesBruteForce` |
| Cheap first is a trap | the three cheapest lines (1, 2, 2) close a loop and leave hut 3 out | `cheapLinesFirstIsATrap` |
| Dear, broken, cut off | `string` DEAR (8 rope, not 7), MALFORMED, CUT_OFF (no full net exists), no credit | `dearBrokenAndCutOffEarnNoCredit` |
| Village rules | `string`: MALFORMED, DUPLICATE, IGNORED | `guards` |
| Quest `q_drum_lines` | colony `QuestProgress`: survey village x1, string lines x1 (retries allowed), talk keeper_oriel | `questDearThenCheapestThenKeeper` |

## Keeper Oriel's lines (`KeeperDrumLines`)

- Greeting: "4 huts and 5 places a drum line could run. Pick lines so a drum at any hut is heard at every hut, for
  the least rope."
- Dear: "That links every hut with 8 rope. It can be done with 7."
- Broken: "Some hut wouldn't hear the drum."
- Cut off: "No set of these lines reaches every hut. We need more rope paths."
- Quest done: "Least rope, every hut linked. Beat the drum!"
- After: "The drums carry across the whole village."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

Huts with small signal drums on posts, taut ropes strung between them, and a drummer. Source-only here.
