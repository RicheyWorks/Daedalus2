# The Name Stones: Youtube Master Island, chapter 47 (youtube-master, contest G297)

Chapters 1-46 run from melody brewing (G25) to the well pipes (G289) and the hut walkways (G293). The marsh families
are joined to the village, and every family wants a name stone by the path.

## Story

Each family gets a stone with its name, but carving is slow, so only the start of each name is cut. A stone is clear
when no other family's name starts the same way. Keeper Oriel wants every stone clear with as few letters carved as
possible. The player lists the families and carves the stones. The fewest letters is right; longer carvings earn no
credit, and a stone two families could both read is ambiguous and earns none.

## Beats, mechanics and tests (`NameStonesTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The families | `seeded`: 2-7 names of 1-5 letters from a, b, c; no name starts another | `seededVillageIsDeterministic` |
| The shortest clear starts | `shortest(i)`: a trie with a count through each node; the first node only one name passes; equals brute force over every start (30 seeds) | `shortestMatchesBruteForce` |
| A known village | marsh, mason, mill, oriel: mar, mas, mi, o = 9 letters | `knownVillage` |
| Ambiguous | "m" fits three families: `carve` is AMBIGUOUS, no credit | `ambiguousStoneEarnsNoCredit` |
| Stone rules | `carve`: NOT_THERE, LONG, DUPLICATE, IGNORED | `guards` |
| Quest `q_name_stones` | colony `QuestProgress`: list families x1, carve well x1 (LONG can be recarved), talk keeper_oriel | `questLongThenWellThenKeeper` |

## Keeper Oriel's lines (`KeeperNameLines`)

- Greeting: "4 families, and a stone for each. Carving is slow: cut only the start of each name, just enough that
  nobody mistakes one family's stone for another's."
- Ambiguous: "The stone for the marsh family could belong to another family too."
- Long: "That's 11 letters of carving. 9 would tell every family apart."
- Quest done: "Short and clear. Every family knows its stone."
- After: "The stones are set along the path."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A path of name stones whose carved letters appear as the player cuts them, with a chisel and mallet. Source-only here.
