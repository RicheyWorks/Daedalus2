// SPDX-License-Identifier: MIT

package com.daedalus.engine;

import com.daedalus.engine.Sealer.SealResult;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.Point;
import com.daedalus.solver.solvers.BfsSolver;
import com.daedalus.model.MazeStats;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * {@link Sealer} is the connectivity proof ADR-006 asked for before living mazes could
 * get harder. The claims: a tree has nothing to close; extras come off without splitting
 * the habitable graph; a batch of closures is safe (the spanning-forest complement, not
 * "every current non-bridge"); the pass is deterministic under a seed.
 */
class SealerTest {

    private static MazeGrid perfectMaze(int size, long seed) {
        return new RecursiveBacktrackerGenerator().generate(size, size, seed);
    }

    @Test
    void aPerfectMazeHasNothingToClose() {
        MazeGrid grid = perfectMaze(12, 42L);
        List<String> before = signature(grid);

        SealResult result = Sealer.seal(grid, 1.0, 7L);

        assertThat(result.closableBefore()).isZero();
        assertThat(result.wallsClosed()).isZero();
        assertThat(result.closableAfter()).isZero();
        assertThat(signature(grid)).isEqualTo(before);
        assertThat(edgeCount(grid)).isEqualTo(12 * 12 - 1);
    }

    @Test
    void fullSeal_reducesABraidToATree_andKeepsEveryoneConnected() {
        MazeGrid grid = perfectMaze(12, 42L);
        Braider.braid(grid, 1.0, 11L);
        int extras = Sealer.closablePassages(grid).size();
        assertThat(extras).isPositive();
        int edgesBefore = edgeCount(grid);

        SealResult result = Sealer.seal(grid, 1.0, 7L);

        assertThat(result.wallsClosed()).isEqualTo(extras);
        assertThat(result.closableAfter()).isZero();
        assertThat(edgeCount(grid)).isEqualTo(edgesBefore - extras);
        assertThat(edgeCount(grid)).isEqualTo(12 * 12 - 1); // back to a spanning tree
        assertHabitableConnected(grid);
        assertThat(new BfsSolver().solve(grid, grid.start(), grid.goal(), new MazeStats()))
                .isNotEmpty();
    }

    @Test
    void zeroFactor_isANoOp() {
        MazeGrid grid = perfectMaze(8, 3L);
        Braider.braid(grid, 1.0, 5L);
        List<String> before = signature(grid);

        SealResult result = Sealer.seal(grid, 0.0, 7L);

        assertThat(result.wallsClosed()).isZero();
        assertThat(result.closableAfter()).isEqualTo(result.closableBefore());
        assertThat(signature(grid)).isEqualTo(before);
    }

    @Test
    void partialFactor_closesThatFractionOfExtras() {
        MazeGrid grid = perfectMaze(12, 42L);
        Braider.braid(grid, 1.0, 11L);
        int extras = Sealer.closablePassages(grid).size();

        SealResult result = Sealer.seal(grid, 0.5, 7L);

        assertThat(result.wallsClosed()).isEqualTo((int) Math.round(0.5 * extras));
        assertThat(result.closableAfter()).isLessThan(result.closableBefore());
        assertHabitableConnected(grid);
    }

    @Test
    void isDeterministicForAGivenSeed() {
        MazeGrid a = braided(12, 42L, 11L);
        MazeGrid b = braided(12, 42L, 11L);

        SealResult ra = Sealer.seal(a, 0.5, 7L);
        SealResult rb = Sealer.seal(b, 0.5, 7L);

        assertThat(ra).isEqualTo(rb);
        assertThat(signature(a)).isEqualTo(signature(b));
    }

    @Test
    void differentSeeds_generallyPickDifferentWalls() {
        MazeGrid a = braided(16, 42L, 11L);
        MazeGrid b = braided(16, 42L, 11L);

        Sealer.seal(a, 0.5, 1L);
        Sealer.seal(b, 0.5, 999L);

        assertThat(signature(a)).isNotEqualTo(signature(b));
    }

