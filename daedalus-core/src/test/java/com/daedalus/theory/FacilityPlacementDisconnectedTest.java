// SPDX-License-Identifier: MIT

package com.daedalus.theory;

import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.Direction;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Facility placement on a <b>fragmented</b> graph — the case the vision documents actually
 * describe, since chaos-engineering ("inject 15% node failure") partitions a topology.
 *
 * <p>{@link FacilityPlacement#kCenter} deliberately stays inside one component: unreachable
 * cells are treated as non-places, which is correct for a dungeon's solid rock. On a severed
 * network that behaviour clusters every facility into whichever fragment the first pick landed
 * in, and reports a small, healthy-looking covering radius while most of the graph goes
 * unserved. {@link FacilityPlacement#kCenterAcrossComponents} ranks unreachable cells as
 * infinitely badly served — which is what the k-center objective says — so the greedy reaches
 * new components first.
 *
 * <p>Both behaviours are intentional; these tests pin the difference so neither drifts.
 */
class FacilityPlacementDisconnectedTest {

    private static final int SIZE = 16;

    /**
     * A perfect maze severed along one column. A spanning tree cut at {@code n} edges falls
     * into {@code n + 1} components, so this shatters the grid rather than halving it — which
     * is exactly what makes it a good stress case.
     */
    private static MazeGrid severed(long seed) {
        MazeGrid grid = new RecursiveBacktrackerGenerator()
                .generate(SIZE, SIZE, seed, new MazeStats());
        int mid = SIZE / 2;
        for (int r = 0; r < SIZE; r++) {
            grid.cell(new Point(r, mid - 1)).close(Direction.EAST);
            grid.cell(new Point(r, mid)).close(Direction.WEST);
        }
        return grid;
    }

    /** How many distinct components the chosen facilities sit in. */
    private static long componentsTouched(MazeGrid grid, FacilityPlacement.Placement placement) {
        return placement.facilities().stream()
                .map(f -> {
                    // Identify a component by the row-major smallest cell reachable from f.
                    int[][] d = MazeMetrics.distancesFrom(grid, f);
                    for (int r = 0; r < grid.rows(); r++) {
                        for (int c = 0; c < grid.cols(); c++) {
                            if (d[r][c] >= 0) {
                                return new Point(r, c);
                            }
                        }
                    }
                    return f;
                })
                .distinct()
                .count();
    }

    @Test
    void plainKCenterClustersInOneComponent_andSaysSoViaServedCells() {
        MazeGrid grid = severed(1L);
        FacilityPlacement.Placement placement = FacilityPlacement.kCenter(grid, 3);

        assertThat(componentsTouched(grid, placement))
                .as("kCenter never leaves the component it started in")
                .isEqualTo(1);
        assertThat(placement.servedCells())
                .as("a severed grid leaves the other components unserved")
                .isLessThan(SIZE * SIZE);

        // The trap worth naming: adding facilities improves the reported radius while
        // coverage does not move at all, because every extra facility refines service inside
        // the one component the greedy can see.
        FacilityPlacement.Placement richer = FacilityPlacement.kCenter(grid, 12);
        assertThat(richer.coveringRadius())
                .as("radius improves with more facilities...")
                .isLessThan(placement.coveringRadius());
        assertThat(richer.servedCells())
                .as("...while coverage is completely unchanged — radius alone must not be trusted")
                .isEqualTo(placement.servedCells());
    }

    @Test
    void acrossComponentsVariantReachesSeparateFragments() {
        MazeGrid grid = severed(1L);
        FacilityPlacement.Placement spread =
                FacilityPlacement.kCenterAcrossComponents(grid, 3);

        assertThat(componentsTouched(grid, spread))
                .as("three facilities should reach three different fragments")
                .isEqualTo(3);
        assertThat(spread.servedCells())
                .as("and therefore serve strictly more of the graph")
                .isGreaterThan(FacilityPlacement.kCenter(grid, 3).servedCells());
    }

    @Test
    void moreFacilitiesNeverServeFewerCells() {
        // Monotonicity — the property most likely to break if the selection ordering is
        // fiddled with later.
        MazeGrid grid = severed(2L);
        int previous = 0;
        for (int k = 1; k <= 8; k++) {
            int served = FacilityPlacement.kCenterAcrossComponents(grid, k).servedCells();
            assertThat(served).as("k=%d must not serve fewer cells than k=%d", k, k - 1)
                    .isGreaterThanOrEqualTo(previous);
            previous = served;
        }
    }

    @Test
    void onAConnectedGridBothVariantsAgree() {
        // The generalisation must not disturb the ordinary case: with nothing unreachable,
        // "rank unreachable first" never fires and the two greedies are the same algorithm.
        MazeGrid connected = new RecursiveBacktrackerGenerator()
                .generate(SIZE, SIZE, 5L, new MazeStats());

        for (int k = 1; k <= 5; k++) {
            FacilityPlacement.Placement plain = FacilityPlacement.kCenter(connected, k);
            FacilityPlacement.Placement spread =
                    FacilityPlacement.kCenterAcrossComponents(connected, k);
            assertThat(spread.facilities()).as("k=%d", k).isEqualTo(plain.facilities());
            assertThat(spread.coveringRadius()).isEqualTo(plain.coveringRadius());
            assertThat(spread.servedCells()).isEqualTo(plain.servedCells());
        }
    }

    @Test
    void rejectsNonPositiveK() {
        MazeGrid grid = severed(3L);
        assertThat(org.assertj.core.api.Assertions
                .catchThrowable(() -> FacilityPlacement.kCenterAcrossComponents(grid, 0)))
                .isInstanceOf(IllegalArgumentException.class);
    }
}
