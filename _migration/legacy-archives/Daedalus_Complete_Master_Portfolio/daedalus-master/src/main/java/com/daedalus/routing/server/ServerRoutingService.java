package com.daedalus.routing.server;

import com.daedalus.routing.PathfindingAlgorithm;
import com.daedalus.routing.algorithms.AStar;
import java.util.List;

public class ServerRoutingService {
    private final ServerNetworkGraph net;
    private final PathfindingAlgorithm<ServerNode> algo = new AStar<>();

    public ServerRoutingService(ServerNetworkGraph net) { this.net = net; }

    public List<ServerNode> route(String from, String to) {
        return algo.findPath(net, net.get(from), net.get(to));
    }
}