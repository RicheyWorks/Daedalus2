// SPDX-License-Identifier: MIT

package com.daedalus.engine;

import com.daedalus.engine.generators.BinaryTreeGenerator;
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

    @Test
    void everyChildIsFullyConnected_theRepairIsLoadBearing() {
        // Across several seeds: every cell reachable from (0,0). This is the property the
        // ADR flagged as crossbreeding's real algorithmic problem.
        for (long seed = 0; seed < 8; seed++) {
            MazeGrid child = MazeBreeder.breed(backtracker, binaryTree, seed);
            int[][] dist = MazeMetrics.distancesFrom(child, new Point(0, 0));
            for (int r = 0; r < child.rows(); r++) {
                for (int c = 0; c < child.cols(); c++) {
                    assertThat(dist[r][c])
                            .as("cell (%d,%d) must be reachable (seed %d)", r, c, seed)
                            .isGreaterThanOrEqualTo(0);
                }
            }
        }
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
