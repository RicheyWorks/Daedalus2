// SPDX-License-Identifier: MIT

package com.daedalus.world.ecology;

/**
 * One kind of creature, plant or fungus (ADR-021). The identity fields come from the ComputerPets
 * catalog; the ecology fields are assigned by {@code tools/canon/build_species.py}.
 *
 * @param rarity     COMMON, UNCOMMON, RARE or LEGENDARY — how often an ark's hold carries it
 * @param size       TINY, SMALL, MEDIUM, LARGE or SESSILE (rooted)
 * @param strategy   R or K: many fast young, or few slow ones
 * @param disperses  crosses open sky alone (wings, spores, wind); otherwise it needs an ark
 */
public record Species(String key, String name, String rarity, String temperament, Guild guild,
                      String size, char strategy, boolean disperses) {

    public boolean rSelected() {
        return strategy == 'R';
    }
}
