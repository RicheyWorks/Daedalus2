// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.SplittableRandom;

/**
 * Anvil Rota (contest gap G195): {@code n} smiths, {@code n} forge jobs and a table of the hours each smith needs for
 * each job. Give every smith exactly one job so the forge finishes in the fewest total hours.
 *
 * <p>The solver is plain: {@code cost[smith][job]} hours, an assignment is {@code job[smith]}. {@link #assign} is the
 * exact Hungarian method (O(n^3)); {@link #greedy} takes the cheapest free smith-job pair first and can lose. Any
 * project can use it for crews to stations or units to targets.
 */
public final class AnvilRota {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_anvil_rota";

    /** How a rota compares with the best. */
    public enum Grade { TIGHT, LOOSE, SLACK }

    /** An assignment: {@code jobs.get(s)} is smith s's job, and the total hours. */
    public record Rota(List<Integer> jobs, long hours) {

        public Rota {
            jobs = List.copyOf(jobs);
        }
    }

    private AnvilRota() {
    }

    /** A seeded n x n table of 1..maxHours hours. Same seed, same table. */
    public static int[][] table(long seed, int n, int maxHours) {
        if (n < 0 || maxHours < 1) {
            throw new IllegalArgumentException("need n >= 0 and maxHours >= 1");
        }
        SplittableRandom r = new SplittableRandom(seed);
        int[][] c = new int[n][n];
        for (int i = 0; i < n; i++) {
            for (int j = 0; j < n; j++) {
                c[i][j] = 1 + r.nextInt(maxHours);
            }
        }
        return c;
    }

    /** Total hours of an assignment. */
    public static long hours(int[][] cost, List<Integer> jobs) {
        check(cost);
        if (jobs.size() != cost.length) {
            throw new IllegalArgumentException("one job per smith");
        }
        boolean[] taken = new boolean[cost.length];
        long h = 0;
        for (int s = 0; s < jobs.size(); s++) {
            int j = jobs.get(s);
            if (j < 0 || j >= cost.length || taken[j]) {
                throw new IllegalArgumentException("not a one-to-one rota");
            }
            taken[j] = true;
            h += cost[s][j];
        }
        return h;
    }

    /** The exact fewest-hours rota (Hungarian method with potentials). */
    public static Rota assign(int[][] cost) {
        check(cost);
        int n = cost.length;
        long inf = Long.MAX_VALUE / 4;
        long[] u = new long[n + 1];
        long[] v = new long[n + 1];
        int[] p = new int[n + 1];
        int[] way = new int[n + 1];
        for (int i = 1; i <= n; i++) {
            p[0] = i;
            int j0 = 0;
            long[] minv = new long[n + 1];
            Arrays.fill(minv, inf);
            boolean[] used = new boolean[n + 1];
            do {
                used[j0] = true;
                int i0 = p[j0];
                long delta = inf;
                int j1 = 0;
                for (int j = 1; j <= n; j++) {
                    if (!used[j]) {
                        long cur = cost[i0 - 1][j - 1] - u[i0] - v[j];
                        if (cur < minv[j]) {
                            minv[j] = cur;
                            way[j] = j0;
                        }
                        if (minv[j] < delta) {
                            delta = minv[j];
                            j1 = j;
                        }
                    }
                }
                for (int j = 0; j <= n; j++) {
                    if (used[j]) {
                        u[p[j]] += delta;
                        v[j] -= delta;
                    } else {
                        minv[j] -= delta;
                    }
                }
                j0 = j1;
            } while (p[j0] != 0);
            do {
                int j1 = way[j0];
                p[j0] = p[j1];
                j0 = j1;
            } while (j0 != 0);
        }
        Integer[] job = new Integer[n];
        for (int j = 1; j <= n; j++) {
            job[p[j] - 1] = j - 1;
        }
        List<Integer> jobs = Arrays.asList(job);
        return new Rota(jobs, hours(cost, jobs));
    }

    /** Greedy foreman: repeatedly the cheapest free smith-job pair (lowest smith, then job, on ties). */
    public static Rota greedy(int[][] cost) {
        check(cost);
        int n = cost.length;
        boolean[] sDone = new boolean[n];
        boolean[] jDone = new boolean[n];
        Integer[] job = new Integer[n];
        for (int k = 0; k < n; k++) {
            int bs = -1;
            int bj = -1;
            for (int s = 0; s < n; s++) {
                for (int j = 0; j < n; j++) {
                    if (!sDone[s] && !jDone[j] && (bs < 0 || cost[s][j] < cost[bs][bj])) {
                        bs = s;
                        bj = j;
                    }
                }
            }
            sDone[bs] = true;
            jDone[bj] = true;
            job[bs] = bj;
        }
        List<Integer> jobs = new ArrayList<>(Arrays.asList(job));
        return new Rota(jobs, hours(cost, jobs));
    }

    /** TIGHT at the best, LOOSE within 10% over, SLACK beyond. */
    public static Grade grade(long hours, long best) {
        if (hours < best) {
            throw new IllegalArgumentException("hours below the best");
        }
        if (hours == best) {
            return Grade.TIGHT;
        }
        return 10L * hours <= 11L * best ? Grade.LOOSE : Grade.SLACK;
    }

    /** The Forgemaster's line for a rota. */
    public static String forgemasterLine(Rota r, long best) {
        return switch (grade(r.hours(), best)) {
            case TIGHT -> "Forgemaster: " + r.hours() + " hours. Every anvil rings on the beat.";
            case LOOSE -> "Forgemaster: " + r.hours() + " of " + best + " hours. Near enough. Swap two and see.";
            case SLACK -> "Forgemaster: " + r.hours() + " hours for a " + best + "-hour forge. Half of them are idle.";
        };
    }

    private static void check(int[][] cost) {
        for (int[] row : cost) {
            if (row.length != cost.length) {
                throw new IllegalArgumentException("cost table must be square");
            }
        }
    }
}
