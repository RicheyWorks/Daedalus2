// SPDX-License-Identifier: MIT

package com.daedalus.solver.solvers;

import com.daedalus.engine.Braider;
import com.daedalus.engine.MazeGenerator;
import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.KruskalsGenerator;
import com.daedalus.engine.generators.PrimsGenerator;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.engine.generators.WilsonsGenerator;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.solver.MazeSolver;
import com.daedalus.theory.MazeMetrics;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Suite-wide property test: every solver, over mazes that contain <b>loops</b>.
 *
 * <h3>Why this exists</h3>
 *
 * <p>Two separate correctness bugs shipped behind a fully green suite in July 2026, and both
 * had the same root cause: <b>every solver fixture in the repository was a perfect maze</b>.
 * A perfect maze is a spanning tree, which makes it a uniquely forgiving test subject —
 * there is exactly one route between any pair of cells, so a solver can be badly wrong and
 * still look right.
 *
 * <ul>
 *   <li>{@code LandmarkHeuristic} was inadmissible on weighted grids, but A* still returned
 *       the optimal path on every fixture, because there was only one path to return.</li>
 *   <li>{@code TremauxSolver} was missing one of Trémaux's three rules and could not solve a
 *       maze with loops at all — it failed on roughly a quarter to a half of braided mazes,
 *       and on none of the perfect ones.</li>
 * </ul>
 *
 * <p>Braiding — {@link Braider} reopens walls to remove dead ends — is what turns a tree into
 * a graph with genuine route choice. It is also the shape the project's topology and
 * load-balancing work actually targets, so it is the case that matters most, and it was the
 * one case nothing covered.
 *
 * <p>The audit that produced this test found no further defects: nine of ten solvers are
 * correct at every braid factor, and the tenth fails exactly where its own javadoc says it
 * will. That is worth pinning, so the next change has to keep it true.
 */
class SolverBraidedMazePropertyTest {

    private static final int SIZE = 16;
    private static final double[] BRAID_FACTORS = {0.0, 0.3, 0.7, 1.0};
    private static final long SEEDS = 5;

    /**
     * Solvers guaranteeing a <em>shortest</em> path. Dead-end filling qualifies because
     * filling only removes cells that cannot lie on any simple route.
     */
    private static final Set<String> OPTIMAL = Set.of(
            "bfs", "dijkstra", "astar", "dial", "bidirectional", "ida-star", "dead-end-filling");

    /**
     * Wall following is provably correct only on <b>simply-connected</b> mazes. Given a loop
     * it can circle an island forever, which is inherent to the method rather than a defect —
     * {@code WallFollowerSolver}'s javadoc and descriptor both say so, and it gives up via an
     * iteration cap instead of hanging. Measured at 20², it failed 5–7 of 24 braided mazes.
     *
     * <p>Its exclusion is scoped to <em>completeness</em> only. It is still held to the
     * legality contract below — returning a wrong path would be a defect, returning none is
     * a documented limitation.
     */
    private static final Set<String> NOT_COMPLETE_ON_LOOPS = Set.of("wall-follower");

    /**
     * Every solver in {@code com.daedalus.solver.solvers}.
     *
     * <p>Kept explicit rather than discovered, because core has no classpath scanner and no
     * {@code ServiceLoader} registration. {@link #everySolverIsCoveredByThisTest()} guards the
     * obvious hazard — a solver added later and silently left out, which is precisely how
     * Trémaux went untested for so long.
     */
    private static List<MazeSolver> solvers() {
        return List.of(new BfsSolver(), new DfsSolver(), new DijkstraSolver(), new AStarSolver(),
                new DialSolver(), new IDAStarSolver(), new BidirectionalSolver(),
                new TremauxSolver(), new WallFollowerSolver(), new DeadEndFillingSolver());
    }

    private static List<MazeGenerator> generators() {
        return List.of(new RecursiveBacktrackerGenerator(), new KruskalsGenerator(),
                new PrimsGenerator(), new WilsonsGenerator());
    }

    private static MazeGrid maze(MazeGenerator gen, long seed, double braid) {
        MazeGrid grid = gen.generate(SIZE, SIZE, seed, new MazeStats());
        if (braid > 0.0) {
            Braider.braid(grid, braid, seed);
        }
        MazeMetrics.placeStartAndGoalAtExtremes(grid);
        return grid;
    }

    /** Start at the start, end at the goal, and never step through a wall. */
    private static String illegality(MazeGrid grid, List<Point> path) {
        if (!path.get(0).equals(grid.start())) {
            return "starts at " + path.get(0) + ", not " + grid.start();
        }
        if (!path.get(path.size() - 1).equals(grid.goal())) {
            return "ends at " + path.get(path.size() - 1) + ", not " + grid.goal();
        }
        for (int i = 1; i < path.size(); i++) {
            if (!grid.openNeighbors(path.get(i - 1)).contains(path.get(i))) {
                return "step " + i + " " + path.get(i - 1) + " -> " + path.get(i) + " crosses a wall";
            }
        }
        return null;
    }

