// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.Arrays;

/**
 * G446 The Sail Cuts: the sailmaker cuts a flat sail (a simple polygon with integer corners) into
 * triangles along straight seams between corners. Uses ear clipping: repeatedly cut off a convex
 * corner whose triangle holds no other corner. Takes 3 to 500 corners within 10^6, in either
 * orientation, with no repeated corner, no self-crossing and no zero area; returns n - 2
 * triangles as corner indices, each listed counter-clockwise. O(n^3) worst case.
 */
public final class SailCuts {

    public static final String QUEST_ID = "q_sail_cuts";
    public static final int MAX_CORNERS = 500;
    public static final long MAX_COORD = 1_000_000;

    private SailCuts() { }

    static long cross(long[] o, long[] a, long[] b) {
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
    }

    /** Twice the signed area (positive when counter-clockwise). */
    public static long doubledArea(long[][] p) {
        long s = 0;
        for (int i = 0; i < p.length; i++) {
            long[] a = p[i];
            long[] b = p[(i + 1) % p.length];
            s += a[0] * b[1] - a[1] * b[0];
        }
        return s;
    }

    private static boolean onSeg(long[] a, long[] b, long[] q) {
        return Math.min(a[0], b[0]) <= q[0] && q[0] <= Math.max(a[0], b[0])
            && Math.min(a[1], b[1]) <= q[1] && q[1] <= Math.max(a[1], b[1]);
    }

    /** True when closed segments ab and cd share any point. */
    static boolean meet(long[] a, long[] b, long[] c, long[] d) {
        long d1 = Long.signum(cross(a, b, c));
        long d2 = Long.signum(cross(a, b, d));
        long d3 = Long.signum(cross(c, d, a));
        long d4 = Long.signum(cross(c, d, b));
        if (d1 * d2 < 0 && d3 * d4 < 0) {
            return true;
        }
        return d1 == 0 && onSeg(a, b, c) || d2 == 0 && onSeg(a, b, d)
            || d3 == 0 && onSeg(c, d, a) || d4 == 0 && onSeg(c, d, b);
    }

    private static void check(long[][] p) {
        if (p == null || p.length < 3 || p.length > MAX_CORNERS) {
            throw new IllegalArgumentException("need 3 to " + MAX_CORNERS + " corners");
        }
        for (long[] q : p) {
            if (q == null || q.length != 2 || Math.abs(q[0]) > MAX_COORD || Math.abs(q[1]) > MAX_COORD) {
                throw new IllegalArgumentException("corners are {x, y} within 10^6");
            }
        }
        int n = p.length;
        for (int i = 0; i < n; i++) {
            for (int j = i + 1; j < n; j++) {
                if (p[i][0] == p[j][0] && p[i][1] == p[j][1]) {
                    throw new IllegalArgumentException("repeated corner");
                }
            }
        }
        if (doubledArea(p) == 0) {
            throw new IllegalArgumentException("zero area");
        }
        for (int i = 0; i < n; i++) {
            for (int j = i + 1; j < n; j++) {
                boolean adjacent = j == i + 1 || i == 0 && j == n - 1;
                if (adjacent) {
                    continue;
                }
                if (meet(p[i], p[(i + 1) % n], p[j], p[(j + 1) % n])) {
                    throw new IllegalArgumentException("sail edges cross");
                }
            }
        }
        for (int i = 0; i < n; i++) {
            long[] a = p[(i + n - 1) % n];
            long[] b = p[i];
            long[] c = p[(i + 1) % n];
            if (cross(a, b, c) == 0 && (c[0] - b[0]) * (a[0] - b[0]) + (c[1] - b[1]) * (a[1] - b[1]) > 0) {
                throw new IllegalArgumentException("sail edges fold back");
            }
        }
    }

    private static boolean inTri(long[] a, long[] b, long[] c, long[] q) {
        return cross(a, b, q) >= 0 && cross(b, c, q) >= 0 && cross(c, a, q) >= 0;
    }

    /** Triangles {i, j, k} of corner indices, counter-clockwise, n - 2 of them. */
    public static int[][] cut(long[][] pts) {
        check(pts);
        int n = pts.length;
        boolean ccw = doubledArea(pts) > 0;
        int[] idx = new int[n];
        for (int i = 0; i < n; i++) {
            idx[i] = ccw ? i : n - 1 - i;
        }
        int m = n;
        int[][] out = new int[n - 2][];
        int t = 0;
        while (m > 3) {
            int ear = -1;
            for (int i = 0; i < m && ear < 0; i++) {
                long[] a = pts[idx[(i + m - 1) % m]];
                long[] b = pts[idx[i]];
                long[] c = pts[idx[(i + 1) % m]];
                if (cross(a, b, c) <= 0) {
                    continue;
                }
                boolean empty = true;
                for (int k = 0; k < m && empty; k++) {
                    int v = idx[k];
                    if (k != i && k != (i + 1) % m && k != (i + m - 1) % m && inTri(a, b, c, pts[v])) {
                        empty = false;
                    }
                }
                if (empty) {
                    ear = i;
                }
            }
            if (ear < 0) {
                throw new IllegalArgumentException("no ear found; sail is not simple");
            }
            out[t++] = new int[] {idx[(ear + m - 1) % m], idx[ear], idx[(ear + 1) % m]};
            System.arraycopy(idx, ear + 1, idx, ear, m - ear - 1);
            m--;
        }
        out[t] = new int[] {idx[0], idx[1], idx[2]};
        return out;
    }

    /** Sum of the triangles' doubled areas; equals |doubledArea| of the sail. */
    public static long totalDoubledArea(long[][] pts, int[][] tris) {
        long s = 0;
        for (int[] tr : tris) {
            s += cross(pts[tr[0]], pts[tr[1]], pts[tr[2]]);
        }
        return s;
    }

    /** Quest q_sail_cuts: the sailmaker names how many triangles and the sail's doubled area. */
    public static boolean quest(long[][] pts, int triangles, long doubled) {
        int[][] tr = cut(pts);
        return tr.length == triangles && totalDoubledArea(pts, tr) == doubled
            && Arrays.stream(tr).allMatch(x -> cross(pts[x[0]], pts[x[1]], pts[x[2]]) > 0);
    }
}