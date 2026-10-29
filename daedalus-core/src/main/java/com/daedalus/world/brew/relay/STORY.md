# The Lighthouse Relay: Youtube Master Island, chapter 33 (youtube-master, contest G242)

Chapters 1-32 run from melody brewing (G25) to the net mending (G235) and the harvest feasts (G238). After the feasts
the island must send word to the far isle that the harvest is in.

## Story

A chain of lighthouses can pass a lamp signal, but sea haze dims some sightlines more than others, and a relay is
only as clear as its haziest sightline. Keeper Oriel asks the player to pass the signal lamp to lamp from lighthouse 0
to the far light. The clearest relay possible signals well; a dimmer one is too faint and earns nothing, and if no
chain of lamps reaches the far light there is no relay at all.

## Beats, mechanics and tests (`LighthouseRelayTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| The coast | `seeded`: 4-7 lighthouses, each sightline present with probability 1/2 at clarity 1-9 | `seededCoastIsDeterministic` |
| The clearest relay | `clearest()`: widest-path (maximin) Dijkstra; equals brute force over every simple path (30 seeds) | `clearestMatchesBruteForce` |
| The short way is hazy | direct 0-3 clarity 2, the 0-1-2-3 relay clarity 7 | `directSightlineIsNotAlwaysClearest` |
| No relay | the far light out of sight: `signal` is NO_RELAY, no credit | `noRelayEarnsNoCredit` |
| Relay rules | `light` / `signal`: NO_SIGHT, NOT_THERE, DUPLICATE, IGNORED | `guards` |
| Quest `q_lighthouse_relay` | colony `QuestProgress`: light lamp x1, signal well x1 (DIM can be retried with `restart`), talk keeper_oriel | `questDimThenWellThenKeeper` |

## Keeper Oriel's lines (`KeeperRelayLines`)

- Greeting: "A signal from lighthouse 0 to lighthouse 3, lamp to lamp. A relay is only as clear as its haziest
  sightline, so pick the clearest way."
- Passing: "Lamp 1 lit, haziest sightline so far 8."
- Dim: "It reached, but its haziest sightline is 2 where 7 could be. Too faint."
- No relay: "No line of lamps reaches the far light tonight. The signal waits."
- Quest done: "Clear across the whole sea. They will see it on the far isle."
- After: "Let the lamps burn down. Good signalling."

## Daedalus hook

Uses the colony `QuestProgress` and Keeper Oriel (`SeedSongSpring.KEEPER`) from G62, like every YTM chapter.

## Editor later (UNREAL-QUEUE)

A coast of small lighthouses with shutter lamps, haze volumes between some of them, and a beam that hops lamp to lamp.
Source-only here.
