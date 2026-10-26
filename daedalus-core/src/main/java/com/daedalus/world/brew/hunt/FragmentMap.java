// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.hunt;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.SplittableRandom;
import java.util.TreeSet;

/**
 * The broken shelf of Youtube Master Island: fragments of land joined by rope bridges. Fragment 0 is the homestead.
 * A seeded random spanning tree keeps every fragment reachable; a few extra bridges make loops. Distances are in
 * bridges (breadth-first search), and {@link #nextStep} names the neighbour on a shortest route.
 */
public final class FragmentMap {
    public static final int MIN_FRAGMENTS = 4;
    public static final int MAX_FRAGMENTS = 64;
    public static final int HOME = 0;

    private static final String[] NAMES = {"Homestead", "Reed Shelf", "Goat Rock", "Keel Drift", "Bell Ledge",
        "Mist Step", "Lantern Isle", "Choir Stone", "Cloudfoot", "Needle Spur", "Summit Shard", "Ferry Knoll",
        "Willow Crumb", "Ash Tooth", "Kite Perch", "Hollow Bell"};

    private final List<TreeSet<Integer>> links;
    private final int[][] dist;

    private FragmentMap(List<TreeSet<Integer>> links) {
        this.links = links;
        int n = links.size();
        dist = new int[n][];
        for (int s = 0; s < n; s++) {
            dist[s] = bfs(s);
        }
    }

    /** Seeded map: {@code n} fragments, a random spanning tree plus about n/4 extra bridges. */
    public static FragmentMap seeded(long seed, int n) {
        if (n < MIN_FRAGMENTS || n > MAX_FRAGMENTS) {
            throw new IllegalArgumentException("fragments " + MIN_FRAGMENTS + ".." + MAX_FRAGMENTS + ": " + n);
        }
        SplittableRandom rng = new SplittableRandom(seed);
        List<TreeSet<Integer>> links = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            links.add(new TreeSet<>());
        }
        for (int i = 1; i < n; i++) {
            int j = rng.nextInt(i);
            links.get(i).add(j);
            links.get(j).add(i);
        }
        for (int extra = 0; extra < n / 4; extra++) {
            int a = rng.nextInt(n);
            int b = rng.nextInt(n);
            if (a != b) {
                links.get(a).add(b);
                links.get(b).add(a);
            }
        }
        return new FragmentMap(links);
    }

    /** A map from explicit bridges (for hosts with hand-built islands); must be connected. */
    public static FragmentMap of(int n, int[][] bridges) {
        if (n < 1 || n > MAX_FRAGMENTS) {
            throw new IllegalArgumentException("fragments 1.." + MAX_FRAGMENTS + ": " + n);
        }
        List<TreeSet<Integer>> links = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            links.add(new TreeSet<>());
        }
        for (int[] b : bridges) {
            if (b.length != 2 || b[0] == b[1] || b[0] < 0 || b[1] < 0 || b[0] >= n || b[1] >= n) {
                throw new IllegalArgumentException("bad bridge " + Arrays.toString(b));
            }
            links.get(b[0]).add(b[1]);
            links.get(b[1]).add(b[0]);
        }
        FragmentMap m = new FragmentMap(links);
        for (int d : m.dist[HOME]) {
            if (d < 0) {
                throw new IllegalArgumentException("every fragment must be reachable from the homestead");
            }
        }
        return m;
    }

    private int[] bfs(int s) {
        int[] d = new int[links.size()];
        Arrays.fill(d, -1);
        d[s] = 0;
        ArrayDeque<Integer> q = new ArrayDeque<>();
        q.add(s);
        while (!q.isEmpty()) {
            int u = q.poll();
            for (int v : links.get(u)) {
                if (d[v] < 0) {
                    d[v] = d[u] + 1;
                    q.add(v);
                }
            }
        }
        return d;
    }

    public int size() {
        return links.size();
    }

    public List<Integer> neighbours(int f) {
        return List.copyOf(links.get(f));
    }

    public boolean bridged(int a, int b) {
        return a >= 0 && a < size() && links.get(a).contains(b);
    }

    /** Bridges between two fragments. */
    public int distance(int a, int b) {
        return dist[a][b];
    }

    /** The lowest-numbered neighbour of {@code from} on a shortest route to {@code to}; {@code from} if equal. */
    public int nextStep(int from, int to) {
        if (from == to) {
            return from;
        }
        for (int v : links.get(from)) {
            if (dist[v][to] == dist[from][to] - 1) {
                return v;
            }
        }
        throw new IllegalStateException("unreachable " + to);
    }

    /** Display name of a fragment. */
    public static String name(int f) {
        if (f < NAMES.length) {
            return NAMES[f];
        }
        int k = f - NAMES.length;
        return NAMES[1 + k % (NAMES.length - 1)] + " " + (2 + k / (NAMES.length - 1));
    }
}
