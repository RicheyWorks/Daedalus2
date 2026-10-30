// SPDX-License-Identifier: MIT

package com.daedalus.world.stable;

import java.util.ArrayDeque;
import java.util.Arrays;
import java.util.SplittableRandom;

/**
 * G548 Barn Upgrades (Studio horse lane): seeded stable upgrades each earn coin (a hot-walker, a
 * wash bay) or only cost coin (new wiring, a water main), and some need others built first. Pick a
 * set of upgrades that includes every prerequisite of everything in it and earns the most net coin
 * (maximum-weight closure, also called project selection). {@link #best} is exact: a minimum cut
 * on the project-selection network (source to each earner, each cost to the sink, prerequisite
 * links uncuttable), found with Edmonds-Karp. {@link #oneAtATime} (build an upgrade whenever it
 * plus its missing prerequisites pays for itself, repeat until nothing does) misses prerequisites
 * that only pay when several earners share them. Plain arrays with prerequisite bitmasks, at most
 * 30 upgrades; small and pure so it ports to C++ for Unreal.
 */
public final class BarnUpgrades {

    public static final String QUEST_ID = "q_paying_barn";
    public static final int MAX_UPGRADES = 30;

    /** A build plan: net coin and the bitmask of upgrades built. */
    public record Build(long coin, int chosen) { }

    private BarnUpgrades() { }

    /**
     * Seeded upgrade values: the first {@code base} upgrades are groundwork that only costs (wiring, water
     * main) in [-maxCost, -1]; the rest earn in [1, maxGain].
     */
    public static int[] values(long seed, int n, int base, int maxGain, int maxCost) {
        if (n < 0 || n > MAX_UPGRADES || base < 0 || base > n || maxGain < 1 || maxCost < 1) {
            throw new IllegalArgumentException("bad upgrades");
        }
        SplittableRandom rnd = new SplittableRandom(seed);
        int[] v = new int[n];
        for (int i = 0; i < n; i++) {
            v[i] = i < base ? -1 - rnd.nextInt(maxCost) : 1 + rnd.nextInt(maxGain);
        }
        return v;
    }

    /** Seeded prerequisites: each earner (index >= base) needs each groundwork upgrade with probability percent/100. */
    public static int[] needs(long seed, int n, int base, int percent) {
        if (n < 0 || n > MAX_UPGRADES || base < 0 || base > n || percent < 0 || percent > 100) {
            throw new IllegalArgumentException("bad needs");
        }
        SplittableRandom rnd = new SplittableRandom(seed ^ 0x3C6EF372FE94F82BL);
        int[] need = new int[n];
        for (int i = base; i < n; i++) {
            for (int j = 0; j < base; j++) {
                if (rnd.nextInt(100) < percent) {
                    need[i] |= 1 << j;
                }
            }
        }
        return need;
    }

    /** Most net coin over all prerequisite-closed sets (min cut, Edmonds-Karp). */
    public static Build best(int[] value, int[] need) {
        check(value, need);
        int n = value.length;
        int s = n;
        int t = n + 1;
        int m = n + 2;
        long big = 1;
        long positive = 0;
        for (int v : value) {
            big += Math.abs(v);
            positive += Math.max(0, v);
        }
        long[][] cap = new long[m][m];
        for (int i = 0; i < n; i++) {
            if (value[i] > 0) {
                cap[s][i] = value[i];
            } else if (value[i] < 0) {
                cap[i][t] = -value[i];
            }
            for (int j = 0; j < n; j++) {
                if ((need[i] & (1 << j)) != 0) {
                    cap[i][j] = big;
                }
            }
        }
        long flow = 0;
        while (true) {
            int[] prev = new int[m];
            Arrays.fill(prev, -1);
            prev[s] = s;
            ArrayDeque<Integer> queue = new ArrayDeque<>();
            queue.add(s);
            while (!queue.isEmpty() && prev[t] < 0) {
                int u = queue.poll();
                for (int v = 0; v < m; v++) {
                    if (prev[v] < 0 && cap[u][v] > 0) {
                        prev[v] = u;
                        queue.add(v);
                    }
                }
            }
            if (prev[t] < 0) {
                int chosen = 0;
                for (int i = 0; i < n; i++) {
                    if (prev[i] >= 0) {
                        chosen |= 1 << i;
                    }
                }
                return new Build(positive - flow, chosen);
            }
            long push = Long.MAX_VALUE;
            for (int v = t; v != s; v = prev[v]) {
                push = Math.min(push, cap[prev[v]][v]);
            }
            for (int v = t; v != s; v = prev[v]) {
                cap[prev[v]][v] -= push;
                cap[v][prev[v]] += push;
            }
            flow += push;
        }
    }

    /** Naive habit: build any upgrade whose own value plus its missing prerequisites is positive; repeat. */
    public static Build oneAtATime(int[] value, int[] need) {
        check(value, need);
        int n = value.length;
        int built = 0;
        boolean grew = true;
        while (grew) {
            grew = false;
            for (int i = 0; i < n; i++) {
                if ((built & (1 << i)) != 0) {
                    continue;
                }
                int add = closure(need, 1 << i) & ~built;
                if (coin(value, add) > 0) {
                    built |= add;
                    grew = true;
                }
            }
        }
        return new Build(coin(value, built), built);
    }

    /** Smallest prerequisite-closed set containing {@code mask}. */
    public static int closure(int[] need, int mask) {
        int c = mask;
        boolean grew = true;
        while (grew) {
            grew = false;
            for (int i = 0; i < need.length; i++) {
                if ((c & (1 << i)) != 0 && (need[i] & ~c) != 0) {
                    c |= need[i];
                    grew = true;
                }
            }
        }
        return c;
    }

    /** True when every prerequisite of every chosen upgrade is chosen too. */
    public static boolean closed(int[] need, int chosen) {
        for (int i = 0; i < need.length; i++) {
            if ((chosen & (1 << i)) != 0 && (need[i] & ~chosen) != 0) {
                return false;
            }
        }
        return true;
    }

    /** Net coin of a set (no closure check). */
    public static long coin(int[] value, int chosen) {
        long total = 0;
        for (int i = 0; i < value.length; i++) {
            if ((chosen & (1 << i)) != 0) {
                total += value[i];
            }
        }
        return total;
    }

    /** Quest q_paying_barn: the stable's plan has every prerequisite and earns the most coin. */
    public static boolean quest(int[] value, int[] need, int chosen) {
        check(value, need);
        return (chosen >>> value.length) == 0 && closed(need, chosen) && coin(value, chosen) == best(value, need).coin();
    }

    private static void check(int[] value, int[] need) {
        int n = value.length;
        if (n > MAX_UPGRADES || need.length != n) {
            throw new IllegalArgumentException("bad upgrades");
        }
        for (int i = 0; i < n; i++) {
            if ((need[i] >>> n) != 0 || (need[i] & (1 << i)) != 0) {
                throw new IllegalArgumentException("bad prerequisites for " + i);
            }
        }
    }
}
