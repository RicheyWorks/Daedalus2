# The Gossip Circles: Youtube Master Island, chapter 79 (youtube-master, contest G427)

Chapters 1-78 run from melody brewing (G25) to the quiet elder (G420) and the driftwood cuts (G424). The trader's
visit is big news, and Keeper Oriel wants it to reach everyone.

## Story

On the island, news goes one way: each islander tells only certain friends. A gossip circle is a group where news
from anyone in it reaches everyone else in it. Keeper Oriel asks how many circles of two or more there are, so she
knows who to tell first. Treating a chain that news runs down as one circle is a trap, since the news never comes
back. A WRONG count or a bad pick earns no credit, and in a village where news never comes back round everyone is
LONE.

## Beats, mechanics and tests (`GossipCirclesTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The village | `seeded`: 1-7 islanders, 0-9 one-way tellings | `seededVillageIsDeterministic` |
| Circles | `circles()`: Kosaraju (finish order, then reversed tellings), groups of 2+; equals brute force over two-way reachability (30 seeds) | `circlesMatchBruteForce` |
| A chain is a trap | news from 0 reaches 5 but never comes back: two circles, not one | `oneBigChainIsATrap` |
| Wrong, lone | `count` WRONG, MALFORMED, LONE (no circle at all), no credit | `wrongAndLoneEarnNoCredit` |
| Washing stone rules | `count`: IGNORED, DUPLICATE | `guards` |
| Quest `q_gossip_circles` | colony `QuestProgress`: listen village x1, count circles x1 (retries allowed), talk keeper_oriel | `questWrongThenRightThenKeeper` |

## Keeper Oriel's lines (`KeeperGossip`)

- Greeting: "6 islanders, and news only goes one way from teller to listener. How many gossip circles are there,
  where news from anyone in it reaches everyone else in it?"
- Wrong: "Not 1. Follow the news round again."
- Lone: "News never comes back round here. Everyone is on their own."
- Quest done: "That's the count. Now I know who to tell first!"
- After: "The news goes round every circle by supper."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

Islanders chatting at the washing stones by the stream, laundry baskets and drying lines. Source-only here.
