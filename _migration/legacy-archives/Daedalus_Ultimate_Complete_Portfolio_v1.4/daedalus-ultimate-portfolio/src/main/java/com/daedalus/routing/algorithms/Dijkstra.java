package com.daedalus.routing.algorithms;

import com.daedalus.routing.Graph;
import com.daedalus.routing.PathfindingAlgorithm;
import com.daedalus.routing.PathStats;

import java.util.*;

/**
 * Dijkstra's algorithm (A* with heuristic = 0).
 * Guarantees shortest path in graphs with non-negative weights.
 */
public class Dijkstra<N> implements PathfindingAlgorithm<N> {

    @Override
    public List<N> findPath(Graph<N> graph, N start, N goal) {
        return findPath(graph, start, goal, null);
    }

    @Override
    public List<N> findPath(Graph<N> graph, N start, N goal, PathStats stats) {
        PriorityQueue<Node<N>> openSet = new PriorityQueue<>();
        Map<N, N> cameFrom = new HashMap<>();
        Map<N, Double> dist = new HashMap<>();

        dist.put(start, 0.0);
        openSet.add(new Node<>(start, 0.0));

        while (!openSet.isEmpty()) {
            Node<N> current = openSet.poll();
            if (stats != null) stats.incExplored();

            if (current.node.equals(goal)) {
                return reconstructPath(cameFrom, start, goal);
            }

            for (N neighbor : graph.neighbors(current.node)) {
                double alt = dist.getOrDefault(current.node, Double.MAX_VALUE) +
                             graph.cost(current.node, neighbor);

                if (alt < dist.getOrDefault(neighbor, Double.MAX_VALUE)) {
                    cameFrom.put(neighbor, current.node);
                    dist.put(neighbor, alt);
                    openSet.removeIf(n -> n.node.equals(neighbor));
                    openSet.add(new Node<>(neighbor, alt));
                    if (stats != null) stats.incVisited();
                }
            }
        }
        return Collections.emptyList();
    }

    private List<N> reconstructPath(Map<N, N> cameFrom, N start, N goal) {
        LinkedList<N> path = new LinkedList<>();
        N current = goal;
        while (current != null) {
            path.addFirst(current);
            current = cameFrom.get(current);
        }
        return path.getFirst().equals(start) ? path : Collections.emptyList();
    }

    private record Node<N>(N node, double distance) implements Comparable<Node<N>> {
        @Override
        public int compareTo(Node<N> other) {
            return Double.compare(this.distance, other.distance);
        }
    }
}