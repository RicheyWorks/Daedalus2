# The Twin Braids: Youtube Master Island, chapter 73 (youtube-master, contest G407)

Chapters 1-72 run from melody brewing (G25) to the middle catch (G401) and the drum lines (G404). With the drums
strung, two families want their door braids to hang as a pair.

## Story

Two bead braids were made on different islands. Keeper Oriel asks for the longest run of beads that appears in both
braids in the same order; the beads need not sit next to each other. Grabbing the run where the braids touch is a
trap. A SHORT run, a run NOT_SHARED by both braids, or a bad pick earns no credit, and braids with NO_COMMON bead
cannot be matched at all.

## Beats, mechanics and tests (`TwinBraidsTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The braids | `seeded`: two braids of 0-7 beads from R, G, B, Y | `seededBraidsAreDeterministic` |
| Longest shared run | `longest()`: longest common subsequence table; equals brute force over every subsequence of the left braid (30 seeds) | `longestMatchesBruteForce` |
| Touching beads are a trap | RB sits together in both braids, but RBY (3) is shared | `touchingRunIsATrap` |
| Short, unshared, no common | `name` NOT_SHARED, MALFORMED, NO_COMMON (no shared bead), no credit | `shortNotSharedAndNoCommonEarnNoCredit` |
| Bench rules | `name`: IGNORED, DUPLICATE | `guards` |
| Quest `q_twin_braids` | colony `QuestProgress`: compare braids x1, name run x1 (retries allowed), talk keeper_oriel | `questShortThenLongestThenKeeper` |

## Keeper Oriel's lines (`KeeperTwinBraids`)

- Greeting: "Two braids, RGBRY and GRBYR. Name the longest run of beads that shows up in both, in the same order. The
  beads needn't touch."
- Short: "Those 2 beads are in both braids, but a run of 3 is there too."
- Not shared: "That run isn't in both braids in that order."
- No common: "These braids share no bead at all. Nothing to match."
- Quest done: "The longest shared run. The twin braids will hang together!"
- After: "The twin braids hang side by side over the door."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

Two bead braids hung side by side at a hut door, a braiding bench with bead bowls. Source-only here.
