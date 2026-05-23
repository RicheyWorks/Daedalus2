// SPDX-License-Identifier: MIT

package com.daedalus.engine.generators;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.Direction;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Random;

/**
 * Shared loop body for every member of the Growing-Tree family
 * ({@link GrowingTreeGenerator}, {@link LightningGenerator}, {@link GaussGenerator},
 * {@link TuringGenerator}). Used to be replicated four times with only the cell-selection
 * rule differing — extracted so the rule lives in a single-method
 * {@link GrowingTreePolicy} and the surrounding bookkeeping (frontier counts, backtrack
 * accounting, visited reset, perfect-maze guarantee) lives in exactly one place.
 *
 * <p>The neighbor enumeration here uses the slow path
 * (<em>shuffle 4 directions, then iterate and bounds-check</em>) intentionally — that
 * matches what {@code GrowingTreeGenerator}, {@code GaussGenerator}, and
 * {@code TuringGenerator} did before this refactor, so seed-pinned mazes are bit-for-bit
 * identical. The previous {@code LightningGenerator} used a faster array-based shuffle
 * that filtered out-of-bounds neighbors before shuffling — that consumed the {@link Random}
 * differently and would have changed Lightning's output for the same seed. We preferred
 * unification + reproducibility here over Lightning's marginal allocation savings; the
 * dominant cost is the visited-bitset check, not the direction array.
 *
 * <p>Package-private — only the Growing-Tree generators in this package should reach in.
 */
final class GrowingTreeEngine {

    private GrowingTreeEngine() {}

    /**
     * Run the Growing-Tree loop until the active list drains. Always produces a perfect
     * maze on a {@code rows × cols} grid: every cell visited exactly once, exactly
     * {@code rows*cols - 1} edges carved, no cycles.
     *
     * @param rows    grid rows
     * @param cols    grid cols
     * @param seed    RNG seed — same seed + same policy → same maze, bit-for-bit
     * @param stats   collector for frontier / visited / backtrack metrics
     * @param policy  cell-selection rule; consulted on every iteration
     */
    static MazeGrid run(int rows, int cols, long seed, MazeStats stats, GrowingTreePolicy policy) {
        Random rng = new Random(seed);
        MazeGrid grid = new MazeGrid(rows, cols);

        List<Point> active = new ArrayList<>();
        Point first = new Point(rng.nextInt(rows), rng.nextInt(cols));
        active.add(first);
        grid.cell(first).markVisited();
        stats.incVisited();

        while (!active.isEmpty()) {
            stats.recordFrontier(active.size());

            int idx = policy.pickNext(active, rng);
            Point cur = active.get(idx);

            // Slow-path neighbor enumeration: shuffle all four directions, then iterate
            // and check in-bounds + unvisited per step. Preserves seed → maze mapping
            // for every existing Growing-Tree generator (see class Javadoc).
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
