// SPDX-License-Identifier: MIT
package com.daedalus.world.gallery;

import java.util.EnumMap;
import java.util.Map;

/**
 * A painter's pigment pots. Grinding turns one chemistry ingredient into one unit of its pigment; mixing turns one
 * unit of each primary into one unit of the secondary, only when the painter knows both primaries. The host owns
 * the ingredient inventory; this class only tracks pigment units.
 */
public final class PigmentPalette {

    public static final int MAX_UNITS = 999;

    public enum Result { OK, UNKNOWN_INGREDIENT, NOT_KNOWN, MISSING_PRIMARY, FULL }

    private final EnumMap<Pigment, Integer> units = new EnumMap<>(Pigment.class);

    /** Grinds one ingredient (e.g. "beet", "cobalt") into one pigment unit. */
    public synchronized Result grind(String ingredient) {
        return Pigment.fromIngredient(ingredient).map(this::add).orElse(Result.UNKNOWN_INGREDIENT);
    }

    /** Mixes one secondary unit from one unit of each of its primaries. */
    public synchronized Result mix(Pigment secondary, ColourKnowledge knowledge) {
        if (secondary.primary() || !knowledge.canMix(secondary)) return Result.NOT_KNOWN;
        for (Pigment c : secondary.components()) if (count(c) == 0) return Result.MISSING_PRIMARY;
        if (count(secondary) >= MAX_UNITS) return Result.FULL;
        for (Pigment c : secondary.components()) units.merge(c, -1, Integer::sum);
        units.merge(secondary, 1, Integer::sum);
        return Result.OK;
    }

    /** Spends one unit; false when the pot is empty. */
    public synchronized boolean spend(Pigment p) {
        if (count(p) == 0) return false;
        units.merge(p, -1, Integer::sum);
        return true;
    }

    public synchronized int count(Pigment p) { return units.getOrDefault(p, 0); }

    public synchronized Map<Pigment, Integer> snapshot() { return Map.copyOf(units); }

    private Result add(Pigment p) {
        if (count(p) >= MAX_UNITS) return Result.FULL;
        units.merge(p, 1, Integer::sum);
        return Result.OK;
    }
}
