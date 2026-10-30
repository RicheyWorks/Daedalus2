# The Quiet Elder: Youtube Master Island, chapter 77 (youtube-master, contest G420)

Chapters 1-76 run from melody brewing (G25) to the weak bridges (G415) and the sweeper's walk (G417). With the yard
swept, the islanders gather round the fire.

## Story

Tradition says the first cup of tea goes to the quiet elder: the islander everyone knows, who knows no one by name.
Keeper Oriel asks who it is, and the fastest way is to ask "does a know b?" and rule one islander out with every
answer. Picking the best-known face is a trap. A WRONG name or a bad pick earns no credit, and some nights there is
NO_ELDER at all.

## Beats, mechanics and tests (`QuietElderTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The gathering | `seeded`: 1-6 islanders, an elder planted about half the time | `seededGatheringIsDeterministic` |
| The elder | `elder()`: celebrity elimination (one pass, then one check, at most 3(n-1) questions); equals brute force checking every islander (30 seeds) | `elderMatchesBruteForce` |
| Well known is a trap | islander 0 is known by others but knows 2 | `wellKnownIsATrap` |
| Wrong, no elder | `name` WRONG, MALFORMED, NO_ELDER (nobody fits), no credit | `wrongAndNoElderEarnNoCredit` |
| Fire rules | `name`: IGNORED, DUPLICATE | `guards` |
| Quest `q_quiet_elder` | colony `QuestProgress`: gather islanders x1, name elder x1 (retries allowed), talk keeper_oriel | `questWrongThenFoundThenKeeper` |

## Keeper Oriel's lines (`KeeperQuietElder`)

- Greeting: "4 islanders round the fire. One may be the quiet elder: everyone knows them, and they know no one by
  name. Who is it?"
- Wrong: "Islander 0 isn't the quiet elder."
- No elder: "No quiet elder sits at this fire tonight."
- Quest done: "The quiet elder! Give them the first cup of tea."
- After: "The quiet elder sips tea and listens."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A gathering fire ringed by islanders on logs, a tea kettle and cups, and a quiet elder in a shawl. Source-only here.
