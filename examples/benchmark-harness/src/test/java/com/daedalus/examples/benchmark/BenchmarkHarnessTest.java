// SPDX-License-Identifier: MIT

package com.daedalus.examples.benchmark;

import com.daedalus.engine.MazeGenerator;
import com.daedalus.solver.MazeSolver;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Tests the harness's <em>structure</em>, never its timings.
 *
 * <p>Asserting on measured milliseconds would produce a test that fails when the CI runner is
 * busy and passes when it is idle — noise dressed as a regression. What is worth pinning is
 * that the sweep covers every algorithm, that the rows it emits are well formed, and that a
 * slow algorithm degrades its own precision rather than hanging the run.
 */
class BenchmarkHarnessTest {

    @Test
    void theSweepCoversEveryGeneratorAndSolver() {
        // The failure this catches is an algorithm added to the engine and forgotten here, so
        // it silently never appears in any published benchmark.
        assertThat(BenchmarkHarness.generators())
                .extracting(MazeGenerator::id)
                .doesNotHaveDuplicates()
                .hasSizeGreaterThanOrEqualTo(22);
        assertThat(BenchmarkHarness.solvers())
                .extracting(MazeSolver::id)
                .doesNotHaveDuplicates()
                .hasSizeGreaterThanOrEqualTo(10);
    }

    @Test
    void everyAlgorithmProducesAWellFormedRow() {
        int size = 12;
        List<BenchmarkHarness.Row> rows = BenchmarkHarness.timeGenerators(size, 1);
        rows.addAll(BenchmarkHarness.timeSolvers(size, 1));

        assertThat(rows).hasSize(
                BenchmarkHarness.generators().size() + BenchmarkHarness.solvers().size());
        for (BenchmarkHarness.Row row : rows) {
            assertThat(row.id()).as("id must be populated").isNotBlank();
            assertThat(row.size()).isEqualTo(size);
            assertThat(row.medianMillis())
                    .as("%s must record a non-negative, finite duration", row.id())
                    .isNotNegative()
                    .isFinite();
            assertThat(row.work())
                    .as("%s must report the work it did, so a timing can be sanity-checked "
                            + "against it", row.id())
                    .isPositive();
        }
    }

    @Test
    void medianIgnoresASingleOutlier() {
        // The reason the harness reports medians: one GC pause or scheduler preemption must not
        // move the published number.
        assertThat(BenchmarkHarness.median(new double[] {10, 11, 12, 13, 9_999}))
                .isEqualTo(12);
        assertThat(BenchmarkHarness.median(new double[] {4, 2}))
                .as("even-length input averages the middle pair")
                .isEqualTo(3);
    }

    @Test
    void resultsResolveToASingleRepositoryLevelDirectory() {
        // Guards the bug this had: exec:java runs with the module as its working directory, so
        // a relative path created a second, invisible results directory under the example.
        assertThat(BenchmarkHarness.repositoryRoot())
                .as("root must be absolute so output does not depend on the launch directory")
                .isAbsolute();
    }
}
