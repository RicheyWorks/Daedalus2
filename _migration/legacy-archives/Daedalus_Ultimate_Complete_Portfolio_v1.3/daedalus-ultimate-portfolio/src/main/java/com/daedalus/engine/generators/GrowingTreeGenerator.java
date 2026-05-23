package com.daedalus.engine.generators;

import com.daedalus.engine.AbstractMazeGenerator;
import com.daedalus.engine.MazeGrid;
import com.daedalus.model.*;

import java.util.*;

/**
 * Growing Tree. The "meta-algorithm" — picks a cell from an active list and carves to
 * a random unvisited neighbor. Different cell-selection policies recover different
 * algorithms:
 *
 * <ul>
 *   <li>Always pick newest → Recursive Backtracker</li>
 *   <li>Always pick random → Prim's-ish</li>
 *   <li>Mix → custom textures</li>
 * </ul>
 *
 * <p>This implementation uses 50/50 newest/random for a textured middle ground.
 */
public class GrowingTreeGenerator extends AbstractMazeGenerator {

    @Override public String id() { return "growing-tree"; }
    @Override public String displayName() { return "Growing Tree (mixed)"; }

    @Override
    public AlgorithmDescriptor descriptor() {
        return new AlgorithmDescriptor(
                id(), displayName(), "generator",
                "O(n) time, O(n) space",
                "Tunable bias; default 50/50 newest/random gives mixed texture",
                "Generalization of Prim's and DFS via cell-selection policy.");
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
            int idx = rng.nextBoolean()
                    ? active.size() - 1                    // newest
                    : rng.nextInt(active.size());          // random
            Point cur = active.get(idx);

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
