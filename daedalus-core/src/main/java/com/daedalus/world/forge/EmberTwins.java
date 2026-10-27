// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.Arrays;
import java.util.SplittableRandom;

/**
 * Ember Twins (contest gap G307): embers float over the forge floor, and two embers too close together will fuse. Find
 * the closest pair and its squared distance.
 *
 * <p>The tool is plain: {@link #closestPair} is the O(n log n) divide-and-conquer closest pair on integer points
 * (x-sorted split, y-merged strip scan) with exact {@code long} squared distances. Coordinates must lie within
 * {@link #MAX_COORD} in absolute value so squared distances never overflow. Any project can use it for proximity
 * checks.
 */
public final class EmberTwins {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_ember_twins";

    /** Largest absolute coordinate accepted. */
    public static final long MAX_COORD = 1_000_000_000L;

    /** How a call went. */
    public enum Grade { FUSED, STRAYED }

    /** The closest pair: point indices {@code a < b} and their squared distance. */
    public record Pair(int a, int b, long dist2) {
    }

    private EmberTwins() {
    }

    /** {@code n} seeded embers with coordinates in [0, range). Same seed, same scatter. */
    public static long[][] embers(long seed, int n, int range) {
        if (n < 2 || range < 1) {
            throw new IllegalArgumentException("need n >= 2 and range >= 1");
        }
        SplittableRandom r = new SplittableRandom(seed);
        long[][] p = new long[n][2];
        for (long[] q : p) {
            q[0] = r.nextInt(range);
            q[1] = r.nextInt(range);
        }
        return p;
    }

    /** Squared distance between two points. */
    public static long dist2(long[] p, long[] q) {
        long dx = p[0] - q[0];
        long dy = p[1] - q[1];
        return dx * dx + dy * dy;
    }

    /** The closest pair of points (at least two, each {x, y}). */
    public static Pair closestPair(long[][] pts) {
        int n = pts.length;
        if (n < 2) {
            throw new IllegalArgumentException("need at least two embers");
        }
        Integer[] boxed = new Integer[n];
        for (int i = 0; i < n; i++) {
            if (Math.abs(pts[i][0]) > MAX_COORD || Math.abs(pts[i][1]) > MAX_COORD) {
                throw new IllegalArgumentException("coordinate out of range at " + i);
            }
            boxed[i] = i;
        }
        Arrays.sort(boxed, (u, v) -> pts[u][0] != pts[v][0] ? Long.compare(pts[u][0], pts[v][0])
                : Long.compare(pts[u][1], pts[v][1]));
        int[] idx = new int[n];
        for (int i = 0; i < n; i++) {
            idx[i] = boxed[i];
        }
        long[] best = {Long.MAX_VALUE, -1, -1};
        solve(pts, idx, new int[n], 0, n, best);
        int a = (int) Math.min(best[1], best[2]);
        int b = (int) Math.max(best[1], best[2]);
        return new Pair(a, b, best[0]);
    }

    private static void consider(long[][] pts, int i, int j, long[] best) {
        long d = dist2(pts[i], pts[j]);
        if (d < best[0]) {
            best[0] = d;
            best[1] = i;
            best[2] = j;
        }
    }

    /** Sorts idx[lo, hi) by y on return. */
    private static void solve(long[][] pts, int[] idx, int[] tmp, int lo, int hi, long[] best) {
        if (hi - lo <= 3) {
            for (int i = lo; i < hi; i++) {
                for (int j = i + 1; j < hi; j++) {
                    consider(pts, idx[i], idx[j], best);
                }
            }
            for (int i = lo + 1; i < hi; i++) {
                int v = idx[i];
                int j = i - 1;
                while (j >= lo && pts[idx[j]][1] > pts[v][1]) {
                    idx[j + 1] = idx[j];
                    j--;
                }
                idx[j + 1] = v;
            }
            return;
        }
        int mid = (lo + hi) >>> 1;
        long midX = pts[idx[mid]][0];
        solve(pts, idx, tmp, lo, mid, best);
        solve(pts, idx, tmp, mid, hi, best);
        int i = lo;
        int j = mid;
        int k = lo;
        while (i < mid || j < hi) {
            if (j >= hi || (i < mid && pts[idx[i]][1] <= pts[idx[j]][1])) {
                tmp[k++] = idx[i++];
            } else {
                tmp[k++] = idx[j++];
            }
        }
        System.arraycopy(tmp, lo, idx, lo, hi - lo);
        int m = 0;
        for (int t = lo; t < hi; t++) {
            long dx = pts[idx[t]][0] - midX;
            if (dx * dx < best[0]) {
                for (int s = m - 1; s >= 0; s--) {
                    long dy = pts[idx[t]][1] - pts[tmp[s]][1];
                    if (dy * dy >= best[0]) {
                        break;
                    }
                    consider(pts, idx[t], tmp[s], best);
                }
                tmp[m++] = idx[t];
            }
        }
    }

    /** FUSED if the named pair is distinct and as close as the closest pair. */
    public static Grade grade(long[][] pts, int a, int b) {
        if (a == b || a < 0 || b < 0 || a >= pts.length || b >= pts.length) {
            return Grade.STRAYED;
        }
        return dist2(pts[a], pts[b]) == closestPair(pts).dist2() ? Grade.FUSED : Grade.STRAYED;
    }

    /** The Forgemaster's line for a call. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case FUSED -> "Forgemaster: those two would have fused. Sharp eyes over a busy floor.";
            case STRAYED -> "Forgemaster: there were closer embers than those. Look again before they catch.";
        };
    }
}
