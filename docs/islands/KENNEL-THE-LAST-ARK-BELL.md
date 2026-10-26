# Kennel Isle: The Last Ark Bell (contest gap G50)

Owner: art-master-flex. Code: `daedalus-core/src/main/java/com/daedalus/world/companion/KennelRescue.java`, test `KennelRescueTest` (5 tests). Composes `KennelBond` (G37, the Devoted "rescue" command) and `TonicBottler` (G45, bottled tonics aged to the rescue day).

## Mechanic
- A wreck has stranded survivors, a number of days before its plate falls, and a round trip from the kennel (1-2 days). Seeded wrecks have 4-12 survivors and fall in 3-8 days.
- Only Devoted pets (bond 80+) take the rescue command. Each leads 2 survivors off per trip, or 3 if it carries a bottled tonic that is still T3 or better on the rescue day.
- Trips = days until the fall / round-trip days, rounded down. A trip that can't finish before the fall doesn't count.
- `shortfallPerTrip` tells the player how many more survivors per trip the crew would need: bond another dog to Devoted, or bottle a better tonic.

## Lore
The arks didn't all make it to the sky islands. Some came down hard on plates that are still breaking off the world, one ledge at a time. Each ark carried a bell, and the bell rings when the plate shifts. The keepers listen for it from the kennel cliffs. When a bell rings, they have days, not weeks. People can't cross a breaking plate, but a dog that trusts you can: it finds the stranded hounds and goats in the dust and leads them back across the cracks.

## Quest: The Last Ark Bell
The Kepler's bell has been ringing for a day. Nine survivors, four days before the plate drops, and a one-day round trip.
1. Check your crew. One Devoted dog saves 8 and leaves one behind.
2. Fix it: bond a second dog to Devoted (G37), or send the first with a fresh T3 or T4 bottled tonic (G45) to lead 3 per trip.
3. Bring all nine home before the plate falls.

## NPC lines
- **Marrow** (bell rings): "Hear that? That's the Kepler. Four days, maybe less."
- **Pip** (one dog short): "Tank can only bring two back at a time. Somebody gets left!"
- **Marrow** (tonic): "Ark-glass tonic in his collar. He'll go faster and bring an extra one back."
- **Marrow** (all saved): "Nine. Every one. The bell can stop now."
- **Pip** (plate falls): "It's gone. Just dust where it was."

## Later (editor)
Rescue board at the kennel cliffs lists ringing wrecks and days left; crew picker greys out non-Devoted pets. Queued in BOARD\UNREAL-QUEUE.md.