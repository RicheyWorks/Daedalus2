// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.Arrays;
import java.util.SplittableRandom;

/**
 * Courier Charts (contest gap G250): the forge courier keeps one chart of the cheapest trip between every pair of
 * island workshops over one-way paths, and must read off the cost and the stop-by-stop route for any pair.
 *
 * <p>The tool is plain: Floyd-Warshall all-pairs shortest paths over a {@code long[][]} weight matrix
 * ({@link #NO_PATH} for no direct path, non-negative weights) with next-hop route reconstruction. Any project can use
 * it for small dense distance tables.
 */
public final class CourierCharts {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_courier_charts";

    /** Marks no path in input and output. */
    public static final long NO_PATH = Long.MAX_VALUE;

    /** How a delivery went. */
    public enum Grade { SWIFT, LOST }

    private final long[][] dist;
    private final int[][] next;

    /** Builds the chart from a square matrix of direct path costs. */
    public CourierCharts(long[][] direct) {
        int n = direct.length;
        dist = new long[n][n];
        next = new int[n][n];
        for (int i = 0; i < n; i++) {
            if (direct[i].length != n) {
                throw new IllegalArgumentException("matrix must be square");
            }
            Arrays.fill(next[i], -1);
            for (int j = 0; j < n; j++) {
                long w = direct[i][j];
                if (w < 0) {
                    throw new IllegalArgumentException("negative path " + i + "->" + j);
                }
                dist[i][j] = i == j ? 0 : w;
                if (i == j || w != NO_PATH) {
                    next[i][j] = j;
                }
            }
        }
        for (int k = 0; k < n; k++) {
            for (int i = 0; i < n; i++) {
                if (dist[i][k] == NO_PATH) {
                    continue;
                }
                for (int j = 0; j < n; j++) {
                    if (dist[k][j] != NO_PATH && dist[i][k] + dist[k][j] < dist[i][j]) {
                        dist[i][j] = dist[i][k] + dist[k][j];
                        next[i][j] = next[i][k];
                    }
                }
            }
        }
    }

    /** A seeded n x n matrix: each direct path exists with chance pct/100 at cost 1..maxCost. Same seed, same map. */
    public static long[][] paths(long seed, int n, int pct, int maxCost) {
        if (n < 0 || pct < 0 || pct > 100 || maxCost < 1) {
            throw new IllegalArgumentException("need n >= 0, 0 <= pct <= 100, maxCost >= 1");
        }
        SplittableRandom r = new SplittableRandom(seed);
        long[][] m = new long[n][n];
        for (int i = 0; i < n; i++) {
            for (int j = 0; j < n; j++) {
                m[i][j] = i != j && r.nextInt(100) < pct ? 1 + r.nextInt(maxCost) : NO_PATH;
            }
        }
        return m;
    }

    private void check(int v) {
        if (v < 0 || v >= dist.length) {
            throw new IllegalArgumentException("no workshop " + v);
        }
    }

    /** Cheapest cost from a to b, or {@link #NO_PATH}. */
    public long cost(int a, int b) {
        check(a);
        check(b);
        return dist[a][b];
    }

    /** Stops from a to b inclusive along a cheapest trip; empty if unreachable. */
    public int[] route(int a, int b) {
        check(a);
        check(b);
        if (next[a][b] < 0) {
            return new int[0];
        }
        int[] out = new int[dist.length];
        int len = 0;
        int x = a;
        out[len++] = x;
        while (x != b) {
            x = next[x][b];
            out[len++] = x;
        }
        return Arrays.copyOf(out, len);
    }

    /** SWIFT only if the route runs a to b over existing paths and costs exactly the cheapest trip. */
    public Grade grade(long[][] direct, int a, int b, int[] stops) {
        if (stops.length == 0 || stops[0] != a || stops[stops.length - 1] != b || cost(a, b) == NO_PATH) {
            return Grade.LOST;
        }
        long total = 0;
        for (int i = 0; i + 1 < stops.length; i++) {
            check(stops[i + 1]);
            long w = direct[stops[i]][stops[i + 1]];
            if (w == NO_PATH) {
                return Grade.LOST;
            }
            total += w;
        }
        return total == cost(a, b) ? Grade.SWIFT : Grade.LOST;
    }

    /** The Forgemaster's line for a delivery. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case SWIFT -> "Forgemaster: there and back before the iron cooled. Not one step wasted.";
            case LOST -> "Forgemaster: the parcel wandered. Check your chart before you run.";
        };
    }
}
