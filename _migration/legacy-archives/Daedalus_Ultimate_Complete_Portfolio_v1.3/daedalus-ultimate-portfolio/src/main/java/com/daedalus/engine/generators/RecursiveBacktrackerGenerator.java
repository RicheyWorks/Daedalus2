package com.daedalus.engine.generators;

import com.daedalus.engine.AbstractMazeGenerator;
import com.daedalus.engine.MazeGrid;
import com.daedalus.model.AlgorithmDescriptor;
import com.daedalus.model.Cell;
import com.daedalus.model.Direction;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;

import java.util.ArrayDeque;
import java.util.Deque;
import java.util.Random;

/**
 * Recursive Backtracker (iterative DFS). Classic "depth-first carving."
 *
 * <p>Bias: long, winding corridors with relatively few branches and few short dead ends.
 * Tends toward "river" mazes. Produces a perfect maze.
 *
 * <p>Complexity: O(n) time / O(n) stack.
 */
public class RecursiveBacktrackerGenerator extends AbstractMazeGenerator {

    @Override public String id() { return "recursive-backtracker"; }
    @Override public String displayName() { return "Recursive Backtracker"; }

    @Override
    public AlgorithmDescriptor descriptor() {
        return new AlgorithmDescriptor(
                id(), displayName(), "generator",
                "O(n) time, O(n) stack",
                "Long winding corridors; high 'river' factor",
                "Iterative DFS that carves until blocked, then backtracks. The textbook starter algorithm.");
    }

    @Override
    public MazeGrid generate(int rows, int cols, long seed, MazeStats stats) {
        Random rng = new Random(seed);
        MazeGrid grid = new MazeGrid(rows, cols);

        Deque<Cell> stack = new ArrayDeque<>();
        Cell start = grid.cell(rng.nextInt(rows), rng.nextInt(cols));
        start.markVisited();
        stack.push(start);
        stats.incVisited();

        while (!stack.isEmpty()) {
            Cell current = stack.peek();
            stats.recordFrontier(stack.size());

            // Pick a random unvisited neighbor.
            Direction dir = pickUnvisited(grid, current, rng);
            if (dir == null) {
                stack.pop();
                stats.incBacktrack();
                continue;
            }

            grid.carve(current, dir);
            Cell next = grid.cell(current.position().step(dir));
            next.markVisited();
            stack.push(next);
            stats.incVisited();
        }

        grid.clearVisited();
        stats.finish(true);
        return grid;
    }

    private Direction pickUnvisited(MazeGrid grid, Cell from, Random rng) {
        Direction[] dirs = Direction.values().clone();
        // Fisher–Yates
        for (int i = dirs.length - 1; i > 0; i--) {
            int j = rng.nextInt(i + 1);
            Direction t = dirs[i]; dirs[i] = dirs[j]; dirs[j] = t;
        }
        for (Direction d : dirs) {
            Point np = from.position().step(d);
            if (grid.inBounds(np) && !grid.cell(np).isVisited()) return d;
        }
        return null;
    }
}
