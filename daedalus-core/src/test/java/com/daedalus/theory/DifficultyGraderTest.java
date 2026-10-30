// SPDX-License-Identifier: MIT

package com.daedalus.theory;

import com.daedalus.engine.Braider;
import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.BinaryTreeGenerator;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.MazeStats;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * The grader promises <em>ordering</em>, not calibration (see {@link DifficultyGrader}'s note),
 * so these tests pin ordering — the property the campaign ladder actually depends on.
 *
 * <p>The small-maze case is the one that caught a real defect: normalizing dead ends per
 * <em>cell</em> graded a trivial 3×3 (5.18) above a 5×5 (4.10), because tiny mazes spend a
 * third of their cells on dead ends. That would have put a campaign's first stage above its
 * second. Normalizing per perimeter fixed it, and this test is what keeps it fixed.
 */
class DifficultyGraderTest {

    private static MazeGrid backtracker(int n, long seed) {
        return new RecursiveBacktrackerGenerator().generate(n, n, seed, new MazeStats());
    }

    @Test
    void scoreRisesWithSize_includingAtTheSmallEnd() {
        double tiny = DifficultyGrader.grade(backtracker(3, 1L)).score();
        double small = DifficultyGrader.grade(backtracker(5, 1L)).score();
        double medium = DifficultyGrader.grade(backtracker(9, 1L)).score();
        double large = DifficultyGrader.grade(backtracker(21, 1L)).score();
        double huge = DifficultyGrader.grade(backtracker(31, 1L)).score();

        assertThat(tiny)
                .as("a trivial 3x3 must sit below a 5x5 — the per-cell normalization got this "
                        + "backwards and would have inverted a campaign's first two stages")
                .isLessThan(small);
        assertThat(small).isLessThan(medium);
        assertThat(medium).isLessThan(large);
        assertThat(large).isLessThan(huge);
    }

    @Test
    void aWindingGeneratorOutgradesAStraightOneAtEqualSize() {
        // Binary tree's severe NE bias produces long straight runs; the backtracker winds.
        double straight = DifficultyGrader.grade(
                new BinaryTreeGenerator().generate(21, 21, 4L, new MazeStats())).score();
        double winding = DifficultyGrader.grade(backtracker(21, 4L)).score();
        assertThat(winding).isGreaterThan(straight);
    }

    @Test
    void braidingAMazeMakesItEasier() {
        MazeGrid maze = backtracker(21, 5L);
        double before = DifficultyGrader.grade(maze).score();

        Braider.braid(maze, 1.0, 5L); // remove every dead end it can
        double after = DifficultyGrader.grade(maze).score();

        assertThat(after)
                .as("opening dead ends removes wrong turns — a braided maze forgives mistakes")
                .isLessThan(before);
    }

    @Test
    void labelsMatchTheDocumentedExamples() {
        assertThat(DifficultyGrader.grade(
                new BinaryTreeGenerator().generate(7, 7, 1L, new MazeStats())).label())
                .isEqualTo("gentle");
        assertThat(DifficultyGrader.grade(backtracker(41, 1L)).label())
                .isEqualTo("brutal");
    }

    @Test
    void everyMeasurementBehindTheScoreIsReported() {
        var g = DifficultyGrader.grade(backtracker(15, 2L));
        // The grade shows its work — a caller can audit the score instead of trusting it.
        assertThat(g.routeLength()).isPositive();
        assertThat(g.deadEnds()).isPositive();
        assertThat(g.alternateRoutes()).isEqualTo(1); // perfect maze: exactly one route
        assertThat(g.detourFactor()).isPositive();
        assertThat(g.branchiness()).isPositive();
        assertThat(g.score()).isPositive();
        assertThat(g.label()).isNotBlank();
    }
}
