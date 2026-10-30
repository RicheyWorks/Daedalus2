# Kennel Isle: The Last Kennel Log (contest G92)

Code: `daedalus-core/src/main/java/com/daedalus/world/companion/KennelArkLogs.java` (+ `KennelArkLogsTest`).

## Mechanic
- Six logbook pages from the last kennel ark ride drifting plates (seeded distances 1-9).
- A hound scents a page only if it is grown (G65: Juvenile range 6, Adult 14, Elder 10) and bonded (G37 Loyal+).
- One scent per day; every plate drifts 1 farther each day. Chase the farthest reachable page first or lose it.
- Found pages are read in ark-day order.

## Quest: The Last Kennel Log
Recover all six pages within 8 days and read the log aloud at the kennel post.

## NPC lines
- **Old Tamsin:** "Those pages were tied to collars. Only a grown hound that trusts you will follow that old scent."
- **Keeper Mara (page lost):** "The plate's gone past the haze. Next time, chase the far ones first."
- **Old Tamsin (log complete):** "Day six. 'Keep them close.' That was my mother's hand."

## Lore
The log ties the kennel-post notches (G65), the hounds finding springs (G17) and the Corso line to the last ark.
