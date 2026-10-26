# G41 Coat-variant lookup (OddsReaper Island)

Owner: oddsreaper. Code: `daedalus-core/src/main/java/com/daedalus/world/odds/breeding/CoatVariants.java`.
Table: `daedalus-core/src/main/resources/com/daedalus/world/odds/breeding/Mob_CorsoPup.coat_variants.json`
(blender-team delivery, link 48932, copied verbatim from `bot-team/staging/g28-coat-variants-20261019`).

## Story

The Odds Keeper's breeding ledger (G28, quest The Stormcoat) promises a buyer the odds of an ember,
smoke or ash pup and of a storm-marked one. When the litter comes, the pups must wear exactly the
colours the ledger predicted.

| Story beat | Mechanic in code |
|---|---|
| The ledger names which paint each possible pup wears | `CoatVariants.materialOdds`: G28 cross table summed per material instance |
| The pups are born and wear their coats | `CoatVariants.litterMaterials`: seeded G28 litter mapped to MI names in birth order |
| Every coat the arks bred has a paint | `CoatVariants.coversAllCoats`: all 4 patterns x 3 colours x storm/plain present |

Key format: `<coatKey>/<COLOUR>[/Storm]`, coatKey from `Coat.Pattern.coatKey()` (TuringCoat line).
The pattern itself is grown by the parent material `M_TuringCoat` from the G21 field (UNREAL-QUEUE 6.G21,
editor work, not in this PR); the instances only carry colour and storm streak.
