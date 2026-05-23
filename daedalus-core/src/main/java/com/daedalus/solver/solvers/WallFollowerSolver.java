// SPDX-License-Identifier: MIT

package com.daedalus.solver.solvers;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.AlgorithmDescriptor;
import com.daedalus.model.Cell;
import com.daedalus.model.Direction;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.solver.AbstractMazeSolver;

import java.util.*;

/**
 * Right-hand wall follower.
 *
 * <p>Maintain a heading direction. At every cell, prefer to turn right relative to
 * heading; if blocked, go straight; if blocked, turn left; if blocked, reverse.
 * Always returns a valid path on perfect (simply-connected) mazes — but typically a
 * non-shortest one, since the algorithm hugs the right wall around dead-end branches.
 *
 * <p>Will fail (loop forever) on mazes with disconnected wall components, e.g. a goal
 * inside a closed island. We cap iterations at {@code 4 * rows * cols} to avoid that.
 *
 * <p>Memory is O(1) — no parent map, no visited set needed for the algorithm itself.
 * (Visited tracking here is purely for stats reporting.)
 */
public class WallFollowerSolver extends AbstractMazeSolver {

    @Override public String id() { return "wall-follower"; }
    @Override public String displayName() { return "Wall Follower (right-hand rule)"; }

    @Override
    public AlgorithmDescriptor descriptor() {
        return new AlgorithmDescriptor(
                id(), displayName(), "solver",
                "O(V + E) time, O(1) memory — no maps or queues required",
                "Suboptimal — hugs the wall through every dead-end branch",
                "Always turn right when possible. Works on perfect mazes; may loop on imperfect ones.");
    }

    @Override
    public List<Point> solve(MazeGrid grid, Point start, Point goal, MazeStats stats) {
        List<Point> path = new ArrayList<>();
        Set<Point> visited = new HashSet<>();

        Point pos = start;
        Direction heading = chooseInitialHeading(grid, start);
        path.add(pos);
        visited.add(pos);
        stats.incVisited();

        int maxSteps = 4 * grid.rows() * grid.cols();
        for (int step = 0; step < maxSteps; step++) {
            stats.incExplored();
            stats.recordFrontier(path.size());

            if (pos.equals(goal)) {
                stats.setPathLength(path.size());
                stats.finish(true);
                return path;
            }

            Cell cell = grid.cell(pos);
            // Right-hand priority: right of heading > heading > left of heading > reverse.
            Direction[] order = {right(heading), heading, left(heading), heading.opposite()};
            Direction chosen = null;
            for (Direction d : order) {
                if (cell.isOpen(d)) { chosen = d; break; }
            }
            if (chosen == null) {
                // Boxed in — no exits. Shouldn't happen on a connected maze.
                stats.finish(false);
                return Collections.emptyList();
            }

            pos = pos.step(chosen);
            heading = chosen;
            path.add(pos);
            if (visited.add(pos)) stats.incVisited();
        }

        // Safety cap exceeded — likely a disconnected goal.
        stats.finish(false);
        return Collections.emptyList();
    }

    /** Pick a starting heading that has an open passage if possible. */
    private Direction chooseInitialHeading(MazeGrid grid, Point start) {
        Cell c = grid.cell(start);
        for (Direction d : Direction.values()) {
            if (c.isOpen(d)) return d;
        }
        return Direction.NORTH; // start is isolated; doesn't matter
    }

    private static Direction right(Direction d) {
        return switch (d) {
            case NORTH -> Direction.EAST;
            case EAST  -> Direction.SOUTH;
            case SOUTH -> Direction.WEST;
            case WEST  -> Direction.NORTH;
        };
    }

    private static Direction left(Direction d) {
        return switch (d) {
            case NORTH -> Direction.WEST;
            case WEST  -> Direction.SOUTH;
            case SOUTH -> Direction.EAST;
            case EAST  -> Direction.NORTH;
        };
    }
}
