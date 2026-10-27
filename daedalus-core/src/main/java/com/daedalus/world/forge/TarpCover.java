// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.Arrays;
import java.util.SplittableRandom;

/**
 * Tarp Cover (contest gap G334): rectangular tarps are thrown over the forge yard, overlapping freely. Find the ground
 * actually covered and the ground under two or more tarps.
 *
 * <p>The tool is plain: a sweep line over x with a coordinate-compressed segment tree on y that tracks, per node, the
 * cover count and the length covered at least once and at least twice, in O(n log n). Rectangles are
 * {@code {x1, y1, x2, y2}} with {@code x1 <= x2} and {@code y1 <= y2}; flat ones add nothing. Coordinates must stay
 * within {@link #MAX_COORD} so areas fit in a {@code long}.
 */
public final class TarpCover {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_tarp_cover";

    /** Largest absolute coordinate accepted. */
    public static final long MAX_COORD = 1_000_000_000L;

    /** How a survey went. */
    public enum Grade { COVERED, EXPOSED }

    private TarpCover() {
    }

    /** {@code n} seeded tarps inside [0, range]^2. Same seed, same yard. */
    public static long[][] tarps(long seed, int n, int range) {
        if (n < 0 || range < 1) {
            throw new IllegalArgumentException("need n >= 0 and range >= 1");
        }
        SplittableRandom r = new SplittableRandom(seed);
        long[][] t = new long[n][4];
        for (long[] x : t) {
            long a = r.nextInt(range + 1);
            long b = r.nextInt(range + 1);
            long c = r.nextInt(range + 1);
            long d = r.nextInt(range + 1);
            x[0] = Math.min(a, b);
            x[2] = Math.max(a, b);
            x[1] = Math.min(c, d);
            x[3] = Math.max(c, d);
        }
        return t;
    }

    /** Total area covered by at least one tarp. */
    public static long unionArea(long[][] rects) {
        return sweep(rects)[0];
    }

    /** Total area covered by at least two tarps. */
    public static long overlapArea(long[][] rects) {
        return sweep(rects)[1];
    }

    private static long[] sweep(long[][] rects) {
        int n = rects.length;
        long[] ys = new long[2 * n];
        long[][] ev = new long[2 * n][];
        for (int i = 0; i < n; i++) {
            long[] r = rects[i];
            for (long v : r) {
                if (Math.abs(v) > MAX_COORD) {
                    throw new IllegalArgumentException("coordinate out of range in tarp " + i);
                }
            }
            if (r[0] > r[2] || r[1] > r[3]) {
                throw new IllegalArgumentException("need x1 <= x2 and y1 <= y2 in tarp " + i);
            }
            ys[2 * i] = r[1];
            ys[2 * i + 1] = r[3];
            ev[2 * i] = new long[] {r[0], 1, r[1], r[3]};
            ev[2 * i + 1] = new long[] {r[2], -1, r[1], r[3]};
        }
        long[] u = Arrays.stream(ys).sorted().distinct().toArray();
        int m = u.length - 1;
        if (m < 1) {
            return new long[] {0, 0};
        }
        Arrays.sort(ev, (a, b) -> Long.compare(a[0], b[0]));
        Tree t = new Tree(u);
        long one = 0;
        long two = 0;
        for (int k = 0; k < ev.length; k++) {
            if (k > 0) {
                long dx = ev[k][0] - ev[k - 1][0];
                one += dx * t.len1[1];
                two += dx * t.len2[1];
            }
            int lo = Arrays.binarySearch(u, ev[k][2]);
            int hi = Arrays.binarySearch(u, ev[k][3]);
            if (lo < hi) {
                t.update(1, 0, m, lo, hi, (int) ev[k][1]);
            }
        }
        return new long[] {one, two};
    }

    /** Segment tree over elementary y-intervals [u[i], u[i+1]). */
    private static final class Tree {
        private final long[] u;
        private final int[] cnt;
        private final long[] len1;
        private final long[] len2;

        Tree(long[] u) {
            this.u = u;
            int size = 4 * u.length;
            cnt = new int[size];
            len1 = new long[size];
            len2 = new long[size];
        }

        void update(int node, int l, int r, int ql, int qr, int d) {
            if (qr <= l || r <= ql) {
                return;
            }
            if (ql <= l && r <= qr) {
                cnt[node] += d;
            } else {
                int mid = (l + r) >>> 1;
                update(2 * node, l, mid, ql, qr, d);
                update(2 * node + 1, mid, r, ql, qr, d);
            }
            boolean leaf = r - l == 1;
            long full = u[r] - u[l];
            if (cnt[node] >= 2) {
                len1[node] = full;
                len2[node] = full;
            } else if (cnt[node] == 1) {
                len1[node] = full;
                len2[node] = leaf ? 0 : len1[2 * node] + len1[2 * node + 1];
            } else {
                len1[node] = leaf ? 0 : len1[2 * node] + len1[2 * node + 1];
                len2[node] = leaf ? 0 : len2[2 * node] + len2[2 * node + 1];
            }
        }
    }

    /** COVERED only if both claimed areas are right. */
    public static Grade grade(long[][] rects, long union, long overlap) {
        long[] s = sweep(rects);
        return s[0] == union && s[1] == overlap ? Grade.COVERED : Grade.EXPOSED;
    }

    /** The Forgemaster's line for a survey. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case COVERED -> "Forgemaster: every patch of ground accounted for, doubled or not. The rain can come.";
            case EXPOSED -> "Forgemaster: your sums leave ground bare or count it twice. Pace the yard again.";
        };
    }
}
