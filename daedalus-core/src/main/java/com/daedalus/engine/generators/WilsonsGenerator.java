// SPDX-License-Identifier: MIT

package com.daedalus.engine.generators;

import com.daedalus.engine.AbstractMazeGenerator;
import com.daedalus.engine.MazeGrid;
import com.daedalus.model.*;

import java.util.*;

/**
 * Wilson's algorithm. Loop-erased random walks from unvisited cells back to the visited tree.
 * Produces a maze drawn uniformly at random from all possible spanning trees of the grid graph
 * — the gold standard for "unbiased."
 *
 * <p>Slow start (many wandering walks) but the result has no statistical bias.
 * Complexity: expected O(n) on the grid graph but with a large constant.
 */
public class WilsonsGenerator extends AbstractMazeGenerator {

    @Override public String id() { return "wilsons"; }
    @Override public String displayName() { return "Wilson's"; }

    @Override
    public AlgorithmDescriptor descriptor() {
        return new AlgorithmDescriptor(
                id(), displayName(), "generator",
                "Expected O(n), large constant",
                "Uniformly random spanning tree — provably unbiased",
                "Loop-erased random walks. Slow but mathematically pristine.");
    }

    @Override
    public MazeGrid generate(int rows, int cols, long seed, MazeStats stats) {
        Random rng = new Random(seed);
        MazeGrid grid = new MazeGrid(rows, cols);
        Set<Point> inMaze = new HashSet<>();

        Point seed0 = new Point(rng.nextInt(rows), rng.nextInt(cols));
        inMaze.add(seed0);
        grid.cell(seed0).markVisited();

        List<Point> all = new ArrayList<>(rows * cols);
        for (int r = 0; r < rows; r++) for (int c = 0; c < cols; c++) all.add(new Point(r, c));
        Collections.shuffle(all, rng);

        for (Point start : all) {
            if (inMaze.contains(start)) continue;
            List<Point> walk = new ArrayList<>();
            walk.add(start);
            Map<Point, Integer> indexInWalk = new HashMap<>();
            indexInWalk.put(start, 0);

            Point cur = start;
            while (!inMaze.contains(cur)) {
                List<Point> nbrs = grid.neighbors(cur);
                Point next = nbrs.get(rng.nextInt(nbrs.size()));
                Integer prior = indexInWalk.get(next);
                if (prior != null) {
                    // Loop erasure: trim walk back to prior occurrence.
                    while (walk.size() > prior + 1) {
                        Point removed = walk.remove(walk.size() - 1);
                        indexInWalk.remove(removed);
                    }
                } else {
                    indexInWalk.put(next, walk.size());
                    walk.add(next);
                }
                cur = next;
                stats.incExplored(); // one random-walk step — this is what cover time counts
                stats.recordFrontier(walk.size());
            }

            for (int i = 0; i < walk.size() - 1; i++) {
                grid.carve(walk.get(i), walk.get(i + 1));
                inMaze.add(walk.get(i));
                grid.cell(walk.get(i)).markVisited();
                stats.incVisited();
            }
            inMaze.add(walk.get(walk.size() - 1));
        }

        grid.clearVisited();
        stats.finish(true);
        return grid;
    }
}
