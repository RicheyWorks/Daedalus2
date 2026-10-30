// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.List;

/**
 * Ark names: a colour or quality plus a sky creature, chosen by the launching island's seed.
 * Original pairings, not a franchise's ship names. Same seed, same name, on every JVM.
 */
public final class ArkNames {

    public static final List<String> FIRST = List.of(
            "Amber", "Gilded", "Copper", "Saffron", "Cobalt", "Ivory", "Rose", "Ember",
            "Verdant", "Silver", "Dusk", "Morning", "Lantern", "Thistle", "Tide", "Hollow");
    public static final List<String> SECOND = List.of(
            "Heron", "Wren", "Kestrel", "Albatross", "Swift", "Lark", "Petrel", "Tern",
            "Osprey", "Finch", "Plover", "Moth", "Kite", "Starling", "Gannet", "Shrike");

    private ArkNames() {
    }

    public static String of(long seed) {
        long h = seed * 0x9E3779B97F4A7C15L;
        h ^= h >>> 29;
        h *= 0xBF58476D1CE4E5B9L;
        h ^= h >>> 32;
        int a = (int) Math.floorMod(h, (long) FIRST.size());
        int b = (int) Math.floorMod(h >>> 16, (long) SECOND.size());
        return FIRST.get(a) + " " + SECOND.get(b);
    }
}
