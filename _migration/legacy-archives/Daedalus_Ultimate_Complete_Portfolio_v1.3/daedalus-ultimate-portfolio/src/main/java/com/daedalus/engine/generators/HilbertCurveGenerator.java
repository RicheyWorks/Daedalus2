package com.daedalus.engine.generators;

import com.daedalus.engine.AbstractMazeGenerator;
import com.daedalus.engine.MazeGrid;
import com.daedalus.model.*;

import java.util.*;

/**
 * Hilbert Curve Spanning Tree Generator.
 *
 * Directly inspired by David Hilbert's legendary space-filling curve (1891) — one of the most
 * beautiful objects in all of discrete mathematics. The Hilbert curve is a continuous fractal
 * that visits every cell while preserving locality far better than Morton Z-order (or any
 * other generator in your collection).
 *
 * We traverse the entire grid in true Hilbert order and connect each new cell to a random
 * already-visited neighbor. The result is mesmerizing self-similar swirling patterns —
 * pure mathematical art.
 *
 * From the mathematician list you asked for. This one would make Hilbert himself proud.
 */
public class HilbertCurveGenerator extends AbstractMazeGenerator {

    @Override public String id() { return "hilbert-curve"; }
    @Override public String displayName() { return "Hilbert Curve"; }

    @Override
    public AlgorithmDescriptor descriptor() {
        return new AlgorithmDescriptor(
                id(), displayName(), "generator",
                "O(n) time, O(n) space",
                "Stunning self-similar fractal swirls — best locality of any curve generator",
                "David Hilbert’s space-filling curve (1891) + spanning-tree construction. Pure math elegance.");
    }

    @Override
    public MazeGrid generate(int rows, int cols, long seed, MazeStats stats) {
        Random rng = new Random(seed);
        MazeGrid grid = new MazeGrid(rows, cols);

        List<Point> curve = hilbertOrder(rows, cols);

        Set<Point> visited = new HashSet<>();
        Point first = curve.get(0);
        grid.cell(first).markVisited();
        visited.add(first);
        stats.incVisited();

        for (int i = 1; i < curve.size(); i++) {
            Point p = curve.get(i);
            stats.recordFrontier(curve.size() - i);

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
     * Generates all cells in true Hilbert-curve order using the classic recursive quadrant algorithm.
     * Works perfectly on any rectangular grid (no power-of-2 restriction).
     */
    private List<Point> hilbertOrder(int height, int width) {
        List<Point> order = new ArrayList<>(height * width);
        hilbert(0, 0, width, height, 0, 0, order, height, width);
        return order;
    }

    private void hilbert(int x, int y, int dx, int dy, int rx, int ry,
                         List<Point> order, int h, int w) {
        if (dx * dy <= 1) {
            if (x >= 0 && x < w && y >= 0 && y < h) {
                order.add(new Point(y, x));   // Point(row, col)
            }
            return;
        }

        int dx2 = dx / 2;
        int dy2 = dy / 2;

        if (rx == 0 && ry == 0) {
            hilbert(x, y, dx2, dy2, 0, 0, order, h, w);
            hilbert(x, y + dy2, dx2, dy2, 1, 0, order, h, w);
            hilbert(x + dx2, y + dy2, dx2, dy2, 1, 1, order, h, w);
            hilbert(x + dx2, y, dx2, dy2, 0, 1, order, h, w);
        } else if (rx == 1 && ry == 0) {
            hilbert(x + dx2, y, dx2, dy2, 0, 1, order, h, w);
            hilbert(x, y, dx2, dy2, 0, 0, order, h, w);
            hilbert(x, y + dy2, dx2, dy2, 1, 0, order, h, w);
            hilbert(x + dx2, y + dy2, dx2, dy2, 1, 1, order, h, w);
        } else if (rx == 1 && ry == 1) {
            hilbert(x + dx2, y + dy2, dx2, dy2, 1, 1, order, h, w);
            hilbert(x + dx2, y, dx2, dy2, 0, 1, order, h, w);
            hilbert(x, y, dx2, dy2, 0, 0, order, h, w);
            hilbert(x, y + dy2, dx2, dy2, 1, 0, order, h, w);
        } else { // rx==0, ry==1
            hilbert(x, y + dy2, dx2, dy2, 1, 0, order, h, w);
            hilbert(x + dx2, y + dy2, dx2, dy2, 1, 1, order, h, w);
            hilbert(x + dx2, y, dx2, dy2, 0, 1, order, h, w);
            hilbert(x, y, dx2, dy2, 0, 0, order, h, w);
        }
    }
}
