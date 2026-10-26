// SPDX-License-Identifier: MIT

package com.daedalus.world.colony;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Set;

/** Mutable per-plot state the day book touches: the island store, the museum collection and charm. */
public final class PlotState {
    private final Map<String, Double> store = new LinkedHashMap<>();
    private final Set<String> collection = new LinkedHashSet<>();
    private double charm;

    public void add(String item, double n) {
        store.merge(item, n, Double::sum);
    }

    /** Takes n units if the store has them; false (and no change) otherwise. */
    public boolean take(String item, double n) {
        double have = store.getOrDefault(item, 0.0);
        if (have < n) {
            return false;
        }
        store.put(item, have - n);
        return true;
    }

    public double count(String item) {
        return store.getOrDefault(item, 0.0);
    }

    /** True if the item has ever entered the store (Python's {@code item in p.store}). */
    public boolean hasLine(String item) {
        return store.containsKey(item);
    }

    public Map<String, Double> store() {
        return Collections.unmodifiableMap(store);
    }

    public Set<String> collection() {
        return Collections.unmodifiableSet(collection);
    }

    boolean collect(String item) {
        return collection.add(item);
    }

    public double charm() {
        return charm;
    }

    void addCharm(double c) {
        charm += c;
    }
}
