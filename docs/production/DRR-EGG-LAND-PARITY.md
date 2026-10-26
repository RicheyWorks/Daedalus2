# DRR egg and land parity repair

Full CI found the offline realm spec had native additions absent from Java:
DRAGON_EGG with kind EGG, the castle chest at 2,4, and three demo land records.
Java now declares the same egg and chest. The former random chest roll still
advances the RNG, so subsequent loot remains identical to the shipped world.

RetroRealm has validated land annotations and a backward-compatible constructor
with no lands. RetroCodec writes/reads land records. Numbers must be unique and
within 0..9999; rectangles must have positive dimensions and fit a known map.
Bounds use wide arithmetic to reject overflow. These annotations do not mint,
transfer, authorize ownership, move physical islands or change NFT dimensions.

The generator defaults to no owners. withLands accepts an explicit validated
overlay. The strict offline parity test uses the fixture's demo overlay and
compares the entire resulting spec, including all maps/items/chests/encounters
and annotations. HERO/OSTRA are offline demo labels, not live deed authority.
Server registry integration, mint/tug updates and cache invalidation are pending.
Do not serve fixture demo labels as production ownership data.
