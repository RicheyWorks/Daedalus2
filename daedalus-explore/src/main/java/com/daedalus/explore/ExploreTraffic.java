// SPDX-License-Identifier: MIT

package com.daedalus.explore;

import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.WeightedMazeGrid;
import com.daedalus.model.Point;

/**
 * Walked cells bloom cost — same idea as the well's Jam, without a session.
 */
public final class ExploreTraffic {

    public static final double BUMP = 4.0;

    private ExploreTraffic() {
    }

    public static WeightedMazeGrid wrap(MazeGrid grid) {
        if (grid == null) {
            return null;
        }
        if (grid instanceof WeightedMazeGrid weighted) {
            return weighted;
        }
        return new WeightedMazeGrid(grid);
    }

    public static WeightedMazeGrid occupy(MazeGrid grid, Point cell) {
        WeightedMazeGrid weighted = wrap(grid);
        if (weighted == null || cell == null || !weighted.inBounds(cell)) {
            return weighted;
        }
        weighted.setWeight(cell, weighted.weightOf(cell.row(), cell.col()) + BUMP);
        return weighted;
    }
}
