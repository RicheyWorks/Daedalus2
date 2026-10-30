// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.Arrays;
import java.util.SplittableRandom;

/**
 * G444 The Beacon Ring: the harbour master wants the smallest ring of beacons that covers every
 * moored ship (integer points), the minimum enclosing circle. Uses Welzl's randomized incremental
 * method (expected linear time) after a seeded shuffle. A circle is {cx, cy, r}; points within a
 * relative tolerance of 1e-9 count as inside.
 */
public final class BeaconRing {

    public static final String QUEST_ID = "q_beacon_ring";
    public static final int MAX_POINTS = 100_000;
    public static final long MAX_COORD = 1_000_000;
    private static final double EPS = 1e-9;

    private BeaconRing() { }

    private static void check(long[][] pts) {
        if (pts == null || pts.length < 1 || pts.length > MAX_POINTS) {
            throw new IllegalArgumentException("need 1 to " + MAX_POINTS + " points");
        }
        for (long[] p : pts) {
            if (p == null || p.length != 2 || Math.abs(p[0]) > MAX_COORD || Math.abs(p[1]) > MAX_COORD) {
                throw new IllegalArgumentException("points are {x, y} within 10^6");
            }
        }
    }

    /** True when (x, y) lies in the circle, allowing the tolerance. */
    public static boolean contains(double[] c, long[] p) {
        double dx = p[0] - c[0];
        double dy = p[1] - c[1];
        return Math.sqrt(dx * dx + dy * dy) <= c[2] * (1 + EPS) + EPS;
    }

    private static double[] two(long[] a, long[] b) {
        double cx = (a[0] + b[0]) / 2.0;
        double cy = (a[1] + b[1]) / 2.0;
        return new double[] {cx, cy, Math.hypot(a[0] - cx, a[1] - cy)};
    }

    /** Circumcircle of three points, or the widest two-point circle when they are collinear. */
    public static double[] three(long[] a, long[] b, long[] c) {
        double bx = b[0] - a[0];
        double by = b[1] - a[1];
        double cx = c[0] - a[0];
        double cy = c[1] - a[1];
        double d = 2 * (bx * cy - by * cx);
        if (d == 0) {
            double[] best = two(a, b);
            for (double[] k : new double[][] {two(a, c), two(b, c)}) {
                if (k[2] > best[2]) {
                    best = k;
                }
            }
            return best;
        }
        double b2 = bx * bx + by * by;
        double c2 = cx * cx + cy * cy;
        double ux = (cy * b2 - by * c2) / d;
        double uy = (bx * c2 - cx * b2) / d;
        return new double[] {ux + a[0], uy + a[1], Math.hypot(ux, uy)};
    }

    /** Minimum enclosing circle {cx, cy, r}; the seed fixes the shuffle. */
    public static double[] circle(long[][] pts, long seed) {
        check(pts);
        long[][] p = pts.clone();
        SplittableRandom rnd = new SplittableRandom(seed);
        for (int i = p.length - 1; i > 0; i--) {
            int j = rnd.nextInt(i + 1);
            long[] t = p[i];
            p[i] = p[j];
            p[j] = t;
        }
        double[] c = {p[0][0], p[0][1], 0};
        for (int i = 1; i < p.length; i++) {
            if (contains(c, p[i])) {
                continue;
            }
            c = new double[] {p[i][0], p[i][1], 0};
            for (int j = 0; j < i; j++) {
                if (contains(c, p[j])) {
                    continue;
                }
                c = two(p[i], p[j]);
                for (int k = 0; k < j; k++) {
                    if (!contains(c, p[k])) {
                        c = three(p[i], p[j], p[k]);
                    }
                }
            }
        }
        return c;
    }

    /** Indices of input points lying on the circle's edge (within tolerance). */
    public static int[] boundary(long[][] pts, double[] c) {
        int n = 0;
        int[] tmp = new int[pts.length];
        for (int i = 0; i < pts.length; i++) {
            double dist = Math.hypot(pts[i][0] - c[0], pts[i][1] - c[1]);
            if (Math.abs(dist - c[2]) <= 1e-7 * Math.max(1, c[2])) {
                tmp[n++] = i;
            }
        }
        return Arrays.copyOf(tmp, n);
    }

    /** Quest q_beacon_ring: the harbour master names the ring radius, rounded down. */
    public static boolean quest(long[][] pts, long answer) {
        return (long) Math.floor(circle(pts, 444)[2] + 1e-9) == answer;
    }
}