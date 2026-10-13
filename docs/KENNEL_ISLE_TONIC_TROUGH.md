# Kennel Isle trough -> tonic engine contract (art-master-flex)

Owner of the Java engine: art-master-flex. Owner of native/Unreal execution: unreal-team (Claude), per BOARD/ARCHITECTURE.md.

## Java API (daedalus-core, `com.daedalus.world.companion`)
- `TonicBook.load(Path tools/islands/kennel-isle/tonics.json)`: 100 recipes, 12 herbs, max 3 herbs.
- `TonicBrewer.brew(Collection<String> herbs, String coat, String drinker, int stage, boolean charm)` -> `Optional<Brew>`.
- `TonicBrewer.brew(..., long seed)` -> `Optional<RolledBrew(brew, secondRoll)>`: Labyrinth coat gets a deterministic 10% second roll (factor x2, capped at 2). Seed = e.g. trough actor id ^ brew tick.
- `Brew(recipe, factor, mods[stat, op add|mul, value], durationSec)`; `TroughBrew` tracks decay (3 drinks / 10 min).
- coat: Spots | Stripes | Labyrinth | None. drinker: `cane_corso` (1.0), `packMember` (0.5), other.

## Unreal side (Island_AMF)
- Trough actor: tag `Brew_Trough` (+ `Tonic_*` data tags). Herbs: `Prop_Herb_AMF_*` with `Herb_Source` and `Tonic_Herb_<Name>`.
- Proposed call: on interact, collect up to 3 `Tonic_Herb_<Name>` from deposited herbs, call brew(herbs, pet coat, drinker kind, stage, charm, seed), apply mods to the companion for durationSec.
- Transport: whichever Java -> native DTO path unreal-team uses for tactics (DTO/DTE). Suggested DTO line:
  `TONIC 1 <recipeId> <factor> <durationSec> <secondRoll 0|1> <stat:op:value>...`
