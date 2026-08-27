// SPDX-License-Identifier: MIT

package com.daedalus.explore;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.Point;
import com.daedalus.theory.FacilityPlacement;
import com.daedalus.theory.MazeMetrics;

import java.util.ArrayList;
import java.util.List;

/**
 * Same named locations as {@code DungeonLayoutLab}: entrance, k-center
 * vaults, boss. Daedalus decides where; the story engine decides what.
 */
public final class ExploreMarkers {

    public static final int DEFAULT_VAULTS = 5;

    private ExploreMarkers() {
    }

    public static List<ExploreMarker> plan(MazeGrid grid) {
        return plan(grid, DEFAULT_VAULTS);
    }

    public static List<ExploreMarker> plan(MazeGrid grid, int treasures) {
        if (grid == null || grid.start() == null || grid.goal() == null) {
            return List.of();
        }
        Point entrance = grid.start();
        Point boss = grid.goal();
        int[][] depth = MazeMetrics.distancesFrom(grid, entrance);
        List<ExploreMarker> plan = new ArrayList<>();
        plan.add(new ExploreMarker("entrance", entrance, 0, "ENTRANCE"));
        FacilityPlacement.Placement placement = FacilityPlacement.kCenter(grid, treasures);
        int index = 1;
        for (Point cell : placement.facilities()) {
            if (cell.equals(entrance) || cell.equals(boss)) {
                continue;
            }
            int d = depth[cell.row()][cell.col()];
            plan.add(new ExploreMarker("vault-" + index++, cell, d, "TREASURE"));
        }
        int bossDepth = depth[boss.row()][boss.col()];
        plan.add(new ExploreMarker("boss-chamber", boss, bossDepth, "BOSS"));
        return List.copyOf(plan);
    }
}
