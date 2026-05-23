package com.daedalus.routing.algorithms;

import com.daedalus.routing.Graph;
import com.daedalus.routing.PathfindingAlgorithm;
import com.daedalus.routing.PathStats;

import java.util.*;

public class AStar<N> implements PathfindingAlgorithm<N> {
    @Override
    public List<N> findPath(Graph<N> graph, N start, N goal) {
        PriorityQueue<Node<N>> open = new PriorityQueue<>();
        Map<N, N> cameFrom = new HashMap<>();
        Map<N, Double> g = new HashMap<>();
        Map<N, Double> f = new HashMap<>();

        g.put(start, 0.0);
        f.put(start, graph.estimate(start, goal));
        open.add(new Node<>(start, f.get(start)));

        while (!open.isEmpty()) {
            Node<N> cur = open.poll();
            if (cur.node.equals(goal)) return reconstruct(cameFrom, start, goal);

            for (N nei : graph.neighbors(cur.node)) {
                double ng = g.getOrDefault(cur.node, Double.MAX_VALUE) + graph.cost(cur.node, nei);
                if (ng < g.getOrDefault(nei, Double.MAX_VALUE)) {
                    cameFrom.put(nei, cur.node);
                    g.put(nei, ng);
                    f.put(nei, ng + graph.estimate(nei, goal));
                    open.removeIf(n -> n.node.equals(nei));
                    open.add(new Node<>(nei, f.get(nei)));
                }
            }
        }
        return Collections.emptyList();
    }

    private List<N> reconstruct(Map<N, N> cameFrom, N start, N goal) {
        LinkedList<N> path = new LinkedList<>();
        N cur = goal;
        while (cur != null) { path.addFirst(cur); cur = cameFrom.get(cur); }
        return path.getFirst().equals(start) ? path : Collections.emptyList();
    }

    private record Node<N>(N node, double f) implements Comparable<Node<N>> {
        public int compareTo(Node<N> o) { return Double.compare(f, o.f); }
    }
}