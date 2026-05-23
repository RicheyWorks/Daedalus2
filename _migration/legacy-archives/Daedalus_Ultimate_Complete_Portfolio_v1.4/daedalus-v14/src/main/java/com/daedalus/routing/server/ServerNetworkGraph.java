package com.daedalus.routing.server;

import com.daedalus.routing.Graph;

import java.util.*;

/**
 * Example implementation of a server network as a weighted graph.
 * Used to demonstrate real-world server routing with the new framework.
 */
public class ServerNetworkGraph implements Graph<ServerNode> {

    private final Map<ServerNode, List<ServerNode>> adjacency = new HashMap<>();
    private final Map<String, ServerNode> nodesById = new HashMap<>();

    public void addNode(ServerNode node) {
        nodesById.put(node.id(), node);
        adjacency.putIfAbsent(node, new ArrayList<>());
    }

    public void addConnection(String fromId, String toId, double baseCost) {
        ServerNode from = nodesById.get(fromId);
        ServerNode to = nodesById.get(toId);
        if (from == null || to == null) return;

        adjacency.get(from).add(to);
        // We store cost dynamically via effectiveCost()
    }

    @Override
    public List<ServerNode> neighbors(ServerNode node) {
        return adjacency.getOrDefault(node, Collections.emptyList());
    }

    @Override
    public double cost(ServerNode from, ServerNode to) {
        // Dynamic cost based on current load + base latency
        return to.effectiveCost();
    }

    @Override
    public double estimate(ServerNode from, ServerNode to) {
        // Simple region-based heuristic (can be improved with real geo data)
        if (from.region().equals(to.region())) return 5.0;
        return 50.0;
    }

    public ServerNode getNode(String id) {
        return nodesById.get(id);
    }
}