// SPDX-License-Identifier: MIT

package com.daedalus.engine;

import com.daedalus.engine.generators.BinaryTreeGenerator;
import com.daedalus.engine.generators.DungeonGenerator;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.theory.MazeMetrics;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Crossbreeding's contract (ADR-006 idea #5): whatever the parents, the child is one
 * connected maze (the Kruskal repair is the load-bearing part — stitched patches almost
 * never agree on their own), the operation is deterministic, and the child genuinely
 * inherits from both sides rather than cloning either parent.
 */
class MazeBreederTest {

    private final MazeGrid backtracker =
            new RecursiveBacktrackerGenerator().generate(15, 15, 42L, new MazeStats());
    private final MazeGrid binaryTree =
            new BinaryTreeGenerator().generate(15, 15, 42L, new MazeStats());

    /** Cells with no opening at all are uncarved rock, not rooms. */
    private static boolean isRock(MazeGrid grid, int row, int col) {
        return grid.openNeighbors(new Point(row, col)).isEmpty();
    }

    private static int rockCount(MazeGrid grid) {
        int rock = 0;
        for (int r = 0; r < grid.rows(); r++) {
            for (int c = 0; c < grid.cols(); c++) {
                if (isRock(grid, r, c)) {
                    rock++;
                }
            }
        }
        return rock;
    }

    /** Asserts every habitable cell of {@code child} is reachable from every other. */
    private static void assertHabitableCellsAllConnected(MazeGrid child, long seed) {
        Point anchor = null;
        for (int r = 0; r < child.rows() && anchor == null; r++) {
            for (int c = 0; c < child.cols() && anchor == null; c++) {
                if (!isRock(child, r, c)) {
                    anchor = new Point(r, c);
                }
            }
        }
        assertThat(anchor).as("a bred maze with no habitable cell at all").isNotNull();

        int[][] dist = MazeMetrics.distancesFrom(child, anchor);
        for (int r = 0; r < child.rows(); r++) {
            for (int c = 0; c < child.cols(); c++) {
                if (!isRock(child, r, c)) {
                    assertThat(dist[r][c])
                            .as("habitable cell (%d,%d) is stranded (seed %d)", r, c, seed)
                            .isGreaterThanOrEqualTo(0);
                }
            }
        }
    }

    @Test
    void everyHabitableCellIsReachable_theRepairIsLoadBearing() {
        // Across several seeds. This is the property the ADR flagged as crossbreeding's real
        // algorithmic problem. Both parents here are spanning trees (no rock), so for these
        // two "habitable" means every cell.
        for (long seed = 0; seed < 8; seed++) {
            MazeGrid child = MazeBreeder.breed(backtracker, binaryTree, seed);
            assertThat(rockCount(child)).as("spanning-tree parents cannot yield rock").isZero();
            assertHabitableCellsAllConnected(child, seed);
        }
    }

    /**
     * Breeding sparse parents must not carve their rock away.
     *
     * <p>The first repair ran Kruskal over every closed wall, so it connected rock as
     * enthusiastically as rooms: two 21×21 dungeon parents at 49% and 50% rock produced
     * children at 0% rock on every seed — connected, and unrecognisable as either parent.
     * Rooms still have to be mutually reachable, so this also pins the tunnelling path that
     * earns that.
     */
    @Test
    void dungeonOffspringKeepTheirRock() {
        MazeGrid dungeonA = new DungeonGenerator().generate(21, 21, 1L, new MazeStats());
        MazeGrid dungeonB = new DungeonGenerator().generate(21, 21, 2L, new MazeStats());
        int parentRock = Math.min(rockCount(dungeonA), rockCount(dungeonB));
        assertThat(parentRock).as("dungeon parents are supposed to be substantially rock")
                .isGreaterThan(21 * 21 / 4);

        for (long seed = 0; seed < 4; seed++) {
            MazeGrid child = MazeBreeder.breed(dungeonA, dungeonB, seed);
            assertThat(rockCount(child))
                    .as("seed %d: a dungeon crossbreed that carved its rock away is not a "
                            + "dungeon crossbreed", seed)
                    .isGreaterThan(parentRock / 2);
            assertHabitableCellsAllConnected(child, seed);
        }
    }

    @Test
    void aDungeonBredWithAPerfectMazeKeepsSomeRockAndStaysConnected() {
        MazeGrid dungeon = new DungeonGenerator().generate(21, 21, 7L, new MazeStats());
        MazeGrid maze = new RecursiveBacktrackerGenerator().generate(21, 21, 8L, new MazeStats());
        MazeGrid child = MazeBreeder.breed(dungeon, maze, 3L);
        // Half the patches come from a fully-carved parent, so expect less rock than the
        // dungeon parent but distinctly more than none.
        assertThat(rockCount(child)).isPositive().isLessThan(rockCount(dungeon));
        assertHabitableCellsAllConnected(child, 3L);
    }

    @Test
    void breedingIsDeterministic() {
        MazeGrid x = MazeBreeder.breed(backtracker, binaryTree, 7L);
        MazeGrid y = MazeBreeder.breed(backtracker, binaryTree, 7L);
        assertThat(x.toTileGrid()).isDeepEqualTo(y.toTileGrid());
    }

    @Test
    void theChildClonesNeitherParent() {
        MazeGrid child = MazeBreeder.breed(backtracker, binaryTree, 3L);
        assertThat(child.toTileGrid())
                .as("a bred maze is not parent A")
                .isNotEqualTo(backtracker.toTileGrid());
        assertThat(child.toTileGrid())
                .as("a bred maze is not parent B")
                .isNotEqualTo(binaryTree.toTileGrid());
    }

    @Test
    void mismatchedParentsAreRefused() {
        MazeGrid small = new RecursiveBacktrackerGenerator().generate(9, 9, 1L, new MazeStats());
        assertThatThrownBy(() -> MazeBreeder.breed(backtracker, small, 1L))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("dimensions");
    }
}
