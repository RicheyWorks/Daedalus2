// SPDX-License-Identifier: MIT

package com.daedalus.world;

import java.util.Collection;
import java.util.List;
import java.util.Set;

/**
 * Inspired toponyms for stamped plots. Not GIS, not a trademarked venue.
 */
public final class PlaceNames {

    public static final List<String> STREETS = List.of(
            "Willow Walk",
            "Lantern Lane",
            "Ash Court",
            "Cobble Close",
            "Reed Terrace",
            "Ember Alley",
            "Moss Passage",
            "Cedar Reach",
            "Iron Gate",
            "Quiet Yard");

    private PlaceNames() {
    }

    public static String of(String key) {
        return of(key, List.of());
    }

    public static String of(String key, Collection<String> taken) {
        String seed = key == null ? "" : key;
        int start = Math.floorMod(seed.hashCode(), STREETS.size());
        Set<String> used = taken == null ? Set.of() : Set.copyOf(taken);
        for (int i = 0; i < STREETS.size(); i++) {
            String name = STREETS.get((start + i) % STREETS.size());
            if (!used.contains(name)) {
                return name;
            }
        }
        return STREETS.get(start) + " " + (used.size() + 1);
    }
}
