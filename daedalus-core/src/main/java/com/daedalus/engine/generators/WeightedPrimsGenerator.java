// SPDX-License-Identifier: MIT

package com.daedalus.engine.generators;

import com.daedalus.engine.AbstractMazeGenerator;
import com.daedalus.engine.MazeGrid;
import com.daedalus.model.AlgorithmDescriptor;
import com.daedalus.model.Direction;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;

import java.util.Comparator;
import java.util.PriorityQueue;
import java.util.Random;

/**
 * Prim's algorithm as an actual <b>minimum spanning tree</b> over a randomly weighted grid
 * (CLRS Ch. 23), rather than the frontier-shuffle variant in {@link PrimsGenerator}.
 *
 * <p>Every wall gets a weight up front; the frontier is a priority queue and we always carve the
 * cheapest wall leaving the tree. {@link PrimsGenerator} instead pulls a <em>uniformly random</em>
 * frontier wall, which is a different algorithm with a different bias — so the two produce
 * different mazes from the same seed.
 *
 * <h3>Why there's no "weight variance" knob</h3>
 *
 * <p>It's tempting to expose the weight distribution's spread as a texture control, but it would
 * do nothing: a minimum spanning tree depends only on the <em>relative order</em> of the edge
 * weights, and any strictly monotone reweighting (scaling, raising to a power, changing variance)
 * leaves that order — and therefore the MST — completely unchanged. With i.i.d. weights from any
 * continuous distribution you get the same uniformly random ordering and the same family of mazes.
 *
 * <p>What <em>does</em> change the texture is making the weights depend on <b>direction</b>, which
 * breaks the isotropy. {@link #WeightedPrimsGenerator(double)} takes a {@code horizontalBias}
 * subtracted from every east–west wall's weight: at {@code 0.0} the maze is isotropic, and as the
 * bias grows horizontal walls win ties more and more often, stretching the maze into long
 * east–west corridors.
 *
 * <p>Complexity: O(E log E) time (heap-driven), O(E) space. Deterministic for a given seed.
 */
public class WeightedPrimsGenerator extends AbstractMazeGenerator {

    private static final int EAST_EDGE = 0;
    private static final int SOUTH_EDGE = 1;

    private final double horizontalBias;

    /** Isotropic random-MST maze. */
    public WeightedPrimsGenerator() {
        this(0.0);
    }

    /**
     * @param horizontalBias amount subtracted from every east–west wall weight; {@code 0.0} is
     *                       isotropic, larger values stretch the maze into horizontal corridors
     */
    public WeightedPrimsGenerator(double horizontalBias) {
        this.horizontalBias = horizontalBias;
    }

    @Override public String id() { return "weighted-prims"; }

    @Override public String displayName() { return "Prim's (weighted MST)"; }

    @Override
    public AlgorithmDescriptor descriptor() {
        return new AlgorithmDescriptor(
                id(), displayName(), "generator",
                "O(E log E) time, O(E) space",
                "Isotropic by default; horizontalBias stretches corridors east-west",
                "True minimum spanning tree over a randomly weighted grid — always carves the "
                        + "cheapest frontier wall, unlike the random-frontier Prim's variant.");
    }

    private record WeightedWall(Point inside, Point outside, double weight) {}

    @Override
    public MazeGrid generate(int rows, int cols, long seed, MazeStats stats) {
        Random rng = new Random(seed);
        MazeGrid grid = new MazeGrid(rows, cols);

        // Fix a weight per wall up front so this really is an MST of one weighted graph.
        double[][][] weights = new double[rows][cols][2];
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                weights[r][c][EAST_EDGE] = rng.nextDouble() - horizontalBias;
                weights[r][c][SOUTH_EDGE] = rng.nextDouble();
            }
        }

        Point start = new Point(rng.nextInt(rows), rng.nextInt(cols));
        grid.cell(start).markVisited();
        stats.incVisited();

        PriorityQueue<WeightedWall> frontier =
                new PriorityQueue<>(Comparator.comparingDouble(WeightedWall::weight));
        pushWalls(grid, start, weights, frontier);

        while (!frontier.isEmpty()) {
            stats.recordFrontier(frontier.size());
            WeightedWall wall = frontier.poll();
            if (grid.cell(wall.outside()).isVisited()) {
                continue; // the far side joined the tree by a cheaper route
            }
            grid.carve(grid.cell(wall.inside()), MazeGrid.directionBetween(wall.inside(), wall.outside()));
            grid.cell(wall.outside()).markVisited();
            stats.incVisited();
            pushWalls(grid, wall.outside(), weights, frontier);
        }

        grid.clearVisited();
        stats.finish(true);
        return grid;
    }

    private void pushWalls(MazeGrid grid, Point inside, double[][][] weights,
                           PriorityQueue<WeightedWall> frontier) {
        for (Direction d : Direction.values()) {
            Point outside = inside.step(d);
            if (grid.inBounds(outside) && !grid.cell(outside).isVisited()) {
                frontier.add(new WeightedWall(inside, outside, weightOf(inside, outside, weights)));
            }
        }
    }

    /** Weight of the wall between two adjacent cells, stored on the north/west cell of the pair. */
    private static double weightOf(Point a, Point b, double[][][] weights) {
        if (a.row() == b.row()) {
            int westCol = Math.min(a.col(), b.col());
            return weights[a.row()][westCol][EAST_EDGE];
        }
        int northRow = Math.min(a.row(), b.row());
        return weights[northRow][a.col()][SOUTH_EDGE];
    }
}
