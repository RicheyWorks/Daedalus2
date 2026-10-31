// SPDX-License-Identifier: MIT

package com.daedalus.mazegame;

import java.util.Locale;

/**
 * Labyrinth Run difficulty ladder. Each tier pins a square size and a core generator id, so
 * (seed, difficulty) always names exactly one maze. Only Brutal plays under fog of war.
 */
public enum Difficulty {
    EASY('E', 15, "recursive-backtracker", false),
    NORMAL('N', 25, "prims", false),
    HARD('H', 41, "wilsons", false),
    BRUTAL('B', 61, "ellers", true);

    /** Cells visible around the runner (Chebyshev radius) when fog is on. */
    public static final int FOG_RADIUS = 3;

    private final char code;
    private final int size;
    private final String generatorId;
    private final boolean fog;

    Difficulty(char code, int size, String generatorId, boolean fog) {
        this.code = code;
        this.size = size;
        this.generatorId = generatorId;
        this.fog = fog;
    }

    public char code() { return code; }
    public int size() { return size; }
    public String generatorId() { return generatorId; }
    public boolean fog() { return fog; }

    /** Looks a tier up by its share-code letter or its name (case-insensitive). */
    public static Difficulty parse(String text) {
        String t = text.trim().toUpperCase(Locale.ROOT);
        for (Difficulty d : values()) {
            if (d.name().equals(t) || (t.length() == 1 && t.charAt(0) == d.code)) {
                return d;
            }
        }
        throw new IllegalArgumentException("Unknown difficulty: " + text);
    }
}
