// SPDX-License-Identifier: MIT

package com.daedalus.world.colony;

import java.util.List;
import java.util.Set;

/**
 * What the day book needs to know about one island, as rolled by {@code island_chemistry.profile(deed, realm)}.
 * Kept as plain facts so the day book does not depend on a chemistry port: the server (or the parity fixture)
 * fills it from the same seed.
 *
 * @param deed            plot number (seeds the day's draws)
 * @param fish            {@code chem.water.fish}, in chemistry order
 * @param starmetalCrater {@code chem.geology.starmetal_crater}
 * @param orchardFruits   fruit of each {@code chem.flora.orchard} species, in chemistry order
 * @param makeable        what this island can grow, dig or raise (crops, herbs, ores here, fruit, livestock yields,
 *                        crystal, plank)
 * @param need            {@code chem.economy.need}: the price family the island lacks
 * @param catalog         {@code colony_ledger.catalog(realm)}, sorted
 */
public record IslandFacts(int deed, List<String> fish, boolean starmetalCrater, List<String> orchardFruits,
        Set<String> makeable, String need, List<String> catalog) {
    public IslandFacts {
        fish = List.copyOf(fish);
        orchardFruits = List.copyOf(orchardFruits);
        makeable = Set.copyOf(makeable);
        catalog = List.copyOf(catalog);
    }
}
