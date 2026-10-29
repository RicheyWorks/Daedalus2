// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.Arrays;
import java.util.SplittableRandom;

/**
 * Ore Barter (contest gap G247): barter routes between island stalls each cost or earn ore. Find the cheapest ore cost
 * from the forge to every stall, and spot an endless-profit barter loop if one can be reached.
 *
 * <p>The tool is plain: {@link #costs} is Bellman-Ford over {@code n} nodes and an {@code int[][]} edge list of
 * {from, to, weight} rows (signed weights), and {@link #profitLoop} extracts a reachable negative cycle. Any project
 * can use it for shortest paths with negative edges or arbitrage detection.
 */
public final class OreBarter {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_ore_barter";

    /** Cost reported for a stall the forge cannot reach. */
    public static final long UNREACHABLE = Long.MAX_VALUE;

    /** How an answer went. */
    public enum Grade { SHREWD, FLEECED }

    private OreBarter() {
    }

    /** {@code m} seeded routes among {@code n} stalls with weights in low..high. Same seed, same market. */
    public static int[][] routes(long seed, int n, int m, int low, int high) {
        if (n < 1 || m < 0 || low > high) {
            throw new IllegalArgumentException("need n >= 1, m >= 0, low <= high");
        }
        SplittableRandom r = new SplittableRandom(seed);
        int[][] e = new int[m][];
        for (int i = 0; i < m; i++) {
            e[i] = new int[] {r.nextInt(n), r.nextInt(n), low + r.nextInt(high - low + 1)};
        }
        return e;
    }

    private static void validate(int n, int[][] edges, int src) {
        if (src < 0 || src >= n) {
            throw new IllegalArgumentException("no stall " + src);
        }
        for (int[] e : edges) {
            if (e.length != 3 || e[0] < 0 || e[0] >= n || e[1] < 0 || e[1] >= n) {
                throw new IllegalArgumentException("bad route " + Arrays.toString(e));
            }
        }
    }

    /** Runs n-1 rounds; returns {dist, pred} with pred[v] = index of the last relaxing edge or -1. */
    private static long[][] relax(int n, int[][] edges, int src) {
        long[] dist = new long[n];
        long[] pred = new long[n];
        Arrays.fill(dist, UNREACHABLE);
        Arrays.fill(pred, -1);
        dist[src] = 0;
        for (int round = 1; round < n; round++) {
            boolean changed = false;
            for (int i = 0; i < edges.length; i++) {
                int[] e = edges[i];
                if (dist[e[0]] != UNREACHABLE && dist[e[0]] + e[2] < dist[e[1]]) {
                    dist[e[1]] = dist[e[0]] + e[2];
                    pred[e[1]] = i;
                    changed = true;
                }
            }
            if (!changed) {
                break;
            }
        }
        return new long[][] {dist, pred};
    }

    /** A reachable profit loop as stall ids in route order (empty if none). */
    public static int[] profitLoop(int n, int[][] edges, int src) {
        validate(n, edges, src);
        long[][] dp = relax(n, edges, src);
        long[] dist = dp[0];
        long[] pred = dp[1];
        int hit = -1;
        for (int i = 0; i < edges.length && hit < 0; i++) {
            int[] e = edges[i];
            if (dist[e[0]] != UNREACHABLE && dist[e[0]] + e[2] < dist[e[1]]) {
                pred[e[1]] = i;
                hit = e[1];
            }
        }
        if (hit < 0) {
            return new int[0];
        }
        int x = hit;
        for (int i = 0; i < n; i++) {
            x = edges[(int) pred[x]][0];
        }
        int[] loop = new int[n];
        int len = 0;
        int y = x;
        do {
            loop[len++] = y;
            y = edges[(int) pred[y]][0];
        } while (y != x);
        int[] out = new int[len];
        for (int i = 0; i < len; i++) {
            out[i] = loop[len - 1 - i];
        }
        return out;
    }

    /** Cheapest cost from {@code src} to every stall ({@link #UNREACHABLE} if none); throws if a loop is reachable. */
    public static long[] costs(int n, int[][] edges, int src) {
        if (profitLoop(n, edges, src).length > 0) {
            throw new IllegalStateException("a profit loop is reachable; costs are unbounded");
        }
        return relax(n, edges, src)[0];
    }

    /** SHREWD only if the loop call (true = a loop exists) and, when no loop, the cost to {@code target} are right. */
    public static Grade grade(int n, int[][] edges, int src, boolean saysLoop, int target, long cost) {
        boolean loop = profitLoop(n, edges, src).length > 0;
        if (loop != saysLoop) {
            return Grade.FLEECED;
        }
        return loop || costs(n, edges, src)[target] == cost ? Grade.SHREWD : Grade.FLEECED;
    }

    /** The Forgemaster's line for an answer. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case SHREWD -> "Forgemaster: you priced every stall and smelled the swindle loop. No trader fools you.";
            case FLEECED -> "Forgemaster: the traders saw you coming. Count the ore on every route again.";
        };
    }
}
