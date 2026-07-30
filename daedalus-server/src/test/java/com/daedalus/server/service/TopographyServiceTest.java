// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.DungeonGenerator;
import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.Point;
import com.daedalus.theory.MazeMetrics;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Distance fields (ADR-007 idea 6) and sanctuary placement (ADR-007 idea 5).
 *
 * <p>The field test that matters is the counter-intuitive one. Drawn on screen a maze distance
 * field does <em>not</em> look like a halo around the origin: two cells that touch can be 200
 * steps apart, because a wall stands between them. Reviewing the first render, that looked like
 * a bug — it is the opposite, and it is the most informative thing the overlay shows, so it is
 * pinned here as a property rather than left to be "fixed" by someone who trusts their eyes over
 * the graph.
 */
class TopographyServiceTest {

    private MazeGenerationService gen;
    private TopographyService topography;

    @BeforeEach
    void setUp() {
        gen = new MazeGenerationService(
                new GeneratorRegistry(List.of(
                        new RecursiveBacktrackerGenerator(), new DungeonGenerator())),
                event -> { }, new SimpleMeterRegistry());
        topography = new TopographyService(gen, 16_384);
    }

    @Test
    void unknownMaze_isNull_forBothViews() {
        assertThat(topography.fieldFor(UUID.randomUUID(), TopographyService.Origin.GOAL)).isNull();
        assertThat(topography.sanctuariesFor(UUID.randomUUID(), 5)).isNull();
    }

    @Test
    void theFieldIsZeroAtItsOrigin_andEveryCellIsOneMoreThanANeighbour() {
        var cached = gen.generate("recursive-backtracker", 21, 21, 7L);
        MazeGrid grid = cached.grid();

        var field = topography.fieldFor(cached.metadata().id(), TopographyService.Origin.GOAL);

        assertThat(field.origin()).isEqualTo(grid.goal());
        assertThat(field.distances()[grid.goal().row()][grid.goal().col()]).isZero();
        assertThat(field.unreachable()).as("a perfect maze has no unreachable cells").isZero();

        // The defining property of a BFS field: every non-origin cell is exactly one step
        // further than its closest OPEN neighbour. This is what makes the shading trustworthy.
        for (int r = 0; r < grid.rows(); r++) {
            for (int c = 0; c < grid.cols(); c++) {
                Point p = new Point(r, c);
                if (p.equals(grid.goal())) {
                    continue;
                }
                int best = Integer.MAX_VALUE;
                for (Point n : grid.openNeighbors(p)) {
                    best = Math.min(best, field.distances()[n.row()][n.col()]);
                }
                assertThat(field.distances()[r][c])
                        .as("cell (%d,%d) must be one step past its nearest open neighbour", r, c)
                        .isEqualTo(best + 1);
            }
        }
    }

    @Test
    void neighbouringCellsCanBeHundredsOfStepsApart_becauseAWallIsBetweenThem() {
        // Reviewing the rendered heat map, the absence of a smooth halo looked wrong. It is not:
        // the field measures walking distance, and a wall makes touching cells remote. If this
        // ever stops being true of a 21x21 perfect maze, the field has quietly become Euclidean.
        var cached = gen.generate("recursive-backtracker", 21, 21, 7L);
        var field = topography.fieldFor(cached.metadata().id(), TopographyService.Origin.GOAL);
        int[][] d = field.distances();

        int worstAdjacentJump = 0;
        for (int r = 0; r < field.rows(); r++) {
            for (int c = 0; c + 1 < field.cols(); c++) {
                worstAdjacentJump = Math.max(worstAdjacentJump, Math.abs(d[r][c] - d[r][c + 1]));
            }
        }
        assertThat(worstAdjacentJump)
                .as("side-by-side cells separated by a wall are far apart by walking distance")
                .isGreaterThan(100);
    }

