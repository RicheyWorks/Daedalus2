// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.Deque;
import java.util.List;

/**
 * G305 The Stay Triangles: the rigger wants mast stays whose mast height, deck run and stay length
 * are all whole cubits, so a^2 + b^2 = c^2. Primitive triples grow from (3, 4, 5) down Berggren's
 * ternary tree; every triple is a multiple of one. Lists primitives up to a perimeter, and all
 * triples with a given perimeter or a given stay length. Triples are {a, b, c} with a < b < c.
 */
public final class StayTriangles {

    public static final String QUEST_ID = "q_stay_triangles";
    public static final long MAX_PERIMETER = 10_000_000L;

    private static final Comparator<long[]> ORDER =
            Comparator.<long[]>comparingLong(t -> t[0] + t[1] + t[2]).thenComparingLong(t -> t[0]);

    private StayTriangles() { }

    /** Primitive triples with perimeter at most maxPerimeter, by perimeter then shortest leg. */
    public static List<long[]> primitives(long maxPerimeter) {
        if (maxPerimeter < 0 || maxPerimeter > MAX_PERIMETER) {
            throw new IllegalArgumentException("perimeter out of range: " + maxPerimeter);
        }
        List<long[]> out = new ArrayList<>();
        Deque<long[]> todo = new ArrayDeque<>();
        todo.add(new long[] {3, 4, 5});
        while (!todo.isEmpty()) {
            long[] t = todo.poll();
            long a = t[0];
            long b = t[1];
            long c = t[2];
            if (a + b + c > maxPerimeter) {
                continue;
            }
            out.add(new long[] {Math.min(a, b), Math.max(a, b), c});
            todo.add(new long[] {a - 2 * b + 2 * c, 2 * a - b + 2 * c, 2 * a - 2 * b + 3 * c});
            todo.add(new long[] {a + 2 * b + 2 * c, 2 * a + b + 2 * c, 2 * a + 2 * b + 3 * c});
            todo.add(new long[] {-a + 2 * b + 2 * c, -2 * a + b + 2 * c, -2 * a + 2 * b + 3 * c});
        }
        out.sort(ORDER);
        return out;
    }

    /** Every triple (primitive or not) with perimeter exactly p, by shortest leg. */
    public static List<long[]> withPerimeter(long p) {
        List<long[]> out = new ArrayList<>();
        for (long[] t : primitives(p)) {
            long s = t[0] + t[1] + t[2];
            if (p % s == 0) {
                long k = p / s;
                out.add(new long[] {k * t[0], k * t[1], k * t[2]});
            }
        }
        out.sort(ORDER);
        return out;
    }

    /** Every triple with stay length (hypotenuse) exactly c, by shortest leg. */
    public static List<long[]> withHypotenuse(long c) {
        if (c < 1 || 3 * c > MAX_PERIMETER) {
            throw new IllegalArgumentException("stay length out of range: " + c);
        }
        List<long[]> out = new ArrayList<>();
        for (long[] t : primitives(3 * c)) {
            if (c % t[2] == 0) {
                long k = c / t[2];
                out.add(new long[] {k * t[0], k * t[1], c});
            }
        }
        out.sort(Comparator.comparingLong(t -> t[0]));
        return out;
    }

    /** Quest q_stay_triangles: do the rigger's three whole lengths make a right triangle? */
    public static boolean quest(long a, long b, long c) {
        if (a < 1 || b < 1 || c < 1 || c > 3_000_000_000L) {
            return false;
        }
        return a * a + b * b == c * c;
    }
}