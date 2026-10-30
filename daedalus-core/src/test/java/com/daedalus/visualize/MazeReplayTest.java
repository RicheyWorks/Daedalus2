// SPDX-License-Identifier: MIT

package com.daedalus.visualize;

import com.daedalus.engine.Braider;
import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.solver.MazeSolver;
import com.daedalus.solver.solvers.AStarSolver;
import com.daedalus.solver.solvers.BfsSolver;
import com.daedalus.solver.solvers.BidirectionalSolver;
import com.daedalus.solver.solvers.DeadEndFillingSolver;
import com.daedalus.solver.solvers.DfsSolver;
import com.daedalus.solver.solvers.DialSolver;
import com.daedalus.solver.solvers.DijkstraSolver;
import com.daedalus.solver.solvers.IDAStarSolver;
import com.daedalus.solver.solvers.TremauxSolver;
import com.daedalus.solver.solvers.WallFollowerSolver;
import com.daedalus.theory.MazeMetrics;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.MethodSource;

import java.util.List;
import java.util.stream.Stream;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Replay is observation, not simulation — the properties pinned here are exactly the ones the
 * animation depends on being honest.
 *
 * <p>Braided fixture, per the house rule: perfect mazes are too forgiving to prove anything
 * about search order.
 */
class MazeReplayTest {

    private static MazeGrid maze() {
        MazeGrid grid = new RecursiveBacktrackerGenerator().generate(12, 12, 5L, new MazeStats());
        Braider.braid(grid, 0.4, 5L);
        MazeMetrics.placeStartAndGoalAtExtremes(grid);
        return grid;
    }

    static Stream<MazeSolver> seamSolvers() {
        return Stream.of(new BfsSolver(), new DfsSolver(), new DijkstraSolver(),
                new AStarSolver(), new DialSolver(), new BidirectionalSolver(),
                new TremauxSolver(), new DeadEndFillingSolver());
    }

    @ParameterizedTest(name = "{0}")
    @MethodSource("seamSolvers")
    void recordsARealExpansionSequenceForEverySeamSolver(MazeSolver solver) {
        MazeGrid grid = maze();
        MazeReplay.Replay replay =
                MazeReplay.record(solver, grid, grid.start(), grid.goal(), new MazeStats());

        assertThat(replay.path()).as("the solve itself must still succeed").isNotEmpty();
        assertThat(replay.expansions()).as("seam solvers must record expansions").isNotEmpty();
        assertThat(replay.expansions())
                .as("every expansion is a real cell")
                .allSatisfy(p -> assertThat(grid.inBounds(p)).isTrue());
        // Where a search BEGINS is algorithm-specific — frontier searches start at an
        // endpoint, but dead-end filling legitimately opens by scanning dead ends anywhere
        // in the grid. The honest cross-solver invariant is that the recorded sequence
        // touches the route it returned: the search cannot have found a path along cells
        // it never looked at.
        assertThat(replay.expansions())
                .as("the expansion sequence must touch the returned route")
                .containsAnyElementsOf(replay.path());
    }

    @Test
    void replayedPathIsIdenticalToAnUnobservedSolve() {
        MazeGrid grid = maze();
        List<Point> plain = new BfsSolver().solve(grid, grid.start(), grid.goal(), new MazeStats());
        MazeReplay.Replay replay = MazeReplay.record(
                new BfsSolver(), grid, grid.start(), grid.goal(), new MazeStats());
        assertThat(replay.path())
                .as("observation must not change the algorithm's behavior")
                .isEqualTo(plain);
    }

    @Test
    void bfsExpandsEachNodeAtMostOnceAndInFloodOrder() {
        MazeGrid grid = maze();
        MazeReplay.Replay replay = MazeReplay.record(
                new BfsSolver(), grid, grid.start(), grid.goal(), new MazeStats());
        assertThat(replay.expansions()).doesNotHaveDuplicates();
        assertThat(replay.expansions().get(0)).isEqualTo(grid.start());
    }

    @Test
    void offSeamSolversReturnAnEmptyReplayNotAFakeOne() {
        // IDA* and wall-follower are deliberately off the graph seam (ADR-001 item 3);
        // pretending to replay them would be simulation, which this feature refuses to do.
        MazeGrid grid = maze();
        for (MazeSolver solver : List.of(new IDAStarSolver(), new WallFollowerSolver())) {
            MazeReplay.Replay replay =
                    MazeReplay.record(solver, grid, grid.start(), grid.goal(), new MazeStats());
            assertThat(replay.expansions()).as(solver.id()).isEmpty();
        }
    }

    @Test
    void recordingIsScopedToTheCall() {
        // A solve after record() must not leak expansions into a dead recorder — and a
        // recorder must not see a neighbouring thread's solve. The scoping is the thread-local
        // contract SearchRecorder documents; this pins the "cleared afterwards" half.
        MazeGrid grid = maze();
        MazeReplay.record(new BfsSolver(), grid, grid.start(), grid.goal(), new MazeStats());
        // If end() failed to clear, this solve would throw or pollute nothing observable —
        // so assert via a second recording being exactly a fresh sequence.
        MazeReplay.Replay second = MazeReplay.record(
                new BfsSolver(), grid, grid.start(), grid.goal(), new MazeStats());
        MazeReplay.Replay third = MazeReplay.record(
                new BfsSolver(), grid, grid.start(), grid.goal(), new MazeStats());
        assertThat(second.expansions()).isEqualTo(third.expansions());
    }
}
