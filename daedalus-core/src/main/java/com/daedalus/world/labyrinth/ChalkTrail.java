// SPDX-License-Identifier: MIT
package com.daedalus.world.labyrinth;

import java.util.LinkedHashSet;
import java.util.List;

/** Bounded maze path-marking rules. Host owns identity, inventory and persistence. */
public final class ChalkTrail {
    public record Point(int x, int z) {
        public Point {
            if (x < -1_000_000 || x > 1_000_000 || z < -1_000_000 || z > 1_000_000)
                throw new IllegalArgumentException("mark outside local coordinate bounds");
        }
    }
    public enum Result { ADDED, ALREADY_MARKED, OUT_OF_CHALK, FULL }
    private final int capacity;
    private final LinkedHashSet<Point> marks = new LinkedHashSet<>();
    private int charges;

    public ChalkTrail(int charges, int capacity) {
        if (charges < 0 || charges > 10_000 || capacity < 1 || capacity > 512)
            throw new IllegalArgumentException("invalid chalk supply or trail capacity");
        this.charges=charges;this.capacity=capacity;
    }
    public synchronized Result mark(Point point) {
        if (point==null) throw new IllegalArgumentException("point required");
        if (marks.contains(point)) return Result.ALREADY_MARKED;
        if (marks.size()==capacity) return Result.FULL;
        if (charges==0) return Result.OUT_OF_CHALK;
        marks.add(point);charges--;return Result.ADDED;
    }
    /** Chalk Eaters or approved world events erase a mark; spent chalk is never refunded. */
    public synchronized boolean erase(Point point) { return marks.remove(point); }
    public synchronized int charges() { return charges; }
    public synchronized List<Point> marks() { return List.copyOf(marks); }
}
