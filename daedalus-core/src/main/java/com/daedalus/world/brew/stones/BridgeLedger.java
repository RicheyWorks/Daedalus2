// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.stones;

import com.daedalus.world.brew.hunt.FragmentMap;
import com.daedalus.world.colony.PlotState;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;

/**
 * Strength of every rope bridge of a {@link FragmentMap}. Bridges start at {@link #MAX_STRENGTH}; a tremor frays one
 * by 1 and at 0 it snaps (cannot be crossed). Re-stringing a snapped or frayed bridge costs {@link #ROPE_PER_BRIDGE}
 * {@link #ROPE} from the plot store and restores it to full.
 */
public final class BridgeLedger {
    public static final int MAX_STRENGTH = 3;
    public static final String ROPE = "rope";
    public static final int ROPE_PER_BRIDGE = 2;

    /** One bridge, always stored with {@code a < b}. */
    public record Bridge(int a, int b) implements Comparable<Bridge> {
        public static Bridge of(int x, int y) {
            return new Bridge(Math.min(x, y), Math.max(x, y));
        }

        @Override
        public int compareTo(Bridge o) {
            return a != o.a ? Integer.compare(a, o.a) : Integer.compare(b, o.b);
        }
    }

    private final FragmentMap map;
    private final TreeMap<Bridge, Integer> strength = new TreeMap<>();

    public BridgeLedger(FragmentMap map) {
        this.map = map;
        for (int a = 0; a < map.size(); a++) {
            for (int b : map.neighbours(a)) {
                if (a < b) {
                    strength.put(new Bridge(a, b), MAX_STRENGTH);
                }
            }
        }
    }

    public FragmentMap map() {
        return map;
    }

    /** Every bridge in order. */
    public List<Bridge> bridges() {
        return List.copyOf(strength.keySet());
    }

    /** Strength of a bridge, or -1 when there is no bridge. */
    public int strength(int x, int y) {
        return strength.getOrDefault(Bridge.of(x, y), -1);
    }

    public boolean intact(int x, int y) {
        return strength(x, y) > 0;
    }

    /** Frays a bridge by one; returns true if it snapped just now. */
    boolean fray(Bridge b) {
        int s = strength.get(b);
        if (s == 0) {
            return false;
        }
        strength.put(b, s - 1);
        return s == 1;
    }

    /** Re-strings a bridge to full strength from the plot's rope; false if no bridge, already full, or no rope. */
    public boolean restring(int x, int y, PlotState plot) {
        int s = strength(x, y);
        if (s < 0 || s == MAX_STRENGTH || plot == null || plot.count(ROPE) < ROPE_PER_BRIDGE) {
            return false;
        }
        plot.take(ROPE, ROPE_PER_BRIDGE);
        strength.put(Bridge.of(x, y), MAX_STRENGTH);
        return true;
    }

    /** Fragments that cannot reach the homestead over intact bridges, in order. */
    public Set<Integer> cutOff() {
        boolean[] seen = new boolean[map.size()];
        ArrayDeque<Integer> q = new ArrayDeque<>();
        seen[FragmentMap.HOME] = true;
        q.add(FragmentMap.HOME);
        while (!q.isEmpty()) {
            int u = q.poll();
            for (int v : map.neighbours(u)) {
                if (!seen[v] && intact(u, v)) {
                    seen[v] = true;
                    q.add(v);
                }
            }
        }
        Set<Integer> out = new TreeSet<>();
        for (int f = 0; f < seen.length; f++) {
            if (!seen[f]) {
                out.add(f);
            }
        }
        return out;
    }

    /** Snapshot of all strengths (bridge -> strength). */
    public Map<Bridge, Integer> snapshot() {
        return new TreeMap<>(strength);
    }

    List<Bridge> intactBridges() {
        List<Bridge> out = new ArrayList<>();
        strength.forEach((b, s) -> {
            if (s > 0) {
                out.add(b);
            }
        });
        return out;
    }
}
