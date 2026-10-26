// SPDX-License-Identifier: MIT

package com.daedalus.theory;

import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.Point;
import com.daedalus.theory.BipartiteMatching.Matching;
import com.daedalus.theory.BipartiteMatching.Placement;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * {@link BipartiteMatching}. The load-bearing fixture is the one first-fit gets wrong:
 * a request that can use either server takes the only server the other request can use.
 */
class BipartiteMatchingTest {

    @Test
    void firstFitStrandsARequestThatMaxFlowPlaces() {
        // r0 → {s0, s1}, r1 → {s0}. First-fit gives r0 the only seat r1 can take.
        boolean[][] eligible = {
                {true, true},
                {true, false}
        };
        int[] capacity = {1, 1};

        Matching flow = BipartiteMatching.assign(2, 2, capacity, eligible);
        Matching greedy = firstFit(2, 2, capacity, eligible);

        assertThat(greedy.unmatchedRequests())
                .as("first-fit is the algorithm this must not be")
                .isEqualTo(1);
        assertThat(flow.unmatchedRequests()).isZero();
        assertThat(flow.pairs()).containsExactly(
                new BipartiteMatching.Assignment(0, 1),
                new BipartiteMatching.Assignment(1, 0));
    }

    @Test
    void serverCapacityTwoTakesTwoRequests() {
        boolean[][] eligible = {
                {true},
                {true},
                {true}
        };

        Matching cut = BipartiteMatching.assign(3, 1, new int[] {2}, eligible);

        assertThat(cut.pairs()).hasSize(2);
        assertThat(cut.unmatchedRequests()).isEqualTo(1);
    }

    @Test
    void ineligibleEdgeIsNeverUsed() {
        boolean[][] eligible = {
                {false, true},
                {false, true}
        };

        Matching cut = BipartiteMatching.assign(2, 2, new int[] {1, 1}, eligible);

        assertThat(cut.pairs()).extracting(BipartiteMatching.Assignment::server)
                .containsOnly(1);
        assertThat(cut.unmatchedRequests()).isEqualTo(1);
    }

    @Test
    void moreRequestsThanTotalCapacityLeaveTheOverflowUnmatched() {
        boolean[][] eligible = {
                {true, true},
                {true, true},
                {true, true},
                {true, true}
        };

        Matching cut = BipartiteMatching.assign(4, 2, new int[] {1, 1}, eligible);

        assertThat(cut.pairs()).hasSize(2);
        assertThat(cut.unmatchedRequests()).isEqualTo(2);
    }

    @Test
    void isDeterministic() {
        boolean[][] eligible = {
                {true, true},
                {true, true}
        };
        int[] capacity = {1, 1};

        assertThat(BipartiteMatching.assign(2, 2, capacity, eligible))
                .isEqualTo(BipartiteMatching.assign(2, 2, capacity, eligible));
    }

    @Test
    void negativeCapacityIsRejected() {
        assertThatThrownBy(() -> BipartiteMatching.assign(1, 1, new int[] {-1}, new boolean[][] {{true}}))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining(">= 0");
    }

    @Test
    void assignToFacilities_respectsHopBudgetAndCapacity() {
        MazeGrid grid = new RecursiveBacktrackerGenerator().generate(8, 8, 3L);
        List<Point> facilities = FacilityPlacement.kCenter(grid, 2).facilities();
        List<Point> requests = allCells(grid);

        Placement tight = BipartiteMatching.assignToFacilities(grid, requests, facilities, 1, 0);
        Placement roomy = BipartiteMatching.assignToFacilities(
                grid, requests, facilities, 1, Integer.MAX_VALUE);

        assertThat(tight.pairs()).hasSizeLessThanOrEqualTo(2);
        assertThat(roomy.pairs()).hasSize(2);
        assertThat(roomy.unmatchedRequests()).isEqualTo(requests.size() - 2);
        for (var pair : tight.pairs()) {
            assertThat(pair.request()).isEqualTo(pair.facility());
        }
    }

    /**
     * The algorithm this class exists to beat: walk requests in order, take the first
     * server that still has a seat. On the load-bearing fixture it leaves one unmatched.
     */
    private static Matching firstFit(int nRequests, int nServers, int[] capacity, boolean[][] eligible) {
        int[] left = capacity.clone();
        List<BipartiteMatching.Assignment> pairs = new ArrayList<>();
        for (int i = 0; i < nRequests; i++) {
            for (int j = 0; j < nServers; j++) {
                if (eligible[i][j] && left[j] > 0) {
                    left[j]--;
                    pairs.add(new BipartiteMatching.Assignment(i, j));
                    break;
                }
            }
        }
        return new Matching(pairs, nRequests - pairs.size());
    }

    private static List<Point> allCells(MazeGrid grid) {
        List<Point> cells = new ArrayList<>();
        for (int r = 0; r < grid.rows(); r++) {
            for (int c = 0; c < grid.cols(); c++) {
                cells.add(new Point(r, c));
            }
        }
        return cells;
    }
}
