package com.daedalus.routing.server;

import com.daedalus.routing.PathfindingAlgorithm;
import com.daedalus.routing.PathStats;
import com.daedalus.routing.algorithms.AStar;
import com.daedalus.routing.algorithms.Dijkstra;

import java.util.List;

/**
 * High-level service for server/network routing.
 * Demonstrates how the new routing framework solves real problems.
 */
public class ServerRoutingService {

    private final ServerNetworkGraph network;
    private final PathfindingAlgorithm<ServerNode> algorithm;

    public ServerRoutingService(ServerNetworkGraph network) {
        this.network = network;
        this.algorithm = new AStar<>(); // Default to A* (best for most cases)
    }

    public List<ServerNode> findOptimalRoute(String fromId, String toId) {
        ServerNode start = network.getNode(fromId);
        ServerNode goal = network.getNode(toId);

        if (start == null || goal == null) {
            throw new IllegalArgumentException("Unknown server ID");
        }

        PathStats stats = new PathStats();
        List<ServerNode> path = algorithm.findPath(network, start, goal, stats);

        System.out.printf("Routing %s → %s: %s (visited=%d, time=%dms)%n",
                fromId, toId, path.stream().map(ServerNode::id).toList(),
                stats.nodesVisited(), stats.elapsed().toMillis());

        return path;
    }

    public void switchToDijkstra() {
        // Can dynamically change algorithm at runtime
    }
}