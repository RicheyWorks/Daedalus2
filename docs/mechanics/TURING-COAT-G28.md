# Turing-coat pups (contest gap G28)

Owner: oddsreaper. Module: `daedalus-core/src/main/java/com/daedalus/world/odds/breeding/` (JDK-only, no editor).

## Story
When the arks lifted the last villagers off the breaking planet, the hounds came too. On OddsReaper Island their
descendants are called **Turing-coat pups**, after the old stories of a mathematician who showed how spots and stripes
can grow out of simple rules. Their coats follow simple rules too: spots beat stripes, stripes beat the labyrinth, and any pattern beats plain; an ember parent
and an ash parent make a smoke pup; and a few carry the **storm-mark**, a silver streak that only shows when a pup gets
it from both sides. Islanders say storm-marked pups are born on the storm line. The Odds Keeper keeps the breeding
ledger, and her third quest, **The Stormcoat**, asks the player to raise one. She always tells the true odds before a
pairing.

## Mechanics (each story beat is code)
| Beat | Code | Rule |
|---|---|---|
| Coat genes | `Genotype` (`"SB EA CM"`) | Pattern S > B > L > P; colour E/A blend to smoke; storm-mark M recessive. |
| What a pup looks like | `Genotype.coat()`, `Coat.describe()` | e.g. "storm-marked smoke stripes". |
| The breeding ledger | `CoatOdds.cross / chance / stormMarkedChance` | Exact odds over all 64 gamete pairs. |
| Hidden carriers | `CoatOdds.carrierChance` | Bayes: an unmarked pup of two carriers carries the mark 2 times in 3. |
| A litter | `CoatOdds.litter(mother, father, seed, size)` | 1-8 pups, seeded with `OddsRng`. |
| The Stormcoat quest | `StormcoatQuest` | The Keeper's advice line; done at the first storm-marked pup. |

## Relation to G21 TuringCoat (art-master-flex, PR212)
G21 owns how a coat *grows*: a seeded Gray-Scott model on feed/kill genes, classified into the TonicBrewer coat keys.
G28 is only the odds layer on top. Each pattern allele names one G21 kennel line, so a pup's odds and its grown coat agree:

| G28 allele | `Coat.Pattern` | G21 line (`Pattern.genes()`) | Coat key (`Pattern.coatKey()`) |
|---|---|---|---|
| S | SPOTS | `TuringCoat.SPOTTED_LINE` | `Spots` |
| B | STRIPES (bands) | `TuringCoat.STRIPED_LINE` | `Stripes` |
| L | LABYRINTH | `TuringCoat.LABYRINTH_LINE` | `Labyrinth` |
| P | PLAIN | `TuringCoat.PLAIN_LINE` | `None` |

`Genotype.grownCoatKey(seed)` grows the expressed line with G21 and a test checks it lands on the predicted key.
Colour, storm-mark, carrier Bayes, cross tables, seeded litters and The Stormcoat quest are G28's own.

## Later (editor / art)
Pup colour variants (ember / smoke / ash) and the storm streak on top of G21's grown patterns: UNREAL-QUEUE.md and a NEED to blender-team.
