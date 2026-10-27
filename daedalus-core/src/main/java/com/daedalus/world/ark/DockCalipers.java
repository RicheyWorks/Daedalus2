// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.Arrays;

/**
 * G461 The Dock Calipers: the harbour master measures a field of buoys (integer points): the
 * widest span between two buoys (diameter, as an exact squared distance) and the narrowest dock
 * that holds them all (minimum width between two parallel lines). Builds the convex hull by
 * Andrew's monotone chain, then walks it with rotating calipers, O(n log n). Takes 1 to 100000
 * buoys within 10^6; repeats are allowed. Width is 0 when the buoys are collinear.
 */
public final class DockCalipers {

    public static final String QUEST_ID = "q_dock_calipers";
    public static final int MAX_BUOYS = 100_000;
    public static final long MAX_COORD = 1_000_000;

    private DockCalipers() { }

    static long cross(long[] o, long[] a, long[] b) {
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
    }

    static long dist2(long[] a, long[] b) {
        long dx = a[0] - b[0];
        long dy = a[1] - b[1];
        return dx * dx + dy * dy;
    }

    private static void check(long[][] pts) {
        if (pts == null || pts.length < 1 || pts.length > MAX_BUOYS) {
            throw new IllegalArgumentException("need 1 to " + MAX_BUOYS + " buoys");
        }
        for (long[] p : pts) {
            if (p == null || p.length != 2 || Math.abs(p[0]) > MAX_COORD || Math.abs(p[1]) > MAX_COORD) {
                throw new IllegalArgumentException("buoys are {x, y} within 10^6");
            }
        }
    }

    /** Convex hull corners, counter-clockwise, no collinear corners. */
    public static long[][] hull(long[][] pts) {
        check(pts);
        long[][] p = pts.clone();
        Arrays.sort(p, (a, b) -> a[0] != b[0] ? Long.compare(a[0], b[0]) : Long.compare(a[1], b[1]));
        int n = p.length;
        long[][] h = new long[2 * n][];
        int k = 0;
        for (int i = 0; i < n; i++) {
            while (k >= 2 && cross(h[k - 2], h[k - 1], p[i]) <= 0) {
                k--;
            }
            h[k++] = p[i];
        }
        for (int i = n - 2, lo = k + 1; i >= 0; i--) {
            while (k >= lo && cross(h[k - 2], h[k - 1], p[i]) <= 0) {
                k--;
            }
            h[k++] = p[i];
        }
        int m = Math.max(1, k - 1);
        long[][] out = new long[m][];
        for (int i = 0; i < m; i++) {
            out[i] = h[i].clone();
        }
        if (m == 2 && out[0][0] == out[1][0] && out[0][1] == out[1][1]) {
            return new long[][] {out[0]};
        }
        return out;
    }

    /** Squared diameter: the largest squared distance between two buoys. */
    public static long diameterSquared(long[][] pts) {
        long[][] h = hull(pts);
        int m = h.length;
        if (m == 1) {
            return 0;
        }
        if (m == 2) {
            return dist2(h[0], h[1]);
        }
        long best = 0;
        int j = 1;
        for (int i = 0; i < m; i++) {
            long[] a = h[i];
            long[] b = h[(i + 1) % m];
            while (cross(a, b, h[(j + 1) % m]) > cross(a, b, h[j])) {
                j = (j + 1) % m;
            }
            best = Math.max(best, Math.max(dist2(a, h[j]), dist2(b, h[j])));
        }
        return best;
    }

    /** Minimum width between two parallel lines enclosing every buoy. */
    public static double width(long[][] pts) {
        long[][] h = hull(pts);
        int m = h.length;
        if (m < 3) {
            return 0;
        }
        double best = Double.MAX_VALUE;
        int j = 1;
        for (int i = 0; i < m; i++) {
            long[] a = h[i];
            long[] b = h[(i + 1) % m];
            while (cross(a, b, h[(j + 1) % m]) > cross(a, b, h[j])) {
                j = (j + 1) % m;
            }
            best = Math.min(best, cross(a, b, h[j]) / Math.sqrt(dist2(a, b)));
        }
        return best;
    }

    /** Quest q_dock_calipers: the harbour master names the squared widest span. */
    public static boolean quest(long[][] pts, long answer) {
        return diameterSquared(pts) == answer;
    }
}