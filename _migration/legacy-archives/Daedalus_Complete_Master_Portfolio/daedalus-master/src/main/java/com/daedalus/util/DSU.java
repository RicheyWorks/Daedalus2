package com.daedalus.util;

import java.util.HashMap;
import java.util.Map;

/**
 * Generic Union-Find (DSU) with path compression and union by rank.
 * Used by KruskalsGenerator and BoruvkasGenerator.
 */
public class DSU<T> {

    private final Map<T, T> parent = new HashMap<>();
    private final Map<T, Integer> rank = new HashMap<>();

    public T find(T x) {
        if (!parent.containsKey(x)) parent.put(x, x);
        T root = parent.get(x);
        if (!root.equals(parent.get(root))) {
            parent.put(root, find(parent.get(root))); // path compression
        }
        return parent.get(root);
    }

    public void union(T x, T y) {
        T rx = find(x), ry = find(y);
        if (rx.equals(ry)) return;

        int rxRank = rank.getOrDefault(rx, 0);
        int ryRank = rank.getOrDefault(ry, 0);

        if (rxRank < ryRank) {
            parent.put(rx, ry);
        } else if (ryRank < rxRank) {
            parent.put(ry, rx);
        } else {
            parent.put(ry, rx);
            rank.put(rx, rxRank + 1);
        }
    }
}