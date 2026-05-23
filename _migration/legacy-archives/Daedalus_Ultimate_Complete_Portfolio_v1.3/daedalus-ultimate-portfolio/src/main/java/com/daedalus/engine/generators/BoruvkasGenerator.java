package com.daedalus.engine.generators;

import com.daedalus.engine.AbstractMazeGenerator;
import com.daedalus.engine.MazeGrid;
import com.daedalus.model.*;

import java.util.*;

/**
 * Borůvka's algorithm (parallel MST). 
 * Each component simultaneously picks a random outgoing edge, merges, and repeats.
 * This is the classic "parallel union-find" MST algorithm published by Otakar Borůvka in 1926
 * — mathematically beautiful, extremely uniform, and produces a very different "balanced growth"
 * texture than Kruskal's or Prim's (components grow in parallel waves).
 *
 * <p>Not in your current collection. Pure graph-theory gold, CLRS-adjacent, and original.
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

    /** Exact same tiny DSU as KruskalsGenerator (path compression + union-by-rank). */
    private static final class DSU {
        private final Map<Point, Point> parent = new HashMap<>();
        private final Map<Point, Integer> rank = new HashMap<>();

        Point find(Point p) {
            Point root = parent.computeIfAbsent(p, k -> k);
            while (!root.equals(parent.get(root))) {
                Point next = parent.get(root);
                parent.put(root, parent.get(next)); // path compression
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

    @Override
    public MazeGrid generate(int rows, int cols, long seed, MazeStats stats) {
        Random rng = new Random(seed);
        MazeGrid grid = new MazeGrid(rows, cols);
        DSU dsu = new DSU();

        int components = rows * cols;
        while (components > 1) {
            stats.recordFrontier(components);

            // Phase: each component picks ONE random outgoing edge
            Map<Point, Edge> candidates = new HashMap<>();

            for (int r = 0; r < rows; r++) {
                for (int c = 0; c < cols; c++) {
                    Point p = new Point(r, c);
                    Point root = dsu.find(p);

                    if (candidates.containsKey(root)) continue; // already picked for this component

                    List<Point> nbrs = grid.neighbors(p);
                    Collections.shuffle(nbrs, rng);

                    for (Point n : nbrs) {
                        if (!root.equals(dsu.find(n))) {
                            candidates.put(root, new Edge(p, n));
                            break;
                        }
                    }
                }
            }

            // Merge everything we found this phase
            int added = 0;
            for (Edge e : candidates.values()) {
                Point ra = dsu.find(e.a);
                Point rb = dsu.find(e.b);
                if (!ra.equals(rb)) {
                    dsu.union(e.a, e.b);
                    // Same carve style as KruskalsGenerator
                    grid.carve(grid.cell(e.a), MazeGrid.directionBetween(e.a, e.b));
                    stats.incVisited();
                    added++;
                }
            }

            // Recount components (cheap for maze sizes)
            Set<Point> roots = new HashSet<>();
            for (int r = 0; r < rows; r++) {
                for (int c = 0; c < cols; c++) {
                    roots.add(dsu.find(new Point(r, c)));
                }
            }
            components = roots.size();
        }

        stats.finish(true);
        return grid;
    }
}
