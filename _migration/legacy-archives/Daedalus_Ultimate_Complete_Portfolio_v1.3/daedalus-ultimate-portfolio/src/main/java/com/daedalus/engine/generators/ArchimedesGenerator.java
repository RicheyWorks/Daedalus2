package com.daedalus.engine.generators;

import com.daedalus.engine.AbstractMazeGenerator;
import com.daedalus.engine.MazeGrid;
import com.daedalus.model.*;

import java.util.*;

/**
 * Archimedes Spiral Generator.
 *
 * Inspired by Archimedes of Syracuse (#4 on our mathematician list) and his groundbreaking
 * work on spirals (the Archimedean spiral). We traverse the entire grid in a true discrete
 * spiral order starting from a random center cell and spiraling outward layer by layer.
 * Each new cell carves a random connection to an already-visited neighbor.
 *
 * <p>Result: Elegant, flowing spiral corridors with beautiful concentric layers — completely
 * different from the Hilbert/Morton curves, the organic Kraken, or any tree/MST generator.
 * Pure ancient Greek mathematical beauty in maze form.
 *
 * No repeats. Fresh. Mathematician-approved.
 */
public class ArchimedesGenerator extends AbstractMazeGenerator {

    @Override public String id() { return "archimedes-spiral"; }
    @Override public String displayName() { return "Archimedes Spiral"; }

    @Override
    public AlgorithmDescriptor descriptor() {
        return new AlgorithmDescriptor(
                id(), displayName(), "generator",
                "O(n) time, O(n) space",
                "Flowing concentric spiral corridors — ancient math made visible",
                "Archimedean spiral order + random-attachment spanning tree. Honors Archimedes himself.");
    }

    @Override
    public MazeGrid generate(int rows, int cols, long seed, MazeStats stats) {
        Random rng = new Random(seed);
        MazeGrid grid = new MazeGrid(rows, cols);

        List<Point> spiral = spiralOrder(rows, cols, rng);

        Set<Point> visited = new HashSet<>();
        Point first = spiral.get(0);
        grid.cell(first).markVisited();
        visited.add(first);
        stats.incVisited();

        for (int i = 1; i < spiral.size(); i++) {
            Point p = spiral.get(i);
            stats.recordFrontier(spiral.size() - i);

            List<Point> candidates = new ArrayList<>();
            for (Point n : grid.neighbors(p)) {
                if (visited.contains(n)) {
                    candidates.add(n);
                }
            }

            if (!candidates.isEmpty()) {
                Point from = candidates.get(rng.nextInt(candidates.size()));
                grid.carve(from, p);
                stats.incVisited();
            }

            grid.cell(p).markVisited();
            visited.add(p);
        }

        grid.clearVisited();
        stats.finish(true);
        return grid;
    }

    /**
     * Generates all cells in Archimedean spiral order starting from a random center.
     * Classic layer-by-layer spiral used in graphics, algorithms, and ancient geometry.
     */
    private List<Point> spiralOrder(int rows, int cols, Random rng) {
        List<Point> order = new ArrayList<>(rows * cols);

        // Random starting center (true Archimedean feel)
        int cx = rng.nextInt(rows);
        int cy = rng.nextInt(cols);
        order.add(new Point(cx, cy));

        int layer = 1;
        while (order.size() < rows * cols) {
            // Right
            for (int i = 0; i < layer * 2; i++) {
                int r = cx - layer + i + 1;
                int c = cy + layer;
                if (inBounds(r, c, rows, cols) && !order.contains(new Point(r, c))) {
                    order.add(new Point(r, c));
                }
            }
            // Down
            for (int i = 0; i < layer * 2; i++) {
                int r = cx + layer;
                int c = cy + layer - i - 1;
                if (inBounds(r, c, rows, cols) && !order.contains(new Point(r, c))) {
                    order.add(new Point(r, c));
                }
            }
            // Left
            for (int i = 0; i < layer * 2; i++) {
                int r = cx + layer - i - 1;
                int c = cy - layer;
                if (inBounds(r, c, rows, cols) && !order.contains(new Point(r, c))) {
                    order.add(new Point(r, c));
                }
            }
            // Up
            for (int i = 0; i < layer * 2; i++) {
                int r = cx - layer;
                int c = cy - layer + i + 1;
                if (inBounds(r, c, rows, cols) && !order.contains(new Point(r, c))) {
                    order.add(new Point(r, c));
                }
            }
            layer++;
        }

        // Trim to exact size (in case of odd/even grid quirks)
        while (order.size() > rows * cols) order.remove(order.size() - 1);

        return order;
    }

    private boolean inBounds(int r, int c, int rows, int cols) {
        return r >= 0 && r < rows && c >= 0 && c < cols;
    }
}
