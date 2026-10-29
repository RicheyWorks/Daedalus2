// SPDX-License-Identifier: MIT

package com.daedalus.world.stable;

import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;
import java.util.SplittableRandom;

/**
 * G523 Paddock Rotation (Studio horse lane): the stable's herd grazes exactly one paddock per day
 * for {@code days} days. Paddock {@code p} regrows {@code growth[p]} grass per rest day up to its
 * cap {@code cap[p]}; grazing eats all of it and resets that paddock's rest. All paddocks start
 * full. {@link #best} plans the season with the most grass eaten, using an exact dynamic program
 * over (day, rest counters), with each counter clamped at the day its paddock is full again;
 * {@link #greedy} (always graze the fullest paddock today) is the habit that strips the fast
 * paddocks early and leaves the herd on stubble. Plain int[] API.
 */
public final class PaddockRotation {

    public static final String QUEST_ID = "q_green_pasture";

    /** A grazing season: total grass eaten and the paddock grazed on each day. */
    public record Season(int grass, int[] plan) {
        public Season {
            plan = plan.clone();
        }

        @Override
        public int[] plan() {
            return plan.clone();
        }

        @Override
        public boolean equals(Object o) {
            return o instanceof Season s && s.grass == grass && Arrays.equals(s.plan, plan);
        }

        @Override
        public int hashCode() {
            return 31 * grass + Arrays.hashCode(plan);
        }

        @Override
        public String toString() {
            return "Season[" + grass + ", " + Arrays.toString(plan) + "]";
        }
    }

    private PaddockRotation() { }

    /** Seeded caps in [growth, 12] and growth in [1, 4] for {@code m} paddocks; index 0 = cap, 1 = growth. */
    public static int[][] paddocks(long seed, int m) {
        if (m <= 0) {
            throw new IllegalArgumentException("bad paddocks");
        }
        SplittableRandom rnd = new SplittableRandom(seed);
        int[] cap = new int[m];
        int[] growth = new int[m];
        for (int p = 0; p < m; p++) {
            growth[p] = 1 + rnd.nextInt(4);
            cap[p] = growth[p] + rnd.nextInt(13 - growth[p]);
        }
        return new int[][] {cap, growth};
    }

    /** Most grass the herd can eat over {@code days} days. */
    public static Season best(int[] cap, int[] growth, int days) {
        int[] full = check(cap, growth, days);
        int m = cap.length;
        Map<Long, Integer> memo = new HashMap<>();
        int[] rest = full.clone();
        int total = solve(cap, growth, full, rest, days, memo);
        int[] plan = new int[days];
        for (int d = 0; d < days; d++) {
            int left = days - d - 1;
            for (int p = 0; p < m; p++) {
                int[] next = step(full, rest, p);
                int v = grass(cap, growth, rest, p) + solve(cap, growth, full, next, left, memo);
                if (v == solve(cap, growth, full, rest, days - d, memo)) {
                    plan[d] = p;
                    rest = next;
                    break;
                }
            }
        }
        return new Season(total, plan);
    }

    /** Naive: graze the fullest paddock each day (lowest index on ties). */
    public static Season greedy(int[] cap, int[] growth, int days) {
        int[] full = check(cap, growth, days);
        int[] rest = full.clone();
        int[] plan = new int[days];
        int total = 0;
        for (int d = 0; d < days; d++) {
            int pick = 0;
            for (int p = 1; p < cap.length; p++) {
                if (grass(cap, growth, rest, p) > grass(cap, growth, rest, pick)) {
                    pick = p;
                }
            }
            total += grass(cap, growth, rest, pick);
            plan[d] = pick;
            rest = step(full, rest, pick);
        }
        return new Season(total, plan);
    }

    /** Grass eaten by a plan, or -1 when it has the wrong length or names a missing paddock. */
    public static int graze(int[] cap, int[] growth, int[] plan, int days) {
        int[] full = check(cap, growth, days);
        if (plan.length != days) {
            return -1;
        }
        int[] rest = full.clone();
        int total = 0;
        for (int p : plan) {
            if (p < 0 || p >= cap.length) {
                return -1;
            }
            total += grass(cap, growth, rest, p);
            rest = step(full, rest, p);
        }
        return total;
    }

    /** Quest q_green_pasture: the stable hand's plan is legal and eats as much grass as possible. */
    public static boolean quest(int[] cap, int[] growth, int[] plan, int days) {
        int got = graze(cap, growth, plan, days);
        return got >= 0 && got == best(cap, growth, days).grass();
    }

    private static int solve(int[] cap, int[] growth, int[] full, int[] rest, int left, Map<Long, Integer> memo) {
        if (left == 0) {
            return 0;
        }
        long key = left;
        for (int p = 0; p < rest.length; p++) {
            key = key * (full[p] + 1) + rest[p];
        }
        Integer hit = memo.get(key);
        if (hit != null) {
            return hit;
        }
        int bestValue = 0;
        for (int p = 0; p < rest.length; p++) {
            int v = grass(cap, growth, rest, p) + solve(cap, growth, full, step(full, rest, p), left - 1, memo);
            bestValue = Math.max(bestValue, v);
        }
        memo.put(key, bestValue);
        return bestValue;
    }

    private static int grass(int[] cap, int[] growth, int[] rest, int p) {
        return Math.min(cap[p], growth[p] * rest[p]);
    }

    private static int[] step(int[] full, int[] rest, int grazed) {
        int[] next = new int[rest.length];
        for (int p = 0; p < rest.length; p++) {
            next[p] = p == grazed ? 0 : Math.min(full[p], rest[p] + 1);
        }
        return next;
    }

    private static int[] check(int[] cap, int[] growth, int days) {
        if (cap.length == 0 || cap.length != growth.length || cap.length > 6 || days < 0) {
            throw new IllegalArgumentException("bad pasture");
        }
        int[] full = new int[cap.length];
        for (int p = 0; p < cap.length; p++) {
            if (growth[p] <= 0 || cap[p] < 0 || cap[p] > 1000) {
                throw new IllegalArgumentException("bad paddock " + p);
            }
            full[p] = (cap[p] + growth[p] - 1) / growth[p];
        }
        return full;
    }
}
