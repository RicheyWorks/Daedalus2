// SPDX-License-Identifier: MIT

package com.daedalus.world.stable;

import java.util.Arrays;
import java.util.SplittableRandom;

/**
 * G532 Hay Wagon Round (Studio horse lane): the hay wagon leaves the barn (stop 0) at time 0, must
 * reach every stall inside its feeding window [open, close] (arriving early means waiting for the
 * window to open), and then rolls back to the barn. {@link #best} finds the earliest return, exactly,
 * with Held-Karp over (stalls fed, last stall), keeping the earliest feeding time for each state
 * (waiting is allowed, so earlier is never worse). {@link #nearest} (always drive to the closest
 * stall still open in time) is the habit that comes home late or strands a stall. Manhattan
 * distances on a yard grid, at most 12 stalls.
 */
public final class HayWagonRound {

    public static final String QUEST_ID = "q_hay_on_time";
    public static final int MAX_STALLS = 12;
    public static final int INFEASIBLE = -1;

    /** A yard: barn plus stalls at grid points, with a feeding window per stall (index 0 is the barn). */
    public record Yard(int[] x, int[] y, int[] open, int[] close) {
        public Yard {
            x = x.clone();
            y = y.clone();
            open = open.clone();
            close = close.clone();
            int n = x.length;
            if (n < 1 || n - 1 > MAX_STALLS || y.length != n || open.length != n || close.length != n) {
                throw new IllegalArgumentException("bad yard");
            }
            for (int i = 0; i < n; i++) {
                if (open[i] < 0 || close[i] < open[i]) {
                    throw new IllegalArgumentException("bad window " + i);
                }
            }
        }

        @Override
        public int[] x() {
            return x.clone();
        }

        @Override
        public int[] y() {
            return y.clone();
        }

        @Override
        public int[] open() {
            return open.clone();
        }

        @Override
        public int[] close() {
            return close.clone();
        }

        /** Number of stalls (not counting the barn). */
        public int stalls() {
            return x.length - 1;
        }

        /** Manhattan driving time between two stops. */
        public int dist(int a, int b) {
            return Math.abs(x[a] - x[b]) + Math.abs(y[a] - y[b]);
        }

        @Override
        public boolean equals(Object o) {
            return o instanceof Yard v && Arrays.equals(v.x, x) && Arrays.equals(v.y, y)
                    && Arrays.equals(v.open, open) && Arrays.equals(v.close, close);
        }

        @Override
        public int hashCode() {
            return Arrays.hashCode(new int[] {Arrays.hashCode(x), Arrays.hashCode(y),
                Arrays.hashCode(open), Arrays.hashCode(close)});
        }

        @Override
        public String toString() {
            return "Yard[x=" + Arrays.toString(x) + ", y=" + Arrays.toString(y) + ", open="
                    + Arrays.toString(open) + ", close=" + Arrays.toString(close) + "]";
        }
    }

    /** A round: the stall order (1-based stall ids) and the return time, or INFEASIBLE with an empty order. */
    public record Round(int finish, int[] order) {
        public Round {
            order = order.clone();
        }

        @Override
        public int[] order() {
            return order.clone();
        }

        @Override
        public boolean equals(Object o) {
            return o instanceof Round r && r.finish == finish && Arrays.equals(r.order, order);
        }

        @Override
        public int hashCode() {
            return 31 * finish + Arrays.hashCode(order);
        }

        @Override
        public String toString() {
            return "Round[" + finish + ", " + Arrays.toString(order) + "]";
        }
    }

    private HayWagonRound() { }

    /**
     * Seeded yard of {@code stalls} stalls on a {@code size} grid. Windows are cut around a random
     * visiting order so at least one round always feeds every stall in time.
     */
    public static Yard yard(long seed, int stalls, int size, int slack) {
        if (stalls < 0 || stalls > MAX_STALLS || size <= 0 || slack < 0) {
            throw new IllegalArgumentException("bad yard request");
        }
        SplittableRandom rnd = new SplittableRandom(seed);
        int n = stalls + 1;
        int[] x = new int[n];
        int[] y = new int[n];
        for (int i = 1; i < n; i++) {
            x[i] = rnd.nextInt(size);
            y[i] = rnd.nextInt(size);
        }
        x[0] = size / 2;
        y[0] = size / 2;
        int[] perm = new int[stalls];
        for (int i = 0; i < stalls; i++) {
            perm[i] = i + 1;
        }
        for (int i = stalls - 1; i > 0; i--) {
            int j = rnd.nextInt(i + 1);
            int t = perm[i];
            perm[i] = perm[j];
            perm[j] = t;
        }
        int[] open = new int[n];
        int[] close = new int[n];
        close[0] = Integer.MAX_VALUE / 4;
        int t = 0;
        int at = 0;
        for (int s : perm) {
            t += Math.abs(x[at] - x[s]) + Math.abs(y[at] - y[s]);
            int lo = rnd.nextInt(slack + 1);
            int hi = rnd.nextInt(slack + 1);
            open[s] = Math.max(0, t - lo);
            close[s] = t + hi;
            at = s;
        }
        return new Yard(x, y, open, close);
    }

