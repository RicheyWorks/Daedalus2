# Kennel Isle: Storm Season (contest gap G54, storyline chapter)

Owner: art-master-flex. Code: `daedalus-core/src/main/java/com/daedalus/world/companion/KennelSeason.java`, test `KennelSeasonTest` (6 tests). Runs the G17 water loop (`KennelWaterLoop`), the G26 food loop (`KennelPantry`) and the G37 bond meter (`KennelBond`) together, one tick a day for the whole roster.

## Mechanic
- Every day: the cistern waters the roster, the kibble bin feeds the pack in pack order, then each pet's bond moves.
- A pet that ended thirsty or hungry has a neglect day. Its bond takes the neglect penalty. Everyone else gets basic care, plus tonic and fetch gains where the keeper gave them.
- The season log keeps every day's bonds, who was thirsty, who was hungry, the cistern level and the kibble stock.
- `stormWeek(prep, stormFood)`: 2 clear prep days, a 3-day storm (rain, spring silted, filter clogged, no grazing), then 2 clear days.
- Storm Season passes when nobody had a neglect day and every pet ends at least Familiar (25).

## Lore
Storms on the broken planet don't come from the sky. They come up from the cracks between the plates: dust, ash and old ark smoke, three days at a time. The spring silts up, the filter clogs, and the goats won't leave the barn. The keepers who lasted were the ones who filled the cistern and the kibble bin before the bell on the cliff started to ring.

## Quest chapter: Storm Season
Marrow can smell it coming: two days of clear weather, then three days of storm.
1. Use the two clear days. Keep the spring running into the cistern, graze the goats, and craft every batch of kibble you can.
2. Ride out the storm on what you stored. No hay, no Starkibble and no filtered water come in.
3. Nobody can go thirsty or hungry, not even the pup at the back of the pack order.
4. When the sky clears, every pet should still trust you (bond 25 or more).

## NPC lines
- **Marrow** (prep day): "Fill everything that holds water. Then fill it again."
- **Pip** (storm day 1): "I can't see the barn. Tank's sitting in front of the door like he's guarding it."
- **Marrow** (kibble running low): "Count the bowls before you count the days."
- **Marrow** (passed): "Three days of ash and not one empty bowl. That's keeping."
- **Pip** (failed): "Pip-the-pup wouldn't come to me after. I think he remembers."

## Later (editor)
A day/storm cycle on Kennel Isle drives the season tick; HUD shows the cistern and kibble stock. Queued in BOARD\UNREAL-QUEUE.md.