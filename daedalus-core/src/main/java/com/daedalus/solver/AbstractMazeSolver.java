// SPDX-License-Identifier: MIT

package com.daedalus.solver;

import com.daedalus.model.Point;

import java.util.*;

/** Common helpers for solver implementations. */
public abstract class AbstractMazeSolver implements MazeSolver {

    /**
     * Walk an id-indexed parent array back from goal to start, then reverse — the array-based
     * counterpart to {@link #reconstruct(Map, Point, Point)} for solvers that keep their state in
     * {@link GridIndex}-addressed arrays. {@code -1} marks "no parent".
     */
    protected List<Point> reconstruct(int[] parent, int startId, int goalId, GridIndex index) {
        LinkedList<Point> path = new LinkedList<>();
        int cur = goalId;
        while (cur != -1) {
            path.addFirst(index.pointOf(cur));
            if (cur == startId) {
                break;
            }
            cur = parent[cur];
        }
        if (path.isEmpty() || !path.getFirst().equals(index.pointOf(startId))) {
            return Collections.emptyList();
        }
        return path;
    }

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
