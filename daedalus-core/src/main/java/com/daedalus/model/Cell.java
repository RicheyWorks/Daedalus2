// SPDX-License-Identifier: MIT

package com.daedalus.model;

import java.util.EnumSet;
import java.util.Set;

/**
 * A maze cell holds (a) where it sits in the grid and (b) which of its four walls are carved.
 *
 * <p>The maze is represented in <i>cell graph</i> form (not tile-grid form): each cell knows
 * its open neighbors. Generators carve walls by toggling a four-bit mask.
 * The renderer / {@link MazeUtils} converts to a tile grid for display.
 */
public class Cell {

    private final Point position;
    /** N/S/E/W packed in the low nibble — EnumSet was an object per cell for four bits. */
    private byte openMask;
    private boolean visited = false;

    public Cell(int row, int col) {
        this.position = new Point(row, col);
    }

    public Cell(Point position) {
        this.position = position;
    }

    public Point position() { return position; }
    public int row() { return position.row(); }
    public int col() { return position.col(); }

    public void open(Direction d) { openMask |= (byte) bit(d); }
    public void close(Direction d) { openMask &= (byte) ~bit(d); }
    public boolean isOpen(Direction d) { return (openMask & bit(d)) != 0; }

    public Set<Direction> openWalls() {
        EnumSet<Direction> walls = EnumSet.noneOf(Direction.class);
        for (Direction d : Direction.values()) {
            if (isOpen(d)) {
                walls.add(d);
            }
        }
        return walls;
    }

    public boolean isDeadEnd() { return degree() == 1; }
    public boolean isJunction() { return degree() >= 3; }
    public boolean isCorridor() { return degree() == 2; }
    public int degree() { return Integer.bitCount(openMask & 0x0F); }

    private static int bit(Direction d) {
        return 1 << d.ordinal();
    }

    public boolean isVisited() { return visited; }
    public void markVisited() { this.visited = true; }
    public void clearVisited() { this.visited = false; }
}
