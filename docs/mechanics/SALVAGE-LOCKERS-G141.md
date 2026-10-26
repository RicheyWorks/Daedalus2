# G141 The Salvage Lockers (Sky Islands arks / OddsReaper Island)

Owner: oddsreaper. Code: `daedalus-core/src/main/java/com/daedalus/world/odds/lockers/`.
Reuses `world.odds.OddsRng` and `Intervals`. Self-contained.

## Story

The wreck's brass compass sits in one of four sealed lockers. You lay a hand on one; then two of the
others are opened empty and you may switch to the last closed one. If the Odds Keeper opened them, he
knew where the compass was and would never show it, so switching wins 3 in 4. If the blind deckhand
pried them, he had no idea; half the time he breaks the compass out himself (the round is void), and
when he doesn't, switching is only even money. For the first two rounds you see who opened the
lockers; after that you don't, and the Keeper reminds you that an empty pair is itself evidence it was
him (2 in 3), so switching still wins 2 in 3.

| Story beat | Mechanic in code |
|---|---|
| The Keeper knows | `LockerOdds.stayKeeper` 1/n, `switchKeeper` (n-1)/(n(n-k-1)) (Monty Hall, generalized) |
| The blind deckhand | `blindKeepsRound` (n-k)/n, `stayBlind` = `switchBlind` = 1/(n-k) |
| Not told who opened | `keeperPosterior` (Bayes on "no compass shown"), `switchUntold` / `stayUntold` |
| The lockers themselves | `LockerRound`: seeded deal / resolve, `simulate` with Wilson interval and void rate |
| Five rounds, three compasses | `LockerQuest` (q_salvage_lockers) |

Checks: the closed forms equal a full enumeration of prize, opened sets and switch targets for every
n in 3..7 and k in 1..n-2. With the Keeper's advice each quest round finds the compass half the time,
so three of five comes in about half the time.

## Quest q_salvage_lockers

1. READY: "Round R of 5, F compasses so far. Pick locker one."
2. OFFER: "I opened those, and I know where it is." / "The deckhand pried those blind." / "You didn't see who opened them." + "Stay: S%. Switch: W%."
3. FOUND_ENOUGH: "F compasses in 5 rounds. The arks can steer."
4. CAME_UP_SHORT: "F compasses in 5 rounds, V broken open. Not enough."

No wagering.

## Editor / asset needs (later, not in this PR)

- Locker wall prop (four doors), Keeper/deckhand opening animations, compass pickup.
