package com.daedalus.routing;

import java.util.List;

/**
 * Generic pathfinding algorithm for any graph.
 * This is the core interface that makes the solver system reusable
 * for both mazes and real server/network routing problems.
 */
public interface PathfindingAlgorithm<N> {

    /**
     * Find the optimal (or shortest) path from start to goal.
     *
     * @return ordered list of nodes from start to goal (inclusive).
     *         Empty list if no path exists.
     */
    List<N> findPath(Graph<N> graph, N start, N goal);

    /**
     * Find path with statistics collection.
     */
    default List<N> findPath(Graph<N> graph, N start, N goal, PathStats stats) {
        long startTime = System.nanoTime();
        List<N> path = findPath(graph, start, goal);
        if (stats != null) {
            stats.record(path.size() > 0, System.nanoTime() - startTime);
        }
        return path;
    }
}