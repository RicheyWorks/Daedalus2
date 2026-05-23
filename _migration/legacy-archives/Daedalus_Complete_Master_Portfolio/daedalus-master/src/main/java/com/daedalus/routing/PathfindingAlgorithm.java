package com.daedalus.routing;

import java.util.List;

public interface PathfindingAlgorithm<N> {
    List<N> findPath(Graph<N> graph, N start, N goal);
    default List<N> findPath(Graph<N> graph, N start, N goal, PathStats stats) {
        long startTime = System.nanoTime();
        List<N> path = findPath(graph, start, goal);
        if (stats != null) stats.record(path.size() > 0, System.nanoTime() - startTime);
        return path;
    }
}