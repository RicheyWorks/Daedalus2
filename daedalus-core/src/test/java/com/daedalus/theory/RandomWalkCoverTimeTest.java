// SPDX-License-Identifier: MIT

package com.daedalus.theory;

import com.daedalus.engine.MazeGenerator;
import com.daedalus.engine.generators.AldousBroderGenerator;
import com.daedalus.engine.generators.WilsonsGenerator;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Empirical cover-time comparison of the two uniform-spanning-tree generators (ideas G2 + T4).
 *
 * <p>Aldous-Broder and Wilson's both sample a <em>uniform</em> spanning tree, so they are
 * interchangeable in output but not in cost. Aldous-Broder walks blindly until it has covered every
 * cell, so its work is the random walk's <b>cover time</b>; Wilson's walks only until it hits the
 * tree built so far and erases loops, which is governed by hitting times and is far cheaper.
 *
 * <p>Both generators now count random-walk steps into {@code MazeStats.cellsExplored} — before that
 * instrumentation neither exposed cover time at all, since {@code cellsVisited} counts only cells
 * added to the maze and is therefore exactly {@code n} for both.
 *
 * <p>Measurements are averaged over several seeds: a single random-walk run is far too noisy to
 * assert on (see the note in {@link GrowthEstimator} about class labels wobbling on high-variance
 * randomized algorithms).
 */
class RandomWalkCoverTimeTest {

    private static final int SEEDS = 7;

    private static long averageSteps(MazeGenerator generator, int size) {
        long total = 0;
        for (long seed = 1; seed <= SEEDS; seed++) {
            total += ComplexityAnalyzer.measure(generator, size, size, seed).cellsExplored();
        }
        return total / SEEDS;
    }

    private static double stepsPerCell(MazeGenerator generator, int size) {
        return (double) averageSteps(generator, size) / ((long) size * size);
    }

    @Test
    void bothGeneratorsNowReportRandomWalkSteps() {
        assertThat(averageSteps(new AldousBroderGenerator(), 16)).isPositive();
        assertThat(averageSteps(new WilsonsGenerator(), 16)).isPositive();
    }

    @Test
    void aldousBroderWalksFartherThanWilsons_atEverySize() {
        for (int size : new int[] {16, 32, 64}) {
            assertThat(averageSteps(new AldousBroderGenerator(), size))
                    .as("size %d: blind cover-time walk must cost more than loop-erased walks", size)
                    .isGreaterThan(averageSteps(new WilsonsGenerator(), size));
        }
    }

    @Test
    void aldousBroderCostPerCellGrowsWithSize_whileWilsonsStaysFlat() {
        double aldousSmall = stepsPerCell(new AldousBroderGenerator(), 16);
        double aldousLarge = stepsPerCell(new AldousBroderGenerator(), 64);
        double wilsonsSmall = stepsPerCell(new WilsonsGenerator(), 16);
        double wilsonsLarge = stepsPerCell(new WilsonsGenerator(), 64);

        // Aldous-Broder is superlinear: steps/cell climbs as the maze grows (~19 -> ~35 observed).
        assertThat(aldousLarge)
                .as("Aldous-Broder steps per cell should climb with n")
                .isGreaterThan(aldousSmall * 1.3);

        // Wilson's is essentially linear: steps/cell stays in a narrow band (~5 -> ~7 observed).
        assertThat(wilsonsLarge)
                .as("Wilson's steps per cell should stay roughly flat")
                .isLessThan(wilsonsSmall * 2.5);
    }
}
