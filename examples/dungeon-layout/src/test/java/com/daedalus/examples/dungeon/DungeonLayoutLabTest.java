// SPDX-License-Identifier: MIT

package com.daedalus.examples.dungeon;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.Point;
import com.daedalus.theory.FacilityPlacement;
import com.daedalus.theory.MazeMetrics;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Pins the claims this example makes, and one bug it found.
 *
 * <p>Building this module immediately exposed a defect that had been latent in
 * {@code MazeMetrics}: {@code diameter} seeded its first BFS at {@code (0, 0)}, which is
 * always part of a maze but is <b>solid rock</b> in a BSP dungeon. So it measured a one-cell
 * component, returned a diameter of 0, and {@code placeStartAndGoalAtExtremes} put the
 * entrance and the boss room on the same square. {@code FacilityPlacement} seeded the same
 * way and reported a covering radius of 0 while serving 1 of 529 floor cells. Both now seed
 * from {@link MazeMetrics#largestComponentCell}, and the assertions below are what stop that
 * regressing.
 */
class DungeonLayoutLabTest {

    @Test
    void theLevelIsConnectedAndSubstantial() {
        MazeGrid level = DungeonLayoutLab.buildLevel();
        int floor = DungeonLayoutLab.floorCells(level);

        // A dungeon is mostly rock; the point is that the walkable part is a real space, not
        // the single isolated cell the old seeding collapsed to.
        assertThat(floor)
                .as("reachable floor area")
                .isGreaterThan(100);
    }

    @Test
    void entranceAndBossAreFarApart_notTheSameCell() {
        MazeGrid level = DungeonLayoutLab.buildLevel();

        assertThat(level.start())
                .as("a level whose entrance is its exit is not a level")
                .isNotEqualTo(level.goal());
        assertThat(MazeMetrics.distancesFrom(level, level.start())
                [level.goal().row()][level.goal().col()])
                .as("boss must be reachable from the entrance, and a long way off")
                .isGreaterThan(20);
    }

    @Test
    void fastDiameterAgreesWithExactOnThisLevel() {
        // Not guaranteed in general — the estimate can read short on a looped graph — but if
        // these ever diverge it is worth knowing, because the old bug showed up as exactly
        // this disagreement (0 versus 99).
        MazeGrid level = DungeonLayoutLab.buildLevel();
        assertThat(MazeMetrics.diameter(level).distance())
                .isEqualTo(MazeMetrics.exactDiameter(level).distance());
    }

    @Test
    void treasurePlacementCoversTheWholeFloor() {
        MazeGrid level = DungeonLayoutLab.buildLevel();
        FacilityPlacement.Placement placement = FacilityPlacement.kCenter(level, 5);

        assertThat(placement.servedCells())
                .as("every reachable room should be served by some vault")
                .isEqualTo(DungeonLayoutLab.floorCells(level));
        assertThat(placement.coveringRadius())
                .as("and the worst-served room should be a sane walk away, not 0")
                .isGreaterThan(0);
    }

    @Test
    void plannedLocationsAreDistinctReachablePlacesWithARisingDepthGradient() {
        MazeGrid level = DungeonLayoutLab.buildLevel();
        List<DungeonLayoutLab.Location> plan = DungeonLayoutLab.planLocations(level, 5);

        assertThat(plan).extracting(DungeonLayoutLab.Location::name).doesNotHaveDuplicates();
        assertThat(plan).extracting(DungeonLayoutLab.Location::cell).doesNotHaveDuplicates();

        for (DungeonLayoutLab.Location location : plan) {
            assertThat(location.depth())
                    .as("%s at %s must be reachable from the entrance", location.name(),
                            location.cell())
                    .isGreaterThanOrEqualTo(0);
        }

        DungeonLayoutLab.Location entrance = plan.get(0);
        DungeonLayoutLab.Location boss = plan.get(plan.size() - 1);
        assertThat(entrance.kind()).isEqualTo("ENTRANCE");
        assertThat(entrance.depth()).isZero();
        assertThat(boss.kind()).isEqualTo("BOSS");
        assertThat(boss.depth())
                .as("the boss should be the deepest thing in the level")
                .isEqualTo(plan.stream().mapToInt(DungeonLayoutLab.Location::depth).max()
                        .orElseThrow());
    }

    @Test
    void theHardestRouteIsLongerThanTheDirectOne() {
        // The whole point of "hardest route" as a level-design concept: a braided dungeon
        // should offer a scenic way round. On a perfect maze this would be vacuous, since
        // there is only one route.
        MazeGrid level = DungeonLayoutLab.buildLevel();
        List<Point> direct = MazeMetrics.shortestPath(level, level.start(), level.goal());
        var hardest = com.daedalus.theory.LongestPath.hardestRoute(level);

        assertThat(direct).isNotEmpty();
        assertThat(hardest.path().size()).isGreaterThan(direct.size());
    }
}