    @Test
    void aDungeonsRockIsReportedUnreachable_ratherThanShadedAsNear() {
        var cached = gen.generate("dungeon", 21, 21, 7L);

        var field = topography.fieldFor(cached.metadata().id(), TopographyService.Origin.GOAL);

        assertThat(field.unreachable())
                .as("most of a dungeon is solid rock and must not be drawn as distance 0")
                .isGreaterThan(100);
        int minusOnes = 0;
        for (int[] row : field.distances()) {
            for (int v : row) {
                if (v < 0) {
                    minusOnes++;
                }
            }
        }
        assertThat(minusOnes).isEqualTo(field.unreachable());
    }

    @Test
    void startAndGoalOriginsGiveDifferentFields() {
        var cached = gen.generate("recursive-backtracker", 21, 21, 7L);
        var id = cached.metadata().id();

        var fromGoal = topography.fieldFor(id, TopographyService.Origin.GOAL);
        var fromStart = topography.fieldFor(id, TopographyService.Origin.START);

        assertThat(fromStart.origin()).isEqualTo(cached.grid().start());
        assertThat(fromStart.distances()).isNotEqualTo(fromGoal.distances());
    }

    @Test
    void anOversizedFieldIsRefusedWithAnExplanation_notTruncated() {
        var small = new TopographyService(gen, 100);
        var cached = gen.generate("recursive-backtracker", 21, 21, 7L);

        assertThatThrownBy(() -> small.fieldFor(cached.metadata().id(),
                TopographyService.Origin.GOAL))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("441")
                .hasMessageContaining("payload cap");
    }

    @Test
    void theCoveringRadiusIsTheRealWalkFromTheWorstServedCell() {
        var cached = gen.generate("recursive-backtracker", 21, 21, 7L);
        MazeGrid grid = cached.grid();

        var s = topography.sanctuariesFor(cached.metadata().id(), 5);

        assertThat(s.placements()).hasSize(5);
        assertThat(s.servedCells()).isEqualTo(s.habitableCells());

        // Re-derive the radius independently: BFS from every sanctuary, take each cell's nearest,
        // and the largest of those must be exactly the reported radius, at exactly worstServed.
        int worst = -1;
        for (int r = 0; r < grid.rows(); r++) {
            for (int c = 0; c < grid.cols(); c++) {
                int nearest = Integer.MAX_VALUE;
                for (Point f : s.placements()) {
                    int d = MazeMetrics.distancesFrom(grid, f)[r][c];
                    if (d >= 0) {
                        nearest = Math.min(nearest, d);
                    }
                }
                if (nearest != Integer.MAX_VALUE) {
                    worst = Math.max(worst, nearest);
                }
            }
        }
        assertThat(s.coveringRadius()).isEqualTo(worst);

        int atWorstServed = Integer.MAX_VALUE;
        for (Point f : s.placements()) {
            int d = MazeMetrics.distancesFrom(grid, f)[s.worstServed().row()][s.worstServed().col()];
            if (d >= 0) {
                atWorstServed = Math.min(atWorstServed, d);
            }
        }
        assertThat(atWorstServed)
                .as("worstServed must be a cell that actually sits at the covering radius")
                .isEqualTo(s.coveringRadius());
    }

    @Test
    void moreSanctuariesNeverMakeTheWorstCaseWorse() {
        var cached = gen.generate("recursive-backtracker", 21, 21, 7L);
        var id = cached.metadata().id();

        int previous = Integer.MAX_VALUE;
        for (int k = 1; k <= 8; k++) {
            var s = topography.sanctuariesFor(id, k);
            assertThat(s.coveringRadius())
                    .as("k=%d must not be served worse than k=%d", k, k - 1)
                    .isLessThanOrEqualTo(previous);
            previous = s.coveringRadius();
        }
    }

    @Test
    void kIsClampedRatherThanTrusted() {
        var cached = gen.generate("recursive-backtracker", 21, 21, 7L);
        var id = cached.metadata().id();

        assertThat(topography.sanctuariesFor(id, 9999).placements())
                .hasSize(TopographyService.MAX_SANCTUARIES);
        assertThat(topography.sanctuariesFor(id, -4).placements()).hasSize(1);
        assertThat(topography.sanctuariesFor(id, null).placements()).hasSize(5);
    }
}
