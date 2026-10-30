// SPDX-License-Identifier: MIT

package com.daedalus.theory;

import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.Point;
import com.daedalus.theory.FacilityPlacement.Placement;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * {@link FacilityPlacement}. The load-bearing test is the approximation guarantee: the greedy's
 * covering radius must never exceed <b>twice</b> the true optimum, checked against brute-force
 * enumeration of every possible facility set on small mazes.
 */
class FacilityPlacementTest {

    @Test
    void greedyIsWithinTwiceOptimal_checkedAgainstBruteForce() {
        for (long seed = 1; seed <= 4; seed++) {
            MazeGrid grid = new RecursiveBacktrackerGenerator().generate(5, 5, seed);
            DistanceOracle oracle = DistanceOracle.precompute(grid);
            List<Point> cells = allCells(grid);

            for (int k = 2; k <= 3; k++) {
                int greedy = FacilityPlacement.kCenter(grid, k).coveringRadius();
                int optimal = bruteForceOptimum(cells, oracle, k);

                assertThat(greedy)
                        .as("seed %d k=%d: greedy %d must be <= 2 x optimal %d", seed, k, greedy, optimal)
                        .isLessThanOrEqualTo(2 * optimal);
                assertThat(greedy).isGreaterThanOrEqualTo(optimal); // and never better than optimal
            }
        }
    }

    @Test
    void moreFacilitiesNeverIncreaseTheRadius() {
        MazeGrid grid = new RecursiveBacktrackerGenerator().generate(16, 16, 42L);

        int previous = Integer.MAX_VALUE;
        for (int k = 1; k <= 8; k++) {
            int radius = FacilityPlacement.kCenter(grid, k).coveringRadius();
            assertThat(radius).as("k=%d", k).isLessThanOrEqualTo(previous);
            previous = radius;
        }
    }

    @Test
    void oneFacilityPerCell_meansEveryoneIsServedAtDistanceZero() {
        MazeGrid grid = new RecursiveBacktrackerGenerator().generate(6, 6, 3L);

        Placement placement = FacilityPlacement.kCenter(grid, 36);

        assertThat(placement.coveringRadius()).isZero();
        assertThat(placement.facilities()).hasSize(36).doesNotHaveDuplicates();
    }

    @Test
    void stopsEarlyWhenNoUsefulLocationsRemain() {
        // A 1x3 corridor has only three cells, so a request for ten facilities yields three.
        MazeGrid grid = new MazeGrid(1, 3);
        grid.carve(new Point(0, 0), new Point(0, 1));
        grid.carve(new Point(0, 1), new Point(0, 2));

        Placement placement = FacilityPlacement.kCenter(grid, 10);

        assertThat(placement.facilities()).hasSizeLessThanOrEqualTo(3);
        assertThat(placement.coveringRadius()).isZero();
    }

    @Test
    void unreachableCellsAreNotServed_andDoNotDistortTheRadius() {
        MazeGrid grid = new MazeGrid(2, 2);
        grid.carve(new Point(0, 0), new Point(0, 1)); // (1,0) and (1,1) walled off

        Placement placement = FacilityPlacement.kCenter(grid, 1);

        assertThat(placement.servedCells()).isEqualTo(2);
        assertThat(placement.coveringRadius()).isEqualTo(1);
    }

    @Test
    void isDeterministic() {
        MazeGrid grid = new RecursiveBacktrackerGenerator().generate(12, 12, 7L);

        assertThat(FacilityPlacement.kCenter(grid, 4))
                .isEqualTo(FacilityPlacement.kCenter(grid, 4));
    }

    @Test
    void coveringRadiusScoresACallerChosenPlacement() {
        MazeGrid grid = new RecursiveBacktrackerGenerator().generate(10, 10, 1L);
        Placement greedy = FacilityPlacement.kCenter(grid, 3);

        // Scoring the greedy's own choice must reproduce its reported radius.
        assertThat(FacilityPlacement.coveringRadius(grid, greedy.facilities()))
                .isEqualTo(greedy.coveringRadius());
    }

    @Test
    void rejectsNonPositiveK() {
        MazeGrid grid = new RecursiveBacktrackerGenerator().generate(5, 5, 1L);

        assertThatThrownBy(() -> FacilityPlacement.kCenter(grid, 0))
                .isInstanceOf(IllegalArgumentException.class);
    }

    // ---------- brute-force oracle ----------

    private static List<Point> allCells(MazeGrid grid) {
        List<Point> cells = new ArrayList<>();
        for (int r = 0; r < grid.rows(); r++) {
            for (int c = 0; c < grid.cols(); c++) {
                cells.add(new Point(r, c));
            }
        }
        return cells;
    }

    /** Smallest covering radius over every k-subset — the definition the greedy approximates. */
    private static int bruteForceOptimum(List<Point> cells, DistanceOracle oracle, int k) {
        int[] best = {Integer.MAX_VALUE};
        choose(cells, oracle, k, 0, new ArrayList<>(), best);
        return best[0];
    }

    private static void choose(List<Point> cells, DistanceOracle oracle, int k, int from,
                               List<Point> picked, int[] best) {
        if (picked.size() == k) {
            best[0] = Math.min(best[0], radiusOf(cells, oracle, picked));
            return;
        }
        for (int i = from; i < cells.size(); i++) {
            picked.add(cells.get(i));
            choose(cells, oracle, k, i + 1, picked, best);
            picked.remove(picked.size() - 1);
        }
    }

    private static int radiusOf(List<Point> cells, DistanceOracle oracle, List<Point> facilities) {
        int radius = 0;
        for (Point cell : cells) {
            int nearest = Integer.MAX_VALUE;
            for (Point facility : facilities) {
                int d = oracle.distance(cell, facility);
                if (d >= 0) {
                    nearest = Math.min(nearest, d);
                }
            }
            if (nearest != Integer.MAX_VALUE) {
                radius = Math.max(radius, nearest);
            }
        }
        return radius;
    }
}
