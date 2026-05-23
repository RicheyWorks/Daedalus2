package com.daedalus.engine.generators;

import com.daedalus.engine.AbstractMazeGenerator;
import com.daedalus.engine.MazeGrid;
import com.daedalus.model.AlgorithmDescriptor;
import com.daedalus.model.Direction;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;

/**
 * Randomized Kruskal's. Treat every wall as an edge, shuffle, then union-find:
 * carve the wall if its two cells are in different components.
 *
 * <p>Bias: very uniform — no preference for any direction or topology. Lots of short
 * branches, similar to Prim's but with a slightly different texture.
 *
 * <p>Complexity: O(n α(n)) effectively-linear time with path compression + union by rank.
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

        DSU dsu = new DSU();
        for (Edge e : edges) {
            stats.recordFrontier(edges.size());
            if (dsu.find(e.a).equals(dsu.find(e.b))) continue;
            dsu.union(e.a, e.b);
            grid.carve(grid.cell(e.a), MazeGrid.directionBetween(e.a, e.b));
            stats.incVisited();
        }
        stats.finish(true);
        return grid;
    }

    /** Small union-find keyed on Point — handles arbitrary keys without coordinate flattening. */
    private static final class DSU {
        private final Map<Point, Point> parent = new HashMap<>();
        private final Map<Point, Integer> rank = new HashMap<>();

        Point find(Point p) {
            Point root = parent.computeIfAbsent(p, k -> k);
            while (!root.equals(parent.get(root))) {
                Point next = parent.get(root);
                parent.put(root, parent.get(next)); // path compression (single hop)
                root = next;
            }
            return root;
        }

        void union(Point a, Point b) {
            Point ra = find(a), rb = find(b);
            if (ra.equals(rb)) return;
            int rka = rank.getOrDefault(ra, 0);
            int rkb = rank.getOrDefault(rb, 0);
            if (rka < rkb) parent.put(ra, rb);
            else if (rkb < rka) parent.put(rb, ra);
            else { parent.put(rb, ra); rank.put(ra, rka + 1); }
        }
    }
}
