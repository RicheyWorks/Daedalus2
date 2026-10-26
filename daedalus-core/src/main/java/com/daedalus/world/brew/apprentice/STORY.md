# The Apprentices: Youtube Master Island, chapter 15 (youtube-master, contest G155)

Chapters 1-14 run from melody brewing (G25) to the song school (G116), the graduation concert (G131), the harbour
round (G139) and the guest lofts (G149). The families are packing, and the children don't want to go.

## Story

The four children from the far islands ask to stay on and learn a trade. Four masters each have a spare bench:
Mason Hale at the choir stones, Keeper Oriel at the spring, Aunt Brine in the cellar, Fisher Dov on the jetty.
Every child has a favourite master and every master has a favourite child. Old Wick hangs a lantern board and the
player pins each child to a master. On lantern night the board is read out. If a child and a master would both
rather have each other than the partners on the board, they slip away together before the lanterns are out, and
the whole arrangement falls apart. Wick knows the old way: let the children ask in turn, and let each master hold
on to the best offer so far. That always ends in a board nobody walks out of.

## Beats, mechanics and tests (`ApprenticeshipsTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| Rankings on both sides | `forChildren` (G116 `SongSchool.fromFarIslands` children; masters G53 Mason, G62 Keeper, G73 Brine, G66 Dov), seeded shuffles; constructor checks complete rankings | `seededRankingsOnBothSides` |
| Who would walk out | `blockingPairs`, `rank`; two-stable-pairings and rivals examples | `twoStablePairingsChildrenAndMastersEachGetTheirBest` |
| Wick's old way | `proposing(true/false)` Gale-Shapley: always stable; children-proposing is best for every child and worst for them among stable pairings, masters-proposing best for every master (checked against all 24 pairings, 30 seeds) | `galeShapleyIsStableAndOptimalForTheProposers` |
| The lantern board | `pair` / `unpair` / `announce`: UNKNOWN_CHILD, UNKNOWN_MASTER, CHILD_TAKEN, MASTER_TAKEN, NOT_PAIRED, NOT_EVERYONE | `guards` |
| Quest `q_apprentices` | colony `QuestProgress`: pair child x4 (counted once each), announce stable x1 (UNSTABLE can be fixed), talk old_wick | `questUnstableThenStableThenWick` |

## Old Wick's lines (`WickApprenticeLines`)

- Greeting: "Four children who want to stay, four masters with a spare bench. Pin them up on the lantern board.
  Mind: if a child and a master both fancy each other over who they've got, they'll sort it out themselves, and
  not kindly."
- Pinning: "3 children still to pin."
- Ready: "Board's full. Light the lanterns when you're sure."
- Unstable: "pupil_kelp_harbour slipped off to dov's workshop before the lanterns were out. Fix the board."
- Quest done: "Not one of them looking over the fence. The families can sail easy now."
- After: "Apprentices at every bench. The island's got its next keepers."

## Editor later (UNREAL-QUEUE)

A lantern board in the homestead yard (four child pins, four master hooks, rankings shown as ribbons), master
workshops at the choir stones, spring, cellar and jetty, a lantern-night moment where a blocking pair walks off.
Source-only here.
