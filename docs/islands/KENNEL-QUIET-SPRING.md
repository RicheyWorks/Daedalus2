# Kennel Isle: The Quiet Spring (contest gap G17)

Owner: art-master-flex. Story plus the mechanic it runs on.

- Mechanic: `daedalus-core/src/main/java/com/daedalus/world/companion/KennelWaterLoop.java` (daily water ledger + quest check), rules in `data/islands/kennel-water-v1.json`, tests in `KennelWaterLoopTest` (11 tests).
- Source rules: `tools/islands/kennel-isle/ISLAND.md` s1 (fresh water) and s3 (livestock loop). Until now they were editor tags only.

## Lore
When the planet broke, most shards kept their cities and lost their water. Kennel Isle kept the opposite: one living aquifer and no one left to use it. The spring still runs 40 L a minute into a basin cut by people who didn't come back. The Ark keepers who found the island built the rest of the loop (the rain catchers, the sand and charcoal filter, the 2,000 L cistern, the still and the old well) because they never again wanted to trust a single source.

Coats remember water. The keepers say a pup's spots or stripes set like ripples in a drying trough. That's why the tonic engine reads coat patterns, and why a Labyrinth coat drinks twice from the same brew.

## Quest: The Quiet Spring
A slide upslope silts the spring, and the cistern drains through a cracked tap. Three dry, sunny days follow.
- Goal: no animal goes thirsty on any of the three days.
- Tools: the well (10 L buckets, up to 40 hauls a day), the solar still (5 L a sunny day) and the filter.
- Choice: haul every day, or bank water early. The ledger counts both. For the starter roster (2 dogs, a Cane Corso, 2 goats and a capybara, 18 L a day), the answer is 2 buckets a day or 5 then 1.
- Reward hook: on pass, the keeper unseals the spring (story only; the reward item goes to the Unreal queue).

## NPC lines
- **Marrow, old Ark keeper** (start): "Spring's gone quiet. Don't look at me like that. We built four backups for a reason. Go prove one of them works."
- **Marrow** (after day 1, short): "Dogs first, goats second, herbs if there's anything left. That's the order the trough line runs in, too."
- **Marrow** (after day 1, on track): "Bucket arms tonight, full bowls tomorrow. That's the deal."
- **Pip, kennel kid** (any thirsty day): "Tank won't play fetch. He just lies by the trough and stares at it."
- **Marrow** (pass): "Three days on a well and a jar of sunlight. Now you know why we never trusted just the spring. Grab a shovel; let's let her run again."
- **Marrow** (fail): "The animals forgive. The ledger doesn't. Again, tomorrow."

## Later (editor)
Quest trigger on the `W1_Spring` actor, ledger readout on the cistern sign; queued in BOARD\UNREAL-QUEUE.md.
