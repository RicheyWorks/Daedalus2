// SPDX-License-Identifier: MIT

package com.daedalus.world.fishing;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * The angler's fish log for one table: how many of each kind were landed, "NEW!" the first time, progress
 * "kinds / total" and what the catch would fetch at the inn kitchen (sum of prices). Mutable, one per save.
 */
public final class FishLog {

    private final FishTable table;
    private final Map<String, Integer> counts = new LinkedHashMap<>();

    public FishLog(FishTable table) {
        if (table == null) {
            throw new IllegalArgumentException("a fish log needs a table");
        }
        this.table = table;
    }

    /** Logs one catch. Returns true when it is the first of its kind (the demo's "NEW!"). */
    public boolean record(FishSpecies fish) {
        if (fish == null || table.find(fish.name()).isEmpty()) {
            throw new IllegalArgumentException("fish " + fish + " is not in the " + table.realm() + " table");
        }
        int before = counts.getOrDefault(fish.name(), 0);
        counts.put(fish.name(), before + 1);
        return before == 0;
    }

    /** Logs a finished cast if it CAUGHT something. Returns true only for a first-of-kind catch. */
    public boolean record(CastSession cast) {
        if (cast.outcome() != CastSession.Outcome.CAUGHT) {
            return false;
        }
        return record(cast.fish().orElseThrow());
    }

    public int count(String name) {
        return counts.getOrDefault(name, 0);
    }

    /** Kinds landed at least once. */
    public int kinds() {
        return counts.size();
    }

    /** Every fish landed. */
    public int total() {
        int n = 0;
        for (int c : counts.values()) {
            n += c;
        }
        return n;
    }

    public boolean complete() {
        return counts.size() == table.size();
    }

    /** "3 / 6", the demo's log header. */
    public String progress() {
        return kinds() + " / " + table.size();
    }

    /** What the whole catch sells for. */
    public int value() {
        int v = 0;
        for (Map.Entry<String, Integer> e : counts.entrySet()) {
            v += table.require(e.getKey()).price() * e.getValue();
        }
        return v;
    }

    /** Counts by name, in first-caught order. A read-only snapshot. */
    public Map<String, Integer> counts() {
        return Collections.unmodifiableMap(new LinkedHashMap<>(counts));
    }
}
