// SPDX-License-Identifier: MIT

package com.daedalus.explore;

import com.daedalus.model.Point;

import java.util.HashSet;
import java.util.Set;

/**
 * ADR-006 memory: stood-on cells plus the four wall tiles that touch them.
 * Unseen tiles stay dark; the goal is not implied until stood on or marked.
 */
public final class ExploreFog {

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
            if (tr == cr && tc == cc) {
                return true;
            }
            if ((tr == cr - 1 && tc == cc)
                    || (tr == cr + 1 && tc == cc)
                    || (tr == cr && tc == cc - 1)
                    || (tr == cr && tc == cc + 1)) {
                return true;
            }
        }
        return false;
    }

    public int memorySize() {
        return stood.size();
    }
}
