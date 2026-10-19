// SPDX-License-Identifier: MIT

package com.daedalus.world.fishing;

import java.util.Locale;

/** How rare a fish is, in the words the fish tables use. RARE and LEGENDARY are the ones a storm stirs up. */
public enum Rarity {
    COMMON, UNCOMMON, RARE, LEGENDARY;

    /** True for RARE and LEGENDARY. */
    public boolean isRare() {
        return compareTo(RARE) >= 0;
    }

    /** Parses a table's rarity word, case-insensitively. */
    public static Rarity parse(String word) {
        if (word == null) {
            throw new IllegalArgumentException("fish rarity is missing");
        }
        try {
            return valueOf(word.trim().toUpperCase(Locale.ROOT));
        } catch (IllegalArgumentException e) {
            throw new IllegalArgumentException("unknown fish rarity '" + word + "'", e);
        }
    }
}
