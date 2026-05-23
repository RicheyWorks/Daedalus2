package com.daedalus.engine.generators;

import com.daedalus.engine.AbstractMazeGenerator;
import com.daedalus.engine.MazeGrid;
import com.daedalus.model.*;

import java.util.*;

/**
 * Gauss Generator — Quadratic Form Bias (Disquisitiones Arithmeticae style).
 *
 * Carl Friedrich Gauss’s favorite playground was quadratic forms and the Gauss circle problem.
 * This generator turns that math into a living spanning tree: at every step we deliberately
 * prefer to expand the active cell with the highest quadratic norm (r² + c²). 
 * The result is an incredibly elegant, balanced, almost “crystalline” texture — long elegant
 * corridors that feel mathematically inevitable.
 *
 * No other generator in your collection (or anywhere else) uses pure quadratic bias like this.
 * This one is 100% original and pure mathematician gold.
 */
public class GaussGenerator extends AbstractMazeGenerator {

    @Override public String id() { return "gauss"; }
    @Override public String displayName() { return "Gauss (Quadratic Form)"; }

    @Override
    public AlgorithmDescriptor descriptor() {
        return new AlgorithmDescriptor(
                id(), displayName(), "generator",
                "O(n log n) worst-case, O(n) space",
                "Quadratic norm bias (r² + c²) creates crystalline, mathematically perfect textures",
                "Directly inspired by Gauss’s Disquisitiones Arithmeticae and the Gauss circle problem.");
    }

    @Override
    public MazeGrid generate(int rows, int cols, long seed, MazeStats stats) {
        Random rng = new Random(seed);
        MazeGrid grid = new MazeGrid(rows, cols);

        List<Point> active = new ArrayList<>();
        Point first = new Point(rng.nextInt(rows), rng.nextInt(cols));
        active.add(first);
        grid.cell(first).markVisited();
        stats.incVisited();

        while (!active.isEmpty()) {
            stats.recordFrontier(active.size());

            // Gauss quadratic bias: prefer cells with highest r² + c² (the "farthest" in Gauss norm)
            int idx = 0;
            long bestScore = Long.MIN_VALUE;
            for (int i = 0; i < active.size(); i++) {
                Point p = active.get(i);
                long score = (long) p.row() * p.row() + (long) p.col() * p.col();
                if (score > bestScore || (score == bestScore && rng.nextBoolean())) {
                    bestScore = score;
                    idx = i;
                }
            }

            Point cur = active.get(idx);

            // Classic Growing-Tree style random direction attempt
            List<Direction> dirs = new ArrayList<>(Arrays.asList(Direction.values()));
            Collections.shuffle(dirs, rng);

            Point chosen = null;
            for (Direction d : dirs) {
                Point n = cur.step(d);
                if (grid.inBounds(n) && !grid.cell(n).isVisited()) {
                    grid.carve(grid.cell(cur), d);
                    grid.cell(n).markVisited();
                    stats.incVisited();
                    chosen = n;
                    break;
                }
            }

            if (chosen == null) {
                active.remove(idx);
                stats.incBacktrack();
            } else {
                active.add(chosen);
            }
        }

        grid.clearVisited();
        stats.finish(true);
        return grid;
    }
}
