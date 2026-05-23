// SPDX-License-Identifier: MIT

package com.daedalus.model;

import java.util.EnumSet;
import java.util.Set;

/**
 * A maze cell holds (a) where it sits in the grid and (b) which of its four walls are carved.
 *
 * <p>The maze is represented in <i>cell graph</i> form (not tile-grid form): each cell knows
 * its open neighbors. Generators carve walls by toggling these {@code openWalls} sets.
 * The renderer / {@link MazeUtils} converts to a tile grid for display.
 */
public class Cell {

    private final Point position;
    private final EnumSet<Direction> openWalls = EnumSet.noneOf(Direction.class);
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

    public void open(Direction d) { openWalls.add(d); }
    public void close(Direction d) { openWalls.remove(d); }
    public boolean isOpen(Direction d) { return openWalls.contains(d); }

    public Set<Direction> openWalls() {
        return EnumSet.copyOf(openWalls);
    }

    public boolean isDeadEnd() { return openWalls.size() == 1; }
    public boolean isJunction() { return openWalls.size() >= 3; }
    public boolean isCorridor() { return openWalls.size() == 2; }
    public int degree() { return openWalls.size(); }

    public boolean isVisited() { return visited; }
    public void markVisited() { this.visited = true; }
    public void clearVisited() { this.visited = false; }
}
