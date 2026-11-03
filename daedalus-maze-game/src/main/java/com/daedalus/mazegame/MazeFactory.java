// SPDX-License-Identifier: MIT

package com.daedalus.mazegame;

import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.EllersGenerator;
import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.engine.generators.PrimsGenerator;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.engine.generators.WilsonsGenerator;
import com.daedalus.model.Direction;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.solver.solvers.AStarSolver;
import com.daedalus.solver.solvers.BfsSolver;
import com.daedalus.solver.solvers.SolverRegistry;
import com.daedalus.solver.solvers.TremauxSolver;

import java.util.List;

/**
 * Builds Labyrinth Run mazes through the core registries (no forked generators). The entrance is
 * the top-left cell and the exit the bottom-right cell, matching the Daedalus realm convention.
 */
public final class MazeFactory {

    private final GeneratorRegistry generators;
    private final SolverRegistry solvers;

    public MazeFactory() {
        this(new GeneratorRegistry(List.of(new RecursiveBacktrackerGenerator(), new PrimsGenerator(),
                        new WilsonsGenerator(), new EllersGenerator())),
                new SolverRegistry(List.of(new BfsSolver(), new AStarSolver(), new TremauxSolver())));
    }

    /** Uses caller-supplied registries, e.g. the host's full built-in set. */
    public MazeFactory(GeneratorRegistry generators, SolverRegistry solvers) {
        this.generators = generators;
        this.solvers = solvers;
    }

    /** Engine seed for a game seed: SplitMix64 finaliser over seed and tier, so tiers never share a maze. */
    public static long engineSeed(long seed, Difficulty difficulty) {
        long z = seed + 0x9E3779B97F4A7C15L * (difficulty.ordinal() + 1L);
        z = (z ^ (z >>> 30)) * 0xBF58476D1CE4E5B9L;
        z = (z ^ (z >>> 27)) * 0x94D049BB133111EBL;
        return z ^ (z >>> 31);
    }

    public MazeGrid build(long seed, Difficulty difficulty) {
        int n = difficulty.size();
        MazeGrid grid = generators.require(difficulty.generatorId()).generate(n, n, engineSeed(seed, difficulty));
        grid.setStart(new Point(0, 0));
        grid.setGoal(new Point(n - 1, n - 1));
        return grid;
    }

    /** Shortest path (inclusive of both ends) from the named solver; BFS gives par. */
    public List<Point> solve(MazeGrid grid, Point from, String solverId) {
        return solvers.require(solverId).solve(grid, from, grid.goal(), new MazeStats());
    }

    /** Par in moves: optimal BFS path length minus one. */
    public int par(MazeGrid grid) {
        return solve(grid, grid.start(), "bfs").size() - 1;
    }

    /** FNV-1a over every cell's east and south openings; a stable fingerprint for golden fixtures. */
    public static String hash(MazeGrid grid) {
        long h = 0xcbf29ce484222325L;
        for (int r = 0; r < grid.rows(); r++) {
            for (int c = 0; c < grid.cols(); c++) {
                int bits = (grid.isOpen(r, c, Direction.EAST) ? 1 : 0)
                        | (grid.isOpen(r, c, Direction.SOUTH) ? 2 : 0);
                h ^= bits;
                h *= 0x100000001b3L;
            }
        }
        return String.format("%016x", h);
    }
}
