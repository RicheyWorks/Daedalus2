// SPDX-License-Identifier: MIT

package com.daedalus.explore;

import com.daedalus.engine.Braider;
import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.Sealer;

/**
 * One living tick without Spring — same primitives as ADR-006 / ADR-008.
 * The host rebuilds {@link ExploreMesh} from the returned snapshot.
 */
public final class ExploreLive {

    public static final double ERODE = 0.35;
    public static final double HARDEN = 0.08;

    private ExploreLive() {
    }

    public static MazeGrid pulse(MazeGrid grid, long seed, boolean harden) {
        if (grid == null) {
            return null;
        }
        MazeGrid next = grid.copy();
        Braider.braid(next, ERODE, seed);
        if (harden) {
            Sealer.seal(next, HARDEN, seed);
        }
        return next;
    }
}
