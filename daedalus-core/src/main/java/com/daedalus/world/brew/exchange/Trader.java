// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.exchange;

import java.util.List;

/**
 * A neighbour on another fragment who barters for pressed record copies.
 *
 * @param id     NPC key, e.g. {@code pell}
 * @param name   display name
 * @param good   the store item they pay in, e.g. {@code rope}
 * @param wants  how many tunes they ask for each day (seeded)
 */
public record Trader(String id, String name, String good, int wants) {
    public Trader {
        if (id == null || id.isBlank() || name == null || good == null || good.isBlank() || wants < 0) {
            throw new IllegalArgumentException("trader needs id, name, good and wants >= 0");
        }
    }

    /** The four neighbours of Youtube Master Island. */
    public static List<Trader> island() {
        return List.of(
                new Trader("pell", "Pell the rope-maker", "rope", 2),
                new Trader("ida", "Quarry Ida", "choir_stone_blank", 1),
                new Trader("mora", "Hen-wife Mora", "Egg", 2),
                new Trader("dov", "Fisher Dov", "fish", 2));
    }
}
