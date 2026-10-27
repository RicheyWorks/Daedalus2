// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.Arrays;
import java.util.Comparator;
import java.util.TreeSet;

/**
 * G455 The Crossing Lines: the bosun asks whether any two mooring lines (straight segments
 * between integer points) touch or cross, and if so names one such pair. Uses the Shamos-Hoey
 * sweep line, O(n log n), with exact integer comparisons. Takes 1 to 5000 segments
 * {x1, y1, x2, y2} within 10^5; a segment may be a single point. Shared endpoints and collinear
 * overlaps count as meeting.
 */
public final class CrossingLines {

    public static final String QUEST_ID = "q_crossing_lines";
    public static final int MAX_LINES = 5000;
    public static final long MAX_COORD = 100_000;

    private CrossingLines() { }

    private static long cross(long ox, long oy, long ax, long ay, long bx, long by) {
        return (ax - ox) * (by - oy) - (ay - oy) * (bx - ox);
    }

    private static boolean box(long a, long b, long c) {
        return Math.min(a, b) <= c && c <= Math.max(a, b);
    }

    /** True when the closed segments share at least one point. */
    public static boolean meet(long[] s, long[] t) {
        long d1 = Long.signum(cross(s[0], s[1], s[2], s[3], t[0], t[1]));
        long d2 = Long.signum(cross(s[0], s[1], s[2], s[3], t[2], t[3]));
        long d3 = Long.signum(cross(t[0], t[1], t[2], t[3], s[0], s[1]));
        long d4 = Long.signum(cross(t[0], t[1], t[2], t[3], s[2], s[3]));
        if (d1 * d2 < 0 && d3 * d4 < 0) {
            return true;
        }
        return d1 == 0 && box(s[0], s[2], t[0]) && box(s[1], s[3], t[1])
            || d2 == 0 && box(s[0], s[2], t[2]) && box(s[1], s[3], t[3])
            || d3 == 0 && box(t[0], t[2], s[0]) && box(t[1], t[3], s[1])
            || d4 == 0 && box(t[0], t[2], s[2]) && box(t[1], t[3], s[3]);
    }

    private static long[][] normalize(long[][] lines) {
        if (lines == null || lines.length < 1 || lines.length > MAX_LINES) {
            throw new IllegalArgumentException("need 1 to " + MAX_LINES + " lines");
        }
        long[][] g = new long[lines.length][];
        for (int i = 0; i < lines.length; i++) {
            long[] s = lines[i];
            if (s == null || s.length != 4) {
                throw new IllegalArgumentException("lines are {x1, y1, x2, y2}");
            }
            for (long v : s) {
                if (Math.abs(v) > MAX_COORD) {
                    throw new IllegalArgumentException("coordinates within 10^5");
                }
            }
            boolean swap = s[2] < s[0] || s[2] == s[0] && s[3] < s[1];
            g[i] = swap ? new long[] {s[2], s[3], s[0], s[1]} : s.clone();
        }
        return g;
    }

    /** One pair {i, j} with i &lt; j of meeting lines, or an empty array when none meet. */
    public static int[] findPair(long[][] lines) {
        long[][] g = normalize(lines);
        int n = g.length;
        Comparator<Integer> byY = (a, b) -> {
            if (a.intValue() == b.intValue()) {
                return 0;
            }
            long x = Math.max(g[a][0], g[b][0]);
            int c = compareY(g[a], g[b], x);
            return c != 0 ? c : Integer.compare(a, b);
        };
        long[][] ev = new long[2 * n][];
        for (int i = 0; i < n; i++) {
            ev[2 * i] = new long[] {g[i][0], 0, i};
            ev[2 * i + 1] = new long[] {g[i][2], 1, i};
        }
        Arrays.sort(ev, (p, q) -> p[0] != q[0] ? Long.compare(p[0], q[0]) : Long.compare(p[1], q[1]));
        TreeSet<Integer> act = new TreeSet<>(byY);
        for (long[] e : ev) {
            int id = (int) e[2];
            if (e[1] == 0) {
                Integer hi = act.ceiling(id);
                Integer lo = act.floor(id);
                if (hi != null && meet(g[hi], g[id])) {
                    return pair(hi, id);
                }
                if (lo != null && meet(g[lo], g[id])) {
                    return pair(lo, id);
                }
                act.add(id);
            } else {
                Integer hi = act.higher(id);
                Integer lo = act.lower(id);
                if (hi != null && lo != null && meet(g[hi], g[lo])) {
                    return pair(hi, lo);
                }
                act.remove(id);
            }
        }
        return new int[0];
    }

    private static int[] pair(int a, int b) {
        return new int[] {Math.min(a, b), Math.max(a, b)};
    }

    /** Compare the heights of two left-to-right segments at x (a vertical one uses its low end). */
    private static int compareY(long[] a, long[] b, long x) {
        long na;
        long da;
        if (a[0] == a[2]) {
            na = a[1];
            da = 1;
        } else {
            da = a[2] - a[0];
            na = a[1] * da + (a[3] - a[1]) * (x - a[0]);
        }
        long nb;
        long db;
        if (b[0] == b[2]) {
            nb = b[1];
            db = 1;
        } else {
            db = b[2] - b[0];
            nb = b[1] * db + (b[3] - b[1]) * (x - b[0]);
        }
        return Long.compare(na * db, nb * da);
    }

    /** Quest q_crossing_lines: the bosun says whether any two lines meet. */
    public static boolean quest(long[][] lines, boolean anyMeet) {
        return (findPair(lines).length == 2) == anyMeet;
    }
}