    /** Earliest return to the barn feeding every stall inside its window (Held-Karp). */
    public static Round best(Yard yard) {
        int m = yard.stalls();
        if (m == 0) {
            return new Round(0, new int[0]);
        }
        int[] open = yard.open;
        int[] close = yard.close;
        int states = 1 << m;
        int[][] fed = new int[states][m];
        int[][] prev = new int[states][m];
        for (int[] row : fed) {
            Arrays.fill(row, Integer.MAX_VALUE);
        }
        for (int j = 0; j < m; j++) {
            int arrive = Math.max(open[j + 1], yard.dist(0, j + 1));
            if (arrive <= close[j + 1]) {
                fed[1 << j][j] = arrive;
                prev[1 << j][j] = -1;
            }
        }
        for (int s = 1; s < states; s++) {
            for (int j = 0; j < m; j++) {
                int t = fed[s][j];
                if (t == Integer.MAX_VALUE) {
                    continue;
                }
                for (int k = 0; k < m; k++) {
                    if ((s & (1 << k)) != 0) {
                        continue;
                    }
                    int arrive = Math.max(open[k + 1], t + yard.dist(j + 1, k + 1));
                    int ns = s | (1 << k);
                    if (arrive <= close[k + 1] && arrive < fed[ns][k]) {
                        fed[ns][k] = arrive;
                        prev[ns][k] = j;
                    }
                }
            }
        }
        int full = states - 1;
        int bestFinish = Integer.MAX_VALUE;
        int last = -1;
        for (int j = 0; j < m; j++) {
            if (fed[full][j] != Integer.MAX_VALUE) {
                int f = fed[full][j] + yard.dist(j + 1, 0);
                if (f < bestFinish) {
                    bestFinish = f;
                    last = j;
                }
            }
        }
        if (last < 0) {
            return new Round(INFEASIBLE, new int[0]);
        }
        int[] order = new int[m];
        int s = full;
        for (int pos = m - 1; pos >= 0; pos--) {
            order[pos] = last + 1;
            int p = prev[s][last];
            s ^= 1 << last;
            last = p;
        }
        return new Round(bestFinish, order);
    }

    /** Naive habit: drive to the nearest unfed stall still reachable before it closes; ties to the lower id. */
    public static Round nearest(Yard yard) {
        int m = yard.stalls();
        boolean[] done = new boolean[m + 1];
        int[] order = new int[m];
        int at = 0;
        int t = 0;
        for (int step = 0; step < m; step++) {
            int pick = -1;
            for (int k = 1; k <= m; k++) {
                if (!done[k] && t + yard.dist(at, k) <= yard.close[k]
                        && (pick < 0 || yard.dist(at, k) < yard.dist(at, pick))) {
                    pick = k;
                }
            }
            if (pick < 0) {
                return new Round(INFEASIBLE, new int[0]);
            }
            t = Math.max(yard.open[pick], t + yard.dist(at, pick));
            done[pick] = true;
            order[step] = pick;
            at = pick;
        }
        return new Round(t + yard.dist(at, 0), order);
    }

    /** Return time of a stall order, or INFEASIBLE when it misses a window, repeats or skips a stall. */
    public static int drive(Yard yard, int[] order) {
        int m = yard.stalls();
        if (order.length != m) {
            return INFEASIBLE;
        }
        boolean[] seen = new boolean[m + 1];
        int at = 0;
        int t = 0;
        for (int s : order) {
            if (s < 1 || s > m || seen[s]) {
                return INFEASIBLE;
            }
            seen[s] = true;
            t = Math.max(yard.open[s], t + yard.dist(at, s));
            if (t > yard.close[s]) {
                return INFEASIBLE;
            }
            at = s;
        }
        return t + yard.dist(at, 0);
    }

    /** Quest q_hay_on_time: the stable hand's round feeds every stall in time and is home earliest. */
    public static boolean quest(Yard yard, int[] order) {
        int got = drive(yard, order);
        return got != INFEASIBLE && got == best(yard).finish();
    }
}
