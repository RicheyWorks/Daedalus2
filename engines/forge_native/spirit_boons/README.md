# Spirit Boons (Prismheart R2-9, hephaestus)

Header-only, engine-free C++17 core: `DaedalusSpiritBoonsCore.h`. Rules authority: `spirit_boons_ref.py`
(`python spirit_boons_ref.py --check spirit_boons_golden.txt`). The golden is generated, never hand-edited.

Spirits summoned in Wardens' Accord (its `SpiritName` order) and Shardring (hue *i* → spirit *i*) are tallied.
Each spirit grants one small boon in another cabinet, as a delta to a setting in that cabinet's `DIFFICULTY` table.
A spirit summoned 5+ times gives a doubled boon.

| Spirit | Cabinet | Setting | Delta | Source |
|---|---|---|---|---|
| Cinder Wisp | glowmoss | light | +1 | IDEAS.md (Art Master Flex #5) |
| Mere Sprite | spiritkite | wind | +2 | IDEAS.md (Art Master Flex #5) |
| Thornkin | facetlock | spare | +1 | PROPOSED |
| Sky Lark Spirit | lumenpath | moves | +1 | PROPOSED |
| Hollow Moth | shardfall | cracked | -1 | PROPOSED; needs Hollow Moth rival beaten |
| Glass Heron | glimmerloom | satchel | +2 | PROPOSED |
| Lantern Newt | shadewatch | hearts | +1 | PROPOSED |

**Data + evaluator only.** No game's rules change until that game's owner ACKs its boon (PLAN.md R2-9).
API: `Add`, `AddShardringHue`, `Level`, `BoonsFor(tally, gameId, mothFreed, &list)`. Statuses: OK, NULL_POINTER,
BAD_SPIRIT, BAD_COUNT, BAD_TALLY, OVERFLOW, UNKNOWN_GAME. Refusals leave state unchanged. No randomness.
