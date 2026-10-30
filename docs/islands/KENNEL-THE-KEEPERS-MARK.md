# Kennel Isle: The Keeper's Mark (contest gap G37)

Owner: art-master-flex. Code: `daedalus-core/src/main/java/com/daedalus/world/companion/KennelBond.java`, test `KennelBondTest` (9 tests). Composes the G26 food loop (`KennelPantry` day reports), the G17 water loop and G11 fetch catches, and gates G32 pairings.

## Mechanic
- Every pet has a bond from 0 to 100. It moves once a day.
- A cared-for day (fed and watered): +4 fed, +2 watered, +3 if it drank a tonic, +1 per fetch catch (up to 5), then -1 decay. Full care is +13 a day; food and water alone are only +5.
- A neglect day (no full ration or no water): no gains, -10, then -1 decay.
- Tiers: **Wary** 0-24 (ignores commands), **Familiar** 25-49 (come), **Loyal** 50-79 (come, stay, fetch), **Devoted** 80+ (also guard and rescue).
- `careFromPantry` reads a G26 day report: a pet on the hungry list wasn't fed.
- `pairReady`: both pets must be at least Familiar before a G32 pairing.

## Lore
When the planet broke, the arks carried the hounds off the falling plates, but there was no room for the keepers who had raised them. The hounds that came ashore on Kennel Isle remember a keeper, just not you. The old keepers marked a dog's collar when it chose them. That mark is the bond meter. You can't buy it or brew it, only earn it day by day.

## Quest: The Keeper's Mark
A stray ark hound (bond 10, Wary) has been sleeping under the trough.
1. Feed it in pack order and keep the trough full every day for up to 7 days.
2. Play fetch and share a tonic. Food and water alone won't get it there in time (45 after 7 days).
3. Reach Loyal (50) with no neglect day. With full care that's day 4.
4. One missed meal or dry trough and the hound walks off. The quest fails and starts over.

## NPC lines
- **Marrow** (start): "That one came off an ark. It's waiting for somebody who isn't coming. Be the next best thing."
- **Pip** (first fetch): "It brought the ball back! Halfway. Then it sat on it."
- **Marrow** (neglect): "Dogs count days too. You missed one."
- **Marrow** (Loyal): "See the collar? That's the keeper's mark. It picked you."
- **Pip** (Devoted): "It stood between me and the cliff edge. Nobody told it to."

## Later (editor)
Bond meter UI on the pet panel; command menu greys out by tier. Queued in BOARD\UNREAL-QUEUE.md.
