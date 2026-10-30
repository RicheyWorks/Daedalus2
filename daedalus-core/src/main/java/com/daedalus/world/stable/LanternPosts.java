// SPDX-License-Identifier: MIT

package com.daedalus.world.stable;

import java.util.Arrays;
import java.util.SplittableRandom;

/**
 * G540 Lantern Posts (Studio horse lane, the stable yard at night): the yard's paths form a tree of
 * junctions (junction 0 is the barn door; junction i hangs off {@code parent[i] < i}). A lantern
 * hung at a junction costs that junction's price and can light at most {@code reach} of the paths
 * that meet there. Light every path at the least cost (capacitated weighted vertex cover on a tree).
 * {@link #best} is an exact tree DP: for each junction, unlit, lit without its parent path, or lit
 * including its parent path, and a lit junction takes over the child paths that save the most.
 * {@link #busiestFirst} (hang the next lantern where it lights the most dark paths per coin) pays
 * more or leaves a path dark. Plain int[] API; small and pure so it can be ported to C++ for Unreal.
 */
public final class LanternPosts {

    public static final String QUEST_ID = "q_paths_lit";
    public static final int INFEASIBLE = -1;
    private static final long INF = Long.MAX_VALUE / 4;

    /** A lighting plan: total cost and, for each path i (junction i to parent[i], i >= 1), the junction that lights it. */
    public record Plan(int cost, int[] lighter) {
        public Plan {
            lighter = lighter.clone();
        }

        @Override
        public int[] lighter() {
            return lighter.clone();
        }

        @Override
        public boolean equals(Object o) {
            return o instanceof Plan p && p.cost == cost && Arrays.equals(p.lighter, lighter);
        }

        @Override
        public int hashCode() {
            return 31 * cost + Arrays.hashCode(lighter);
        }

        @Override
        public String toString() {
            return "Plan[" + cost + ", " + Arrays.toString(lighter) + "]";
        }
    }

    private LanternPosts() { }

    /** Seeded tree: parent[0] = -1, parent[i] uniform in [0, i). */
    public static int[] yard(long seed, int n) {
        if (n < 1 || n > 4096) {
            throw new IllegalArgumentException("bad yard size");
        }
        SplittableRandom rnd = new SplittableRandom(seed);
        int[] parent = new int[n];
        parent[0] = -1;
        for (int i = 1; i < n; i++) {
            parent[i] = rnd.nextInt(i);
        }
        return parent;
    }

    /** Seeded lantern prices in [1, maxPrice]. */
    public static int[] prices(long seed, int n, int maxPrice) {
        if (n < 1 || maxPrice < 1) {
            throw new IllegalArgumentException("bad prices");
        }
        SplittableRandom rnd = new SplittableRandom(seed ^ 0xBB67AE8584CAA73BL);
        int[] p = new int[n];
        for (int i = 0; i < n; i++) {
            p[i] = 1 + rnd.nextInt(maxPrice);
        }
        return p;
    }

    /** Cheapest lighting of every path (exact tree DP), or INFEASIBLE when the reach is too small. */
    public static Plan best(int[] parent, int[] price, int reach) {
        check(parent, price, reach);
        int n = parent.length;
        long[][] f = new long[3][n];
        for (int v = n - 1; v >= 0; v--) {
            long own = 0;
            for (int c = v + 1; c < n; c++) {
                if (parent[c] == v) {
                    own = Math.min(INF, own + f[2][c]);
                }
            }
            f[0][v] = own;
            f[1][v] = lit(parent, price, f, v, reach, null);
            f[2][v] = reach >= 1 ? lit(parent, price, f, v, reach - 1, null) : INF;
        }
        long total = Math.min(f[0][0], f[1][0]);
        if (total >= INF) {
            return new Plan(INFEASIBLE, new int[0]);
        }
        int[] lighter = new int[n];
        lighter[0] = -1;
        int[] state = new int[n];
        state[0] = f[0][0] <= f[1][0] ? 0 : 1;
        for (int v = 0; v < n; v++) {
            boolean[] mine = new boolean[n];
            if (state[v] != 0) {
                lit(parent, price, f, v, state[v] == 1 ? reach : reach - 1, mine);
            }
            for (int c = v + 1; c < n; c++) {
                if (parent[c] == v) {
                    if (mine[c]) {
                        lighter[c] = v;
                        state[c] = f[0][c] <= f[1][c] ? 0 : 1;
                    } else {
                        lighter[c] = c;
                        state[c] = 2;
                    }
                }
            }
        }
        return new Plan((int) total, lighter);
    }

