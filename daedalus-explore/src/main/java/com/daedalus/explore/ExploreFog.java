// SPDX-License-Identifier: MIT

package com.daedalus.explore;

import com.daedalus.model.Point;

import java.util.HashSet;
import java.util.Set;

/**
 * ADR-006 memory: stood-on cells plus a Chebyshev neighborhood so the
 * enclosing wall posts stay painted. Unseen tiles stay dark; the goal
 * is not implied until stood on or marked.
 */
public final class ExploreFog {

    /** Tiles from a cell center that still count as in-view stone. */
    public static final int REACH = 3;

    private final Set<Point> stood = new HashSet<>();

    public void stand(Point cell) {
        if (cell != null) {
            stood.add(cell);
        }
    }

    public boolean stoodOn(Point cell) {
        return cell != null && stood.contains(cell);
    }

    public boolean tileVisible(int tr, int tc) {
        for (Point cell : stood) {
            int cr = 2 * cell.row() + 1;
            int cc = 2 * cell.col() + 1;
            if (Math.max(Math.abs(tr - cr), Math.abs(tc - cc)) <= REACH) {
                return true;
            }
        }
        return false;
    }

    public int memorySize() {
        return stood.size();
    }
}
