// SPDX-License-Identifier: MIT

package com.daedalus.engine.generators;

import com.daedalus.engine.AbstractMazeGenerator;
import com.daedalus.engine.MazeGrid;
import com.daedalus.model.AlgorithmDescriptor;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.util.DSU;

import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;

/**
 * Borůvka's algorithm (parallel MST). Each component simultaneously picks a random
 * outgoing edge, merges, and repeats. Classical "parallel union-find" MST published
 * by Otakar Borůvka in 1926 — mathematically beautiful, extremely uniform, produces a
 * very different "balanced growth" texture than Kruskal's or Prim's (components grow
 * in parallel waves).
 *
 * <p>Cells are flattened to {@code int} keys via {@code r * cols + c} so the shared
 * {@link DSU} can use int-array storage. The component-count post-sweep that the
 * earlier inline implementation needed (re-walk every cell, build a Set of roots) is
 * gone — {@link DSU#components()} tracks it incrementally.
 */
public class BoruvkasGenerator extends AbstractMazeGenerator {

    @Override public String id() { return "boruvkas"; }
    @Override public String displayName() { return "Borůvka's"; }

    @Override
    public AlgorithmDescriptor descriptor() {
        return new AlgorithmDescriptor(
                id(), displayName(), "generator",
                "O(n log n) time, O(n) space",
                "Ultra-uniform parallel merging; balanced component growth",
                "Mathematician's classic MST (1926). Rare in maze generators — very clean result.");
    }

    private record Edge(Point a, Point b) {}

    @Override
    public MazeGrid generate(int rows, int cols, long seed, MazeStats stats) {
        Random rng = new Random(seed);
        MazeGrid grid = new MazeGrid(rows, cols);
        DSU dsu = new DSU(rows * cols);

        while (dsu.components() > 1) {
            stats.recordFrontier(dsu.components());

            // Phase: each component picks ONE random outgoing edge. Keying the
            // candidate map by root index keeps the per-component "first cell wins"
            // semantics from the previous implementation (we walk cells in row-major
            // order; the first cell whose root has no candidate yet contributes one).
            Map<Integer, Edge> candidates = new HashMap<>();

            for (int r = 0; r < rows; r++) {
                for (int c = 0; c < cols; c++) {
                    Point p = new Point(r, c);
                    int root = dsu.find(r * cols + c);
                    if (candidates.containsKey(root)) continue;

                    List<Point> nbrs = grid.neighbors(p);
                    Collections.shuffle(nbrs, rng);     // RNG order preserved bit-for-bit

                    for (Point n : nbrs) {
                        int nKey = n.row() * cols + n.col();
                        if (root != dsu.find(nKey)) {
                            candidates.put(root, new Edge(p, n));
                            break;
                        }
                    }
                }
            }

            // Merge everything we found this phase. Some candidates may already be
            // unioned by the time we reach them (two roots pick edges into each other);
            // dsu.union returns false in that case and we skip the carve.
            for (Edge e : candidates.values()) {
                int ka = e.a.row() * cols + e.a.col();
                int kb = e.b.row() * cols + e.b.col();
                if (dsu.union(ka, kb)) {
                    grid.carve(grid.cell(e.a), MazeGrid.directionBetween(e.a, e.b));
                    stats.incVisited();
                }
            }
        }

        stats.finish(true);
        return grid;
    }
}
