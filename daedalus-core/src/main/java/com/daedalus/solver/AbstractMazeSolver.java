// SPDX-License-Identifier: MIT

package com.daedalus.solver;

import com.daedalus.model.Point;

import java.util.*;

/** Common helpers for solver implementations. */
public abstract class AbstractMazeSolver implements MazeSolver {

    /** Walk the parent map back from goal to start, then reverse. */
    protected List<Point> reconstruct(Map<Point, Point> parent, Point start, Point goal) {
        if (!parent.containsKey(goal) && !goal.equals(start)) return Collections.emptyList();
        LinkedList<Point> path = new LinkedList<>();
        Point cur = goal;
        while (cur != null) {
            path.addFirst(cur);
            if (cur.equals(start)) break;
            cur = parent.get(cur);
        }
        if (path.isEmpty() || !path.getFirst().equals(start)) return Collections.emptyList();
        return path;
    }
}
