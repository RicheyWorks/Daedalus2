// SPDX-License-Identifier: MIT

package com.daedalus.engine.generators;

import com.daedalus.engine.AbstractMazeGenerator;
import com.daedalus.engine.MazeGrid;
import com.daedalus.model.AlgorithmDescriptor;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.util.DSU;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Random;

/**
 * Randomized Kruskal's. Treat every wall as an edge, shuffle, then union-find:
 * carve the wall if its two cells are in different components.
 *
 * <p>Bias: very uniform — no preference for any direction or topology. Lots of short
 * branches, similar to Prim's but with a slightly different texture.
 *
 * <p>Complexity: O(n α(n)) effectively-linear time with path compression + union by rank.
 *
 * <p>Cells are flattened to {@code int} keys via {@code r * cols + c} so the shared
 * {@link DSU} can use its int-array storage. The previous inline implementation kept a
 * {@code HashMap<Point, Point>} per generator instance — same complexity, more boxing.
 */
public class KruskalsGenerator extends AbstractMazeGenerator {

    @Override public String id() { return "kruskals"; }
    @Override public String displayName() { return "Kruskal's (randomized)"; }

    @Override
    public AlgorithmDescriptor descriptor() {
        return new AlgorithmDescriptor(
                id(), displayName(), "generator",
                "O(n α(n)) ≈ O(n) time",
                "Very uniform; no directional or topological bias",
                "Randomized Kruskal's via union-find on edges. Most 'unbiased' generator.");
    }

    private record Edge(Point a, Point b) {}

    @Override
    public MazeGrid generate(int rows, int cols, long seed, MazeStats stats) {
        Random rng = new Random(seed);
        MazeGrid grid = new MazeGrid(rows, cols);

        // Build edge list: each cell to its E and S neighbor (avoids duplicates).
        List<Edge> edges = new ArrayList<>(rows * cols * 2);
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                Point p = new Point(r, c);
                if (c + 1 < cols) edges.add(new Edge(p, new Point(r, c + 1)));
                if (r + 1 < rows) edges.add(new Edge(p, new Point(r + 1, c)));
            }
        }
        Collections.shuffle(edges, rng);

        DSU dsu = new DSU(rows * cols);
        for (Edge e : edges) {
            // Early exit: once the spanning tree is complete, every remaining edge is a
            // same-set skip. Bailing here saves the shuffle's tail end of cycle-creating
            // edges — roughly half of the original edge list on a typical maze.
            if (dsu.isFullyConnected()) break;

            stats.recordFrontier(edges.size());
            int ka = e.a.row() * cols + e.a.col();
            int kb = e.b.row() * cols + e.b.col();
            if (!dsu.union(ka, kb)) continue;          // already connected — skip carve
            grid.carve(grid.cell(e.a), MazeGrid.directionBetween(e.a, e.b));
            stats.incVisited();
        }
        stats.finish(true);
        return grid;
    }
}
