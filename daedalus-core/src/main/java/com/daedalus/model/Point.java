// SPDX-License-Identifier: MIT

package com.daedalus.model;

/**
 * Immutable grid coordinate. Records give us free equals/hashCode for use as map keys.
 */
public record Point(int row, int col) {

    public Point translate(int dr, int dc) {
        return new Point(row + dr, col + dc);
    }

    public Point step(Direction d) {
        return new Point(row + d.dr(), col + d.dc());
    }

    public int manhattan(Point other) {
        return Math.abs(row - other.row) + Math.abs(col - other.col);
    }

    public double euclidean(Point other) {
        int dr = row - other.row;
        int dc = col - other.col;
        return Math.sqrt(dr * dr + dc * dc);
    }

    @Override
    public String toString() {
        return "(" + row + "," + col + ")";
    }
}
