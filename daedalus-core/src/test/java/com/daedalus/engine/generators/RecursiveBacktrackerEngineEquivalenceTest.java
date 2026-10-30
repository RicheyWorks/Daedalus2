// SPDX-License-Identifier: MIT

package com.daedalus.engine.generators;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Locks the contract that {@link RecursiveBacktrackerGenerator} <em>is</em> a thin
 * delegation to {@link GrowingTreeEngine}{@code .run(..., }{@link
 * GrowingTreePolicies#newest()}{@code )} — bit-for-bit equivalent output for every
 * {@code (seed, rows, cols)} triple.
 *
 * <p>Why this test exists: the 2026-05-11 refactor folded RB onto the shared engine.
 * The class-level Javadoc claims the seed → maze mapping is preserved (a strictly
 * better outcome than the original BACKLOG worried about). This test catches any
 * future divergence — for example, if someone reintroduces a hand-rolled DFS in RB,
 * the per-cell {@code openNeighbors} comparison will diverge and the test will fail
 * loudly with a clear "(row, col)" location label.
 *
 * <p>Coverage spans a handful of dimension / seed combinations chosen to stress both
 * tall and wide grids plus a non-square one — enough to catch a "works for square
 * grids" regression while still running in well under 100 ms.
 *
 * @since 1.0
 */
class RecursiveBacktrackerEngineEquivalenceTest {

    @ParameterizedTest(name = "RB == engine.newest() at rows={0} cols={1} seed={2}")
    @CsvSource({
            // Square, tall, wide, and a non-square — enough variety that a
            // dimension-specific divergence wouldn't slip through.
            "12, 17, 42",
            "8,  8,  1",
            "20, 5,  2026051100",
            "5,  20, 2026051100",
            "16, 16, -1"
    })
    void rbOutputMatchesGrowingTreeEngineWithNewestPolicy(int rows, int cols, long seed) {
        MazeGrid rb  = new RecursiveBacktrackerGenerator()
                .generate(rows, cols, seed, new MazeStats());
        MazeGrid eng = GrowingTreeEngine.run(rows, cols, seed, new MazeStats(),
                GrowingTreePolicies.newest());

        assertThat(rb.rows()).isEqualTo(eng.rows());
        assertThat(rb.cols()).isEqualTo(eng.cols());

        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                Point p = new Point(r, c);
                assertThat(rb.openNeighbors(p))
                        .as("openNeighbors at (%d,%d), seed=%d", r, c, seed)
                        .containsExactlyInAnyOrderElementsOf(eng.openNeighbors(p));
            }
        }
    }

    @Test
    void backToBackInvocationsAreSeedDeterministic() {
        // A regression that broke seed determinism inside RB (e.g. consulting
        // ThreadLocalRandom instead of the passed seed) would fail this test even
        // if the per-engine equivalence test happened to pass by chance.
        long seed = 7L;
        int rows = 11, cols = 13;
        RecursiveBacktrackerGenerator g = new RecursiveBacktrackerGenerator();

        MazeGrid a = g.generate(rows, cols, seed, new MazeStats());
        MazeGrid b = g.generate(rows, cols, seed, new MazeStats());

        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                Point p = new Point(r, c);
                assertThat(a.openNeighbors(p))
                        .as("openNeighbors at (%d,%d)", r, c)
                        .containsExactlyInAnyOrderElementsOf(b.openNeighbors(p));
            }
        }
    }
}
