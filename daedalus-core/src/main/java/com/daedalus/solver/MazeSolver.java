// SPDX-License-Identifier: MIT

package com.daedalus.solver;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.AlgorithmDescriptor;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;

import java.util.List;

/**
 * SPI for any maze-solving algorithm.
 *
 * <p>Solvers consume the cell-graph view (via {@code MazeGrid#openNeighbors})
 * and return a path from {@code start} to {@code goal} (inclusive). Empty list ⇒ no path.
 *
 * <p>Implementations should populate {@link MazeStats} as they explore — this is what
 * powers {@code theory.ComplexityAnalyzer} and the live solver visualizer.
 */
public interface MazeSolver {

    String id();
    String displayName();
    AlgorithmDescriptor descriptor();

    /**
     * @return the path from {@code start} to {@code goal}, inclusive of both endpoints.
     *         Empty list if unreachable.
     */
    List<Point> solve(MazeGrid grid, Point start, Point goal, MazeStats stats);

    default List<Point> solve(MazeGrid grid) {
        return solve(grid, grid.start(), grid.goal(), new MazeStats());
    }
}
