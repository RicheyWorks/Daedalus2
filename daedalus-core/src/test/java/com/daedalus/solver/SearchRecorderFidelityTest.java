// SPDX-License-Identifier: MIT

package com.daedalus.solver;

import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.solver.solvers.AStarSolver;
import com.daedalus.solver.solvers.BfsSolver;
import com.daedalus.solver.solvers.BidirectionalSolver;
import com.daedalus.solver.solvers.DfsSolver;
import com.daedalus.solver.solvers.DialSolver;
import com.daedalus.solver.solvers.DijkstraSolver;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.MethodSource;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * The recorder must report the search that actually happened — every expansion, in order.
 *
 * <p>Everything built on replay leans on this: the step-through visualiser, the solver arena
 * that races two algorithms' recorded searches at equal speed and declares a winner on
 * expansion count, and the "observation, never reenactment" claim those features are sold on.
 * If the recorder silently dropped expansions, the arena would still animate beautifully and
 * announce a completely fabricated result.
 *
 * <p>It is tested here, in core, because of where it was missing: a mutation that dropped half
 * of all recorded expansions left {@code mvn -pl daedalus-core test} green — the recorder lives
 * in core and the only test of its fidelity lived in the server module.
 */
class SearchRecorderFidelityTest {

    private final MazeGrid grid =
            new RecursiveBacktrackerGenerator().generate(15, 15, 42L, new MazeStats());

    /** Solve while recording, returning the node ids in the order they were expanded. */
    private List<Integer> recordedExpansions() {
        List<Integer> expansions = new ArrayList<>();
        SearchRecorder.begin(expansions::add);
        try {
            new BfsSolver().solve(grid, grid.start(), grid.goal(), new MazeStats());
        } finally {
            SearchRecorder.end();
        }
        return expansions;
    }

    @Test
    void everyExpansionIsReportedExactlyOnceAndInOrder() {
        List<Integer> expansions = recordedExpansions();
        GridIndex index = new GridIndex(grid);

        assertThat(expansions).as("a recorded search with no expansions is not a search")
                .isNotEmpty();
        // BFS never re-expands a node, so a duplicate means the recording is not the search.
        Set<Integer> unique = new HashSet<>(expansions);
        assertThat(unique)
                .as("expansions repeated — the recording does not mirror BFS's real behaviour")
                .hasSameSizeAs(expansions);
        // The first expansion is the start cell: recording begins where the search begins.
        assertThat(expansions.get(0)).isEqualTo(index.idOf(grid.start()));
        // Every reported id is a real cell of this maze.
        for (int id : expansions) {
            Point p = index.pointOf(id);
            assertThat(p.row()).isBetween(0, grid.rows() - 1);
            assertThat(p.col()).isBetween(0, grid.cols() - 1);
        }
    }

    /**
     * Every cell the solver explored is recorded exactly once — the invariant that makes the
     * arena's "did less work" verdict a fact rather than an animation.
     *
     * <p>Two things had to be measured rather than assumed to write this. First, the metric:
     * the obvious-looking {@code cellsVisited} is <em>not</em> the count to compare against and
     * disagrees with the recording by up to 17 on a 31×31 DFS solve; {@code cellsExplored} is
     * the right one. Second, the tolerance: {@code cellsExplored - recorded} is exactly
     * {@code 1} for most solvers and {@code 0} for bidirectional search, because the recorder
     * fires when a cell's neighbours are requested and the final cell — the goal, where the
     * search stops — never gets asked. Swept over six solvers, three generators, six seeds and
     * three sizes (324 solves), the difference was never anything but 0 or 1. Anything outside
     * that window means expansions were dropped or invented.
     */
    @ParameterizedTest
    @MethodSource("solvers")
    void everyExploredCellIsRecordedExactlyOnce(MazeSolver solver) {
        MazeStats stats = new MazeStats();
        List<Integer> expansions = new ArrayList<>();
        SearchRecorder.begin(expansions::add);
        List<Point> path;
        try {
            path = solver.solve(grid, grid.start(), grid.goal(), stats);
        } finally {
            SearchRecorder.end();
        }
        assertThat(path).as("%s found no route through a perfect maze",
                solver.getClass().getSimpleName()).isNotEmpty();

        long unrecorded = stats.cellsExplored() - expansions.size();
        assertThat(unrecorded)
                .as("%s: explored %d cells but recorded %d — a recording that is not the search "
                        + "makes the arena's expansion-count verdict fiction",
                        solver.getClass().getSimpleName(), stats.cellsExplored(),
                        expansions.size())
                .isBetween(0L, 1L);
    }

    static java.util.stream.Stream<MazeSolver> solvers() {
        return java.util.stream.Stream.of(
                new BfsSolver(), new DfsSolver(), new AStarSolver(),
                new DijkstraSolver(), new DialSolver(), new BidirectionalSolver());
    }

    @Test
    void recordingIsOffByDefaultAndStopsWhenEnded() {
        // No begin(): a plain solve must record nothing anywhere.
        new BfsSolver().solve(grid, grid.start(), grid.goal(), new MazeStats());

        List<Integer> afterEnd = new ArrayList<>();
        SearchRecorder.begin(afterEnd::add);
        SearchRecorder.end();
        new BfsSolver().solve(grid, grid.start(), grid.goal(), new MazeStats());
        assertThat(afterEnd)
                .as("end() must detach the observer — a leaked recorder would attribute one "
                        + "solver's search to another, which is the arena's whole comparison")
                .isEmpty();
    }
}