    /**
     * The reason this is a spanning-forest complement and not "close every current
     * non-bridge". Two parallel corridors between the same rooms: each corridor is a
     * non-bridge on its own, and closing both disconnects the rooms. The forest keeps
     * exactly one, so a full seal leaves the rooms joined.
     */
    @Test
    void twoParallelPaths_fullSealKeepsExactlyOne() {
        // 3×3: a ring around the centre plus a second east-west through the middle row
        // would be messy. Simpler: two 1-wide corridors of length 3, joined at both ends.
        //
        //   (0,0)—(0,1)—(0,2)
        //     |           |
        //   (1,0)       (1,2)
        //     |           |
        //   (2,0)—(2,1)—(2,2)
        //
        // Two start→goal routes; the four "rung" edges are the forest, the two long
        // sides are extras — or vice versa, depending on BFS order. Either way exactly
        // one of the two disjoint start-goal cuts survives a full seal.
        MazeGrid grid = new MazeGrid(3, 3);
        grid.carve(new Point(0, 0), new Point(0, 1));
        grid.carve(new Point(0, 1), new Point(0, 2));
        grid.carve(new Point(0, 0), new Point(1, 0));
        grid.carve(new Point(1, 0), new Point(2, 0));
        grid.carve(new Point(2, 0), new Point(2, 1));
        grid.carve(new Point(2, 1), new Point(2, 2));
        grid.carve(new Point(0, 2), new Point(1, 2));
        grid.carve(new Point(1, 2), new Point(2, 2));
        grid.setStart(new Point(0, 0));
        grid.setGoal(new Point(2, 2));

        assertThat(Sealer.closablePassages(grid)).hasSize(1); // 8 edges, 8 habitable? 8 cells
        // 8 carved cells (centre is rock), 8 edges, forest has 7, one extra.
        SealResult result = Sealer.seal(grid, 1.0, 1L);
        assertThat(result.wallsClosed()).isEqualTo(1);
        assertHabitableConnected(grid);
        assertThat(new BfsSolver().solve(grid, grid.start(), grid.goal(), new MazeStats()))
                .as("closing the extra must not seal start from goal")
                .isNotEmpty();
    }

    /**
     * Teeth: if Sealer closed walls without consulting the forest, this ring would
     * survive a "close everything" only by luck. After a full seal the habitable
     * set is still one component — the assertion a mutant that seals a bridge fails.
     */
    @Test
    void sealingNeverCreatesANewComponent() {
        for (long seed = 0; seed < 8; seed++) {
            MazeGrid grid = braided(15, seed, seed + 17);
            Set<Integer> componentsBefore = componentSizes(grid);
            Sealer.seal(grid, 1.0, seed);
            assertThat(componentSizes(grid))
                    .as("seed %d: habitable components must be unchanged", seed)
                    .isEqualTo(componentsBefore);
        }
    }

    // ---------- helpers ----------

    private static MazeGrid braided(int size, long genSeed, long braidSeed) {
        MazeGrid grid = perfectMaze(size, genSeed);
        Braider.braid(grid, 1.0, braidSeed);
        return grid;
    }

    private static int edgeCount(MazeGrid grid) {
        int halfEdges = 0;
        for (int r = 0; r < grid.rows(); r++) {
            for (int c = 0; c < grid.cols(); c++) {
                halfEdges += grid.openNeighbors(new Point(r, c)).size();
            }
        }
        return halfEdges / 2;
    }

    private static List<String> signature(MazeGrid grid) {
        List<String> sig = new ArrayList<>();
        for (int r = 0; r < grid.rows(); r++) {
            for (int c = 0; c < grid.cols(); c++) {
                Point p = new Point(r, c);
                sig.add(p + "->" + grid.openNeighbors(p));
            }
        }
        return sig;
    }

    private static void assertHabitableConnected(MazeGrid grid) {
        assertThat(componentSizes(grid)).hasSize(1);
    }

    /** Sizes of habitable (degree &gt; 0) components, as a multiset. */
    private static Set<Integer> componentSizes(MazeGrid grid) {
        boolean[] seen = new boolean[grid.rows() * grid.cols()];
        int cols = grid.cols();
        List<Integer> sizes = new ArrayList<>();
        for (int r = 0; r < grid.rows(); r++) {
            for (int c = 0; c < grid.cols(); c++) {
                Point start = new Point(r, c);
                int id = r * cols + c;
                if (seen[id] || grid.openNeighbors(start).isEmpty()) {
                    continue;
                }
                int size = 0;
                List<Point> stack = new ArrayList<>();
                stack.add(start);
                seen[id] = true;
                while (!stack.isEmpty()) {
                    Point p = stack.remove(stack.size() - 1);
                    size++;
                    for (Point n : grid.openNeighbors(p)) {
                        int nid = n.row() * cols + n.col();
                        if (!seen[nid]) {
                            seen[nid] = true;
                            stack.add(n);
                        }
                    }
                }
                sizes.add(size);
            }
        }
        return new HashSet<>(sizes);
    }
}
