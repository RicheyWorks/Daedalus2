// SPDX-License-Identifier: MIT

package com.daedalus.engine.generators;

import com.daedalus.engine.AbstractMazeGenerator;
import com.daedalus.engine.MazeGrid;
import com.daedalus.model.*;

import java.util.*;

/**
 * Hilbert-order spanning tree.
 *
 * <p>Walks the grid in the canonical Hilbert {@code d2xy} order and attaches each cell to a
 * <em>random already-visited neighbour</em>. The curve itself has excellent locality; this
 * tree does not inherit it. Measured stretch at 32×32 (20,000 random pairs) puts the
 * generator at mean 4.62 versus Prim's 2.48, with more than double the diameter. Carving
 * strictly along the curve is worse still — a Hamiltonian path of diameter 1023.
 *
 * <p>Prefer {@code prims} or {@code archimedes-spiral} when the maze is a network topology.
 * This generator stays in the roster for the swirl texture, not for the locality the
 * vision documents once claimed.
 */
public class HilbertCurveGenerator extends AbstractMazeGenerator {

    @Override public String id() { return "hilbert-curve"; }
    @Override public String displayName() { return "Hilbert Curve"; }

    @Override
    public AlgorithmDescriptor descriptor() {
        return new AlgorithmDescriptor(
                id(), displayName(), "generator",
                "O(n) time, O(n) space",
                "Self-similar swirls; Hilbert order, random attach — not the curve's locality",
                "Walks cells in Hilbert order (1891) and attaches each to a random visited neighbour. "
                        + "The curve preserves locality; the tree does not. Prefer prims for topologies.");
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

        // Cells that arrive with no visited neighbour yet. On a power-of-two grid this stays
        // empty, because a true Hilbert order is contiguous; on other sizes the order is the
        // enclosing square's curve with out-of-range cells filtered out, which can leave gaps.
        List<Point> deferred = new ArrayList<>();

        for (int i = 1; i < curve.size(); i++) {
            Point p = curve.get(i);
            stats.recordFrontier(curve.size() - i);
            if (!attach(grid, p, visited, rng, stats)) {
                deferred.add(p); // deliberately NOT marked visited — it is not in the tree yet
            }
        }

        // Repair pass. Previously a cell with no visited neighbour was silently skipped and
        // left orphaned, which made this generator emit a *forest*: at 32x32 it produced 953
        // edges for 1024 cells (71 components) and only 66 cells were reachable from (0,0).
        // Every cell borders the grid's 4-connected lattice, so repeating until no progress
        // attaches all of them and restores the spanning-tree contract.
        boolean progress = true;
        while (!deferred.isEmpty() && progress) {
            progress = false;
            Iterator<Point> pending = deferred.iterator();
            while (pending.hasNext()) {
                if (attach(grid, pending.next(), visited, rng, stats)) {
                    pending.remove();
                    progress = true;
                }
            }
        }

        grid.clearVisited();
        stats.finish(deferred.isEmpty());
        return grid;
    }

    /** Carve {@code p} onto a random already-visited neighbour. False if it has none yet. */
    private boolean attach(MazeGrid grid, Point p, Set<Point> visited, Random rng, MazeStats stats) {
        List<Point> candidates = new ArrayList<>();
        for (Point n : grid.neighbors(p)) {
            if (visited.contains(n)) {
                candidates.add(n);
            }
        }
        if (candidates.isEmpty()) {
            return false;
        }
        grid.carve(candidates.get(rng.nextInt(candidates.size())), p);
        grid.cell(p).markVisited();
        visited.add(p);
        stats.incVisited();
        return true;
    }

    /**
     * Cells in true Hilbert order.
     *
     * <p>Walks the curve of the smallest enclosing power-of-two square and keeps the cells that
     * fall inside the grid. On a power-of-two grid the result is the exact Hilbert curve, so
     * consecutive cells are always 4-adjacent; on other sizes filtering can break that adjacency,
     * which the generator's repair pass handles.
     *
     * <p>The previous implementation used a hand-rolled recursive quadrant split whose rotation
     * cases did not compose into a real Hilbert curve — consecutive cells were sometimes not
     * adjacent, which is what orphaned cells and produced a forest.
     */
    private List<Point> hilbertOrder(int height, int width) {
        int side = 1;
        while (side < Math.max(height, width)) {
            side <<= 1;
        }
        List<Point> order = new ArrayList<>(height * width);
        long cells = (long) side * side;
        for (long d = 0; d < cells; d++) {
            int[] xy = curveToPoint(side, d);
            if (xy[1] < height && xy[0] < width) {
                order.add(new Point(xy[1], xy[0])); // Point(row, col)
            }
        }
        return order;
    }

    /**
     * Standard Hilbert {@code d2xy}: map a distance along the curve to its {@code (x, y)} cell,
     * un-rotating each quadrant as it descends. This is the canonical formulation and is what
     * guarantees successive distances land on adjacent cells.
     */
    private static int[] curveToPoint(int side, long distance) {
        int x = 0;
        int y = 0;
        long remaining = distance;
        for (int span = 1; span < side; span <<= 1) {
            int rx = (int) (1 & (remaining / 2));
            int ry = (int) (1 & (remaining ^ rx));
            if (ry == 0) {
                if (rx == 1) {
                    x = span - 1 - x;
                    y = span - 1 - y;
                }
                int swap = x;
                x = y;
                y = swap;
            }
            x += span * rx;
            y += span * ry;
            remaining /= 4;
        }
        return new int[] {x, y};
    }
}
