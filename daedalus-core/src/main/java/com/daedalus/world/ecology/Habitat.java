// SPDX-License-Identifier: MIT

package com.daedalus.world.ecology;

import com.daedalus.world.island.IslandTraits;

import java.util.EnumMap;
import java.util.Map;

/**
 * How much of each guild's living space an island offers, in habitat cells (ADR-022). Read off the
 * island's own traits, so a pond-heavy island and a forested one host different communities.
 *
 * <ul>
 *   <li>CANOPY — 12 cells per tree (a crown and the air around it)</li>
 *   <li>POND — every pond and stream column</li>
 *   <li>MEADOW — open ground: the footprint less pond, stream and the trees' shade</li>
 *   <li>DECOMPOSER — a third of the footprint (the soil under everything)</li>
 *   <li>STARBORN — 6 cells per hanging crystal</li>
 *   <li>MARINE — none: the sea fell away</li>
 * </ul>
 */
public record Habitat(Map<Guild, Double> cells) {

    public Habitat {
        EnumMap<Guild, Double> copy = new EnumMap<>(Guild.class);
        for (Guild g : Guild.values()) {
            double v = cells == null ? 0 : cells.getOrDefault(g, 0.0);
            if (v < 0 || Double.isNaN(v)) {
                throw new IllegalArgumentException("habitat cells must be >= 0 for " + g);
            }
            copy.put(g, v);
        }
        cells = Map.copyOf(copy);
    }

    public static Habitat of(IslandTraits t) {
        Map<Guild, Double> c = new EnumMap<>(Guild.class);
        double water = t.pondColumns() + t.streamLength();
        c.put(Guild.CANOPY, 12.0 * t.trees());
        c.put(Guild.POND, water);
        c.put(Guild.MEADOW, Math.max(0.0, t.columns() - water - 9.0 * t.trees()));
        c.put(Guild.DECOMPOSER, t.columns() / 3.0);
        c.put(Guild.STARBORN, 6.0 * t.crystals());
        c.put(Guild.MARINE, 0.0);
        return new Habitat(c);
    }

    public double of(Guild g) {
        return cells.get(g);
    }

    /** Total living space — the island's "area" in MacArthur–Wilson terms. */
    public double area() {
        double sum = 0;
        for (double v : cells.values()) {
            sum += v;
        }
        return sum;
    }
}
