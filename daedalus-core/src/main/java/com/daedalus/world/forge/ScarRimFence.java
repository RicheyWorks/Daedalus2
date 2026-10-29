// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.SplittableRandom;

/**
 * Scar Rim Fence (contest gap G198): meteor shards lie scattered on the floor of the Meteor Scar ({@link ScarDig}).
 * Fence them all with the shortest iron fence: the convex hull.
 *
 * <p>The geometry is plain: points are {@code int[][]} of {@code {x, y}}. {@link #hull} is Andrew's monotone chain with
 * exact long cross products (duplicates and collinear points dropped), corners counter-clockwise from the lowest-left
 * point. Any project can use it for territory outlines or navigation bounds.
 */
public final class ScarRimFence {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_scar_rim_fence";

    /** How the player's fence went. */
    public enum Grade { TAUT, SAGGY, BREACHED }

    private ScarRimFence() {
    }

    /** {@code n} seeded shards with coordinates in [0, size). Same seed, same scar. */
    public static int[][] shards(long seed, int n, int size) {
        if (n < 0 || size < 1) {
            throw new IllegalArgumentException("need n >= 0 and size >= 1");
        }
        SplittableRandom r = new SplittableRandom(seed);
        int[][] p = new int[n][];
        for (int i = 0; i < n; i++) {
            p[i] = new int[] {r.nextInt(size), r.nextInt(size)};
        }
        return p;
    }

    /** Cross product of (b - a) x (c - a); positive when a, b, c turn counter-clockwise. */
    public static long cross(int[] a, int[] b, int[] c) {
        return (long) (b[0] - a[0]) * (c[1] - a[1]) - (long) (b[1] - a[1]) * (c[0] - a[0]);
    }

    /** Hull corners, counter-clockwise from the lowest-left point, as fresh {x, y} pairs. */
    public static List<int[]> hull(int[][] points) {
        int[][] p = new int[points.length][];
        for (int i = 0; i < p.length; i++) {
            if (points[i].length != 2) {
                throw new IllegalArgumentException("points are {x, y}");
            }
            p[i] = points[i].clone();
        }
        Arrays.sort(p, (a, b) -> a[0] != b[0] ? Integer.compare(a[0], b[0]) : Integer.compare(a[1], b[1]));
        List<int[]> u = new ArrayList<>();
        for (int[] q : p) {
            if (u.isEmpty() || u.get(u.size() - 1)[0] != q[0] || u.get(u.size() - 1)[1] != q[1]) {
                u.add(q);
            }
        }
        int n = u.size();
        if (n <= 2) {
            return u;
        }
        int[][] h = new int[2 * n][];
        int k = 0;
        for (int i = 0; i < n; i++) {
            while (k >= 2 && cross(h[k - 2], h[k - 1], u.get(i)) <= 0) {
                k--;
            }
            h[k++] = u.get(i);
        }
        for (int i = n - 2, lo = k + 1; i >= 0; i--) {
            while (k >= lo && cross(h[k - 2], h[k - 1], u.get(i)) <= 0) {
                k--;
            }
            h[k++] = u.get(i);
        }
        List<int[]> out = new ArrayList<>();
        for (int i = 0; i < k - 1; i++) {
            out.add(h[i]);
        }
        return out;
    }

    /** Closed perimeter of a polygon given in order. */
    public static double perimeter(List<int[]> poly) {
        if (poly.size() < 2) {
            return 0;
        }
        double s = 0;
        for (int i = 0; i < poly.size(); i++) {
            int[] a = poly.get(i);
            int[] b = poly.get((i + 1) % poly.size());
            s += Math.hypot(b[0] - a[0], b[1] - a[1]);
        }
        return s;
    }

    /** Twice the enclosed area (shoelace), exact; positive for counter-clockwise order. */
    public static long area2(List<int[]> poly) {
        long s = 0;
        for (int i = 0; i < poly.size(); i++) {
            int[] a = poly.get(i);
            int[] b = poly.get((i + 1) % poly.size());
            s += (long) a[0] * b[1] - (long) b[0] * a[1];
        }
        return s;
    }

    /**
     * Grades a fence through the shards at {@code posts} (indices, in walking order): BREACHED if any shard lies
     * outside the fenced region, TAUT if the fence is as short as the hull, SAGGY otherwise.
     */
    public static Grade grade(int[][] points, List<Integer> posts) {
        int[][] pp = new int[posts.size()][];
        for (int i = 0; i < pp.length; i++) {
            pp[i] = points[posts.get(i)];
        }
        List<int[]> region = hull(pp);
        for (int[] q : points) {
            if (!inside(region, q)) {
                return Grade.BREACHED;
            }
        }
        List<int[]> walk = new ArrayList<>(Arrays.asList(pp));
        double best = perimeter(hull(points));
        return perimeter(walk) <= best + 1e-9 ? Grade.TAUT : Grade.SAGGY;
    }

    /** True if q is inside or on a convex counter-clockwise polygon (or on it when degenerate). */
    static boolean inside(List<int[]> h, int[] q) {
        if (h.isEmpty()) {
            return false;
        }
        if (h.size() == 1) {
            return h.get(0)[0] == q[0] && h.get(0)[1] == q[1];
        }
        if (h.size() == 2) {
            int[] a = h.get(0);
            int[] b = h.get(1);
            return cross(a, b, q) == 0 && Math.min(a[0], b[0]) <= q[0] && q[0] <= Math.max(a[0], b[0])
                    && Math.min(a[1], b[1]) <= q[1] && q[1] <= Math.max(a[1], b[1]);
        }
        for (int i = 0; i < h.size(); i++) {
            if (cross(h.get(i), h.get((i + 1) % h.size()), q) < 0) {
                return false;
            }
        }
        return true;
    }

    /** The Forgemaster's line for a fence. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case TAUT -> "Forgemaster: not a link of iron wasted. Every shard is in.";
            case SAGGY -> "Forgemaster: every shard is in, but that fence wanders. Pull it tight.";
            case BREACHED -> "Forgemaster: a shard sits outside your fence. The scavengers will thank you.";
        };
    }
}
