// SPDX-License-Identifier: MIT

package com.daedalus.engine.generators;

import com.daedalus.engine.AbstractMazeGenerator;
import com.daedalus.engine.MazeGrid;
import com.daedalus.model.AlgorithmDescriptor;
import com.daedalus.model.MazeStats;

/**
 * Recursive Backtracker (iterative DFS). Classic "depth-first carving."
 *
 * <p>Implemented as a thin wrapper over {@link GrowingTreeEngine} with
 * {@link GrowingTreePolicies#newest()} — picking the newest cell on every iteration
 * recovers exactly the DFS-with-explicit-stack behavior the textbook RB algorithm has.
 * Folding RB onto the shared engine consolidates the last newest-pick variant of the
 * Growing-Tree family (alongside {@link GrowingTreeGenerator},
 * {@link OldestPickGenerator}, {@link GaussGenerator}, {@link LightningGenerator}, and
 * {@link TuringGenerator}) and means the spanning-tree contract, frontier accounting,
 * and backtrack metrics all live in one place.
 *
 * <p><b>Seed mapping: preserved.</b> The pre-2026-05-11 implementation maintained its
 * own stack-of-cells loop with a Fisher–Yates shuffle of {@code Direction.values()} per
 * cell and an in-order scan to pick the first unvisited neighbour. The engine's
 * slow-path enumeration uses {@code Collections.shuffle} on a {@code List<Direction>},
 * which for a size-4 list goes through the fast path and emits the same Fisher–Yates
 * sequence ({@code nextInt(4), nextInt(3), nextInt(2)}). The {@link
 * com.daedalus.model.Direction} enum order is unchanged ({@code NORTH, SOUTH, EAST,
 * WEST}); the starting cell uses the same {@code nextInt(rows), nextInt(cols)} pair
 * before the loop. The {@link GrowingTreePolicies#newest()} policy consumes zero random
 * bits per call. Therefore the random-bit consumption is identical end-to-end and the
 * {@code seed → maze} mapping for id {@code "recursive-backtracker"} is preserved
 * across the refactor — any client that had pinned RB seeds before 2026-05-11 will
 * resolve to the same maze afterwards. The equivalence is locked by {@code
 * RecursiveBacktrackerEngineEquivalenceTest}, which fails any time RB diverges from a
 * direct {@code GrowingTreeEngine.run(..., newest())} invocation.
 *
 * <p>Bias: long, winding corridors with relatively few branches and few short dead
 * ends. Tends toward "river" mazes. Produces a perfect maze.
 *
 * <p>Complexity: O(n) time / O(n) auxiliary (the engine's active list, which for the
 * newest-pick policy mirrors a DFS stack).
 */
public class RecursiveBacktrackerGenerator extends AbstractMazeGenerator {

    @Override public String id()          { return "recursive-backtracker"; }
    @Override public String displayName() { return "Recursive Backtracker"; }

    @Override
    public AlgorithmDescriptor descriptor() {
        return new AlgorithmDescriptor(
                id(), displayName(), "generator",
                "O(n) time, O(n) auxiliary",
                "Long winding corridors; high 'river' factor",
                "Iterative DFS that carves until blocked, then backtracks. " +
                "Implemented as GrowingTreeEngine.run(..., newest()).");
    }

    @Override
    public MazeGrid generate(int rows, int cols, long seed, MazeStats stats) {
        return GrowingTreeEngine.run(rows, cols, seed, stats, GrowingTreePolicies.newest());
    }
}