    @Test
    void everySolverIsCoveredByThisTest() {
        // A tripwire, not a proof. If you add a solver, add it to solvers() above and bump
        // this — the point is that leaving it out has to be a deliberate act.
        assertThat(solvers())
                .as("every solver in the package must be exercised by the braid properties")
                .hasSize(10);
        assertThat(solvers()).extracting(MazeSolver::id).doesNotHaveDuplicates();
    }

    @Test
    void everyReturnedPathIsALegalTraversal() {
        // The universal contract — it binds even the solvers allowed to give up, and even
        // those that return a walk rather than a shortest path.
        List<String> violations = new ArrayList<>();
        for (MazeSolver solver : solvers()) {
            for (MazeGenerator gen : generators()) {
                for (long seed = 1; seed <= SEEDS; seed++) {
                    for (double braid : BRAID_FACTORS) {
                        MazeGrid grid = maze(gen, seed, braid);
                        List<Point> path = solver.solve(
                                grid, grid.start(), grid.goal(), new MazeStats());
                        if (path.isEmpty()) {
                            continue; // completeness is asserted separately
                        }
                        String problem = illegality(grid, path);
                        if (problem != null) {
                            violations.add("%s / %s seed=%d braid=%.1f: %s"
                                    .formatted(solver.id(), gen.id(), seed, braid, problem));
                        }
                    }
                }
            }
        }
        assertThat(violations).isEmpty();
    }

    @Test
    void everyCompleteSolverFindsAPathWhereverBfsDoes() {
        // This is the assertion TremauxSolver failed before its missing rule was restored.
        List<String> failures = new ArrayList<>();
        for (MazeSolver solver : solvers()) {
            if (NOT_COMPLETE_ON_LOOPS.contains(solver.id())) {
                continue;
            }
            for (MazeGenerator gen : generators()) {
                for (long seed = 1; seed <= SEEDS; seed++) {
                    for (double braid : BRAID_FACTORS) {
                        MazeGrid grid = maze(gen, seed, braid);
                        List<Point> reference = new BfsSolver()
                                .solve(grid, grid.start(), grid.goal(), new MazeStats());
                        if (reference.isEmpty()) {
                            continue;
                        }
                        List<Point> path = solver.solve(
                                grid, grid.start(), grid.goal(), new MazeStats());
                        if (path.isEmpty()) {
                            failures.add("%s / %s seed=%d braid=%.1f"
                                    .formatted(solver.id(), gen.id(), seed, braid));
                        }
                    }
                }
            }
        }
        assertThat(failures)
                .as("a complete solver must find a route wherever one exists")
                .isEmpty();
    }

    @Test
    void optimalSolversStayOptimalOnceThereIsRouteChoice() {
        // On a perfect maze this assertion is nearly free — one route exists, so any solver
        // that finds a route finds the shortest one. Braiding is what gives it teeth.
        List<String> failures = new ArrayList<>();
        for (MazeSolver solver : solvers()) {
            if (!OPTIMAL.contains(solver.id())) {
                continue;
            }
            for (MazeGenerator gen : generators()) {
                for (long seed = 1; seed <= SEEDS; seed++) {
                    for (double braid : BRAID_FACTORS) {
                        MazeGrid grid = maze(gen, seed, braid);
                        List<Point> reference = new BfsSolver()
                                .solve(grid, grid.start(), grid.goal(), new MazeStats());
                        if (reference.isEmpty()) {
                            continue;
                        }
                        List<Point> path = solver.solve(
                                grid, grid.start(), grid.goal(), new MazeStats());
                        if (path.size() != reference.size()) {
                            failures.add("%s / %s seed=%d braid=%.1f: %d steps vs optimal %d"
                                    .formatted(solver.id(), gen.id(), seed, braid,
                                            path.size(), reference.size()));
                        }
                    }
                }
            }
        }
        assertThat(failures).isEmpty();
    }

    @Test
    void wallFollowerHonoursItsActualGuarantee_perfectMazesOnly() {
        // Pin what it does promise, rather than pinning its limitation — asserting that it
        // *fails* on loops would forbid anyone from later improving it.
        for (MazeGenerator gen : generators()) {
            for (long seed = 1; seed <= SEEDS; seed++) {
                MazeGrid grid = maze(gen, seed, 0.0);
                List<Point> path = new WallFollowerSolver()
                        .solve(grid, grid.start(), grid.goal(), new MazeStats());
                assertThat(path)
                        .as("wall following is complete on simply-connected mazes (%s seed=%d)",
                                gen.id(), seed)
                        .isNotEmpty();
                assertThat(illegality(grid, path)).isNull();
            }
        }
    }
}