    /** Cost of v lit with {@code slots} child paths it may light; marks chosen children in {@code mine}. */
    private static long lit(int[] parent, int[] price, long[][] f, int v, int slots, boolean[] mine) {
        int n = parent.length;
        long sum = price[v];
        int forced = 0;
        long[] gain = new long[n];
        int[] who = new int[n];
        int g = 0;
        for (int c = v + 1; c < n; c++) {
            if (parent[c] != v) {
                continue;
            }
            long byV = Math.min(f[0][c], f[1][c]);
            long own = f[2][c];
            if (own >= INF) {
                forced++;
                sum = Math.min(INF, sum + byV);
                if (mine != null) {
                    mine[c] = true;
                }
            } else {
                sum = Math.min(INF, sum + own);
                if (byV < own) {
                    gain[g] = own - byV;
                    who[g] = c;
                    g++;
                }
            }
        }
        if (forced > slots || sum >= INF) {
            return INF;
        }
        int free = slots - forced;
        boolean[] used = new boolean[g];
        for (int k = 0; k < free; k++) {
            int pick = -1;
            for (int i = 0; i < g; i++) {
                if (!used[i] && (pick < 0 || gain[i] > gain[pick])) {
                    pick = i;
                }
            }
            if (pick < 0) {
                break;
            }
            used[pick] = true;
            sum -= gain[pick];
            if (mine != null) {
                mine[who[pick]] = true;
            }
        }
        return sum;
    }

    /** Naive habit: hang the next lantern where it lights the most dark paths per coin (ties to lower id). */
    public static Plan busiestFirst(int[] parent, int[] price, int reach) {
        check(parent, price, reach);
        int n = parent.length;
        int[] lighter = new int[n];
        Arrays.fill(lighter, -2);
        lighter[0] = -1;
        boolean[] hung = new boolean[n];
        int dark = n - 1;
        int cost = 0;
        while (dark > 0) {
            int pick = -1;
            int pickGain = 0;
            for (int v = 0; v < n; v++) {
                if (hung[v]) {
                    continue;
                }
                int gain = Math.min(reach, darkAt(parent, lighter, v));
                if (gain > 0 && (pick < 0 || (long) gain * price[pick] > (long) pickGain * price[v])) {
                    pick = v;
                    pickGain = gain;
                }
            }
            if (pick < 0) {
                return new Plan(INFEASIBLE, new int[0]);
            }
            hung[pick] = true;
            cost += price[pick];
            int left = reach;
            for (int e = 1; e < n && left > 0; e++) {
                if (lighter[e] == -2 && (e == pick || parent[e] == pick)) {
                    lighter[e] = pick;
                    left--;
                    dark--;
                }
            }
        }
        return new Plan(cost, lighter);
    }

    private static int darkAt(int[] parent, int[] lighter, int v) {
        int d = 0;
        for (int e = 1; e < parent.length; e++) {
            if (lighter[e] == -2 && (e == v || parent[e] == v)) {
                d++;
            }
        }
        return d;
    }

    /** Cost of a plan, or INFEASIBLE when a path is dark, lit from a junction it does not touch, or a lantern is overloaded. */
    public static int light(int[] parent, int[] price, int reach, int[] lighter) {
        check(parent, price, reach);
        int n = parent.length;
        if (lighter.length != n) {
            return INFEASIBLE;
        }
        int[] load = new int[n];
        for (int e = 1; e < n; e++) {
            int v = lighter[e];
            if (v != e && v != parent[e]) {
                return INFEASIBLE;
            }
            load[v]++;
            if (load[v] > reach) {
                return INFEASIBLE;
            }
        }
        int cost = 0;
        for (int v = 0; v < n; v++) {
            if (load[v] > 0) {
                cost += price[v];
            }
        }
        return cost;
    }

    /** Quest q_paths_lit: every yard path is lit legally at the least cost. */
    public static boolean quest(int[] parent, int[] price, int reach, int[] lighter) {
        int got = light(parent, price, reach, lighter);
        return got != INFEASIBLE && got == best(parent, price, reach).cost();
    }

    private static void check(int[] parent, int[] price, int reach) {
        int n = parent.length;
        if (n < 1 || price.length != n || reach < 0 || parent[0] != -1) {
            throw new IllegalArgumentException("bad yard");
        }
        for (int i = 1; i < n; i++) {
            if (parent[i] < 0 || parent[i] >= i) {
                throw new IllegalArgumentException("parent must be an earlier junction: " + i);
            }
        }
        for (int p : price) {
            if (p < 1) {
                throw new IllegalArgumentException("price must be positive");
            }
        }
    }
}
