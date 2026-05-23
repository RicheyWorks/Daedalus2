package com.daedalus.routing.algorithms;

import com.daedalus.routing.Graph;
import com.daedalus.routing.PathfindingAlgorithm;
import com.daedalus.routing.PathStats;

import java.util.*;

/**
 * A* pathfinding algorithm.
 * Works on any weighted graph. Uses the graph's estimate() method as heuristic.
 */
public class AStar<N> implements PathfindingAlgorithm<N> {

    @Override
    public List<N> findPath(Graph<N> graph, N start, N goal) {
        return findPath(graph, start, goal, null);
    }

    @Override
    public List<N> findPath(Graph<N> graph, N start, N goal, PathStats stats) {
        PriorityQueue<Node<N>> openSet = new PriorityQueue<>();
        Map<N, N> cameFrom = new HashMap<>();
        Map<N, Double> gScore = new HashMap<>();
        Map<N, Double> fScore = new HashMap<>();

        gScore.put(start, 0.0);
        fScore.put(start, graph.estimate(start, goal));
        openSet.add(new Node<>(start, fScore.get(start)));

        while (!openSet.isEmpty()) {
            Node<N> current = openSet.poll();
            if (stats != null) stats.incExplored();

            if (current.node.equals(goal)) {
                return reconstructPath(cameFrom, start, goal);
            }

            for (N neighbor : graph.neighbors(current.node)) {
                double tentativeG = gScore.getOrDefault(current.node, Double.MAX_VALUE) +
                                    graph.cost(current.node, neighbor);

                if (tentativeG < gScore.getOrDefault(neighbor, Double.MAX_VALUE)) {
                    cameFrom.put(neighbor, current.node);
                    gScore.put(neighbor, tentativeG);
                    double f = tentativeG + graph.estimate(neighbor, goal);
                    fScore.put(neighbor, f);

                    openSet.removeIf(n -> n.node.equals(neighbor));
                    openSet.add(new Node<>(neighbor, f));

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

    private record Node<N>(N node, double fScore) implements Comparable<Node<N>> {
        @Override
        public int compareTo(Node<N> other) {
            return Double.compare(this.fScore, other.fScore);
        }
    }
}