package com.daedalus.engine;

import com.daedalus.model.Direction;
import com.daedalus.model.Point;
import java.util.Arrays;
import java.util.List;
import java.util.Random;

/** OPTIMIZED scaffolding — fewer allocations in hot paths. */
public abstract class AbstractMazeGenerator implements MazeGenerator {

    /** Fast neighbor array (no List allocation in performance-critical loops). */
    protected Point[] getNeighbors(MazeGrid grid, Point p, Random rng) {
        Point[] nbrs = new Point[4];
        int idx = 0;
        for (Direction d : Direction.values()) {
            Point n = p.step(d);
            if (grid.inBounds(n)) nbrs[idx++] = n;
        }
        // Fisher-Yates shuffle on the active slice
        for (int i = idx - 1; i > 0; i--) {
            int j = rng.nextInt(i + 1);
            Point tmp = nbrs[i]; nbrs[i] = nbrs[j]; nbrs[j] = tmp;
        }
        return Arrays.copyOf(nbrs, idx);
    }

    /** Original list-based version — kept for 100% backwards compatibility. */
    protected List<Point> shuffledNeighbors(MazeGrid grid, Point p, Random rng) {
        List<Point> out = new java.util.ArrayList<>(4);
        for (Direction d : Direction.values()) {
            Point n = p.step(d);
            if (grid.inBounds(n)) out.add(n);
        }
        java.util.Collections.shuffle(out, rng);
        return out;
    }

    protected Point randomCell(MazeGrid grid, Random rng) {
        return new Point(rng.nextInt(grid.rows()), rng.nextInt(grid.cols()));
    }
}
