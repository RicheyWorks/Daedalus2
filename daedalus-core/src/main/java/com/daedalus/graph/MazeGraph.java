// SPDX-License-Identifier: MIT

package com.daedalus.graph;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.Direction;
import com.daedalus.model.Point;

/**
 * A {@link Graph} <b>view</b> over a {@link MazeGrid} — the adapter that makes every maze an
 * instance of the general engine rather than a special case of it.
 *
 * <p>This is a live view, not a snapshot: it reads the grid's walls on each call, so carving after
 * construction is reflected immediately and construction costs nothing.
 *
 * <p>It is also allocation-free, which is the point. {@link MazeGrid#openNeighbors(Point)} builds a
 * fresh {@code ArrayList} on every call — in a search loop that is one short-lived list per node
 * expanded. Walking the wall flags by coordinate into a caller-owned buffer removes that
 * entirely. An earlier version of {@link #neighbors} still boxed a {@link Point} per hop;
 * {@link MazeGrid#isOpen(int, int, Direction)} is what made the claim true.
 *
 * <p>Node ids are {@code row * cols + col}, matching {@code solver.GridIndex}, so ids are
 * interchangeable between the two.
 */
public final class MazeGraph implements Graph {

    /** Cached because {@code Direction.values()} clones its array on every call. */
    private static final Direction[] DIRECTIONS = Direction.values();

    private final MazeGrid grid;
    private final int rows;
    private final int cols;

    public MazeGraph(MazeGrid grid) {
        this.grid = grid;
        this.rows = grid.rows();
        this.cols = grid.cols();
    }

    @Override
    public int nodeCount() {
        return rows * cols;
    }

    @Override
    public int maxDegree() {
        return DIRECTIONS.length;
    }

    @Override
    public int neighbors(int node, int[] out) {
        int row = node / cols;
        int col = node % cols;
        int count = 0;
        for (Direction d : DIRECTIONS) {
            if (!grid.isOpen(row, col, d)) {
                continue;
            }
            int nr = row + d.dr();
            int nc = col + d.dc();
            if (nr >= 0 && nr < rows && nc >= 0 && nc < cols) {
                out[count++] = nr * cols + nc;
            }
        }
        return count;
    }

    @Override
    public double edgeWeight(int from, int to) {
        // Matches MazeGrid semantics: cost is a property of the cell being entered.
        //
        // Note this reads the (row, col) accessor rather than pointOf(to): this method sits in
        // the innermost loop of every weighted search, and the Point it used to build was
        // allocated purely to be unwrapped again by the grid.
        //
        // The asymmetry is deliberate and load-bearing — cost(u -> v) is w(v), so
        // edgeWeight(a, b) != edgeWeight(b, a) whenever w(a) != w(b). Anything reasoning about
        // distances over this graph must treat it as directed; see LandmarkHeuristic, which
        // needs both forward and backward sweeps for exactly this reason.
        return grid.weightOf(to / cols, to % cols);
    }

    /** Dense id for a cell. */
    public int idOf(Point p) {
        return p.row() * cols + p.col();
    }

    /** The cell an id refers to. */
    public Point pointOf(int id) {
        return new Point(id / cols, id % cols);
    }
}
