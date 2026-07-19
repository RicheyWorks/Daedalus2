// SPDX-License-Identifier: MIT

package com.daedalus.engine;

import com.daedalus.model.Point;

import java.util.Arrays;

/**
 * A {@link MazeGrid} with a per-cell entry cost.
 *
 * <p>The base {@code MazeGrid} is uniform-cost: every step the solver takes is worth
 * {@code 1.0}. {@code WeightedMazeGrid} overrides {@link MazeGrid#weightOf(Point)} so cost
 * becomes a property of the destination cell — useful for routing scenarios where some
 * nodes are more expensive to traverse than others (loaded servers, slow links, swampy
 * terrain). Edge cost from {@code u} to {@code v} is taken as {@code weightOf(v)}; the
 * starting cell is never charged because we begin there rather than entering it.
 *
 * <p>Because {@code DijkstraSolver} and {@code AStarSolver} consult {@code weightOf}
 * polymorphically, plain {@code MazeGrid} instances continue to behave as before
 * (uniform cost) and code that passes a {@code WeightedMazeGrid} to the same solver
 * automatically gets cost-aware routing — no API changes, no instanceof checks.
 *
 * <h3>Admissibility note for A*</h3>
 *
 * <p>{@link com.daedalus.solver.solvers.AStarSolver}'s default Manhattan heuristic
 * assumes unit edge cost and is admissible only when every weight is {@code >= 1.0}.
 * If the grid contains weights below {@code 1.0}, supply a custom heuristic — e.g.
 * {@code (a, b) -> a.manhattan(b) * minWeight} — to keep A* optimal. Dijkstra has no
 * heuristic and is always optimal under non-negative weights.
 *
 * <h3>Validation</h3>
 *
 * <p>Weights must be non-negative finite doubles. The setters reject {@code NaN},
 * negative infinity, and any negative finite value at the call site rather than letting
 * a malformed grid blow up inside the solver's priority queue.
 *
 * <h3>Example</h3>
 *
 * <pre>{@code
 * // Generate a Hilbert topology, then mark some nodes as overloaded.
 * MazeGrid base = new HilbertCurveGenerator().generate(64, 64, seed, new MazeStats());
 * WeightedMazeGrid wg = new WeightedMazeGrid(base);
 * wg.setWeight(new Point(42, 17), 10.0);   // hot spot: 10x cost to route through
 * wg.setWeight(new Point(43, 18), 25.0);
 *
 * List<Point> route = new DijkstraSolver().solve(wg, base.start(), base.goal(), new MazeStats());
 * }</pre>
 *
 * @since 1.0
 */
public class WeightedMazeGrid extends MazeGrid {

    private final double[][] weights;

    /**
     * Create a fresh weighted grid of the given size with all weights set to {@code 1.0}.
     * The structural state (cells, walls, start/goal) starts in the same default
     * configuration as a plain {@link MazeGrid}; you'll typically run a generator over it
     * just like any other {@code MazeGrid}.
     *
     * @param rows row count, must be {@code >= 1}
     * @param cols column count, must be {@code >= 1}
     */
    public WeightedMazeGrid(int rows, int cols) {
        super(rows, cols);
        this.weights = new double[rows][cols];
        for (double[] row : weights) {
            Arrays.fill(row, 1.0);
        }
    }

    /**
     * Wrap an existing {@link MazeGrid}'s structure into a weighted grid.
     *
     * <p>Useful for layering load/cost data on top of a maze produced by a generator
     * without re-generating it. The new grid copies the source's cell topology
     * (walls / passages) and start/goal points; weights start at {@code 1.0}.
     *
     * <p>Note: the copy is structural — modifying walls on either grid afterwards
     * will not propagate to the other.
     *
     * @param source the maze whose topology to copy; not modified
     */
    public WeightedMazeGrid(MazeGrid source) {
        super(source.rows(), source.cols());
        this.weights = new double[source.rows()][source.cols()];
        for (int r = 0; r < source.rows(); r++) {
            Arrays.fill(weights[r], 1.0);
            for (int c = 0; c < source.cols(); c++) {
                Point here = new Point(r, c);
                for (com.daedalus.model.Direction d : com.daedalus.model.Direction.values()) {
                    if (source.cell(here).isOpen(d)) {
                        cell(here).open(d);
                    }
                }
            }
        }
        setStart(source.start());
        setGoal(source.goal());
    }

    /**
     * Entry cost for a cell. Overrides {@link MazeGrid#weightOf(int, int)} — the
     * coordinate-indexed form — so any solver that consults the hook (Dijkstra, A*) sees the
     * per-cell weight instead of the uniform {@code 1.0} default.
     *
     * <p>Overriding the {@code (row, col)} form rather than {@link MazeGrid#weightOf(Point)}
     * is deliberate: the {@code Point} overload delegates here, so both stay consistent, and
     * the graph seam can ask for a weight by node id without allocating a {@code Point}.
     */
    @Override
    public double weightOf(int row, int col) {
        return weights[row][col];
    }

    /**
     * Set the entry cost of cell {@code p}.
     *
     * @param p cell to update; must be {@link #inBounds(Point)}
     * @param weight non-negative finite cost; rejected if NaN, infinite, or negative
     * @throws IllegalArgumentException if {@code weight} is invalid
     * @throws IndexOutOfBoundsException if {@code p} is out of bounds
     */
    public void setWeight(Point p, double weight) {
        validateWeight(weight);
        if (!inBounds(p)) {
            throw new IndexOutOfBoundsException("(" + p.row() + "," + p.col() + ") out of bounds");
        }
        weights[p.row()][p.col()] = weight;
    }

    /**
     * Read the entry cost for cell {@code p}. Equivalent to {@link #weightOf(Point)} but
     * named symmetrically with {@link #setWeight(Point, double)} for callers thinking in
     * terms of mutable load values.
     *
     * @param p cell to read; must be {@link #inBounds(Point)}
     * @throws IndexOutOfBoundsException if {@code p} is out of bounds
     */
    public double getWeight(Point p) {
        if (!inBounds(p)) {
            throw new IndexOutOfBoundsException("(" + p.row() + "," + p.col() + ") out of bounds");
        }
        return weights[p.row()][p.col()];
    }

    /**
     * Set every cell's weight to the same value.
     *
     * @param weight non-negative finite cost; rejected if NaN, infinite, or negative
     * @throws IllegalArgumentException if {@code weight} is invalid
     */
    public void setAllWeights(double weight) {
        validateWeight(weight);
        for (double[] row : weights) {
            Arrays.fill(row, weight);
        }
    }

    private static void validateWeight(double w) {
        if (Double.isNaN(w) || Double.isInfinite(w) || w < 0.0) {
            throw new IllegalArgumentException("Weight must be a non-negative finite number, got " + w);
        }
    }
}
