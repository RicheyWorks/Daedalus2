package com.daedalus.routing.server;

import com.daedalus.routing.Graph;
import java.util.*;

public class ServerNetworkGraph implements Graph<ServerNode> {
    private final Map<ServerNode, List<ServerNode>> adj = new HashMap<>();
    private final Map<String, ServerNode> byId = new HashMap<>();

    public void addNode(ServerNode n) { byId.put(n.id(), n); adj.putIfAbsent(n, new ArrayList<>()); }
    public void addEdge(String from, String to) {
        ServerNode a = byId.get(from), b = byId.get(to);
        if (a != null && b != null) adj.get(a).add(b);
    }
    @Override public List<ServerNode> neighbors(ServerNode n) { return adj.getOrDefault(n, List.of()); }
    @Override public double cost(ServerNode a, ServerNode b) { return b.effectiveCost(); }
    @Override public double estimate(ServerNode a, ServerNode b) { return a.region().equals(b.region()) ? 5 : 50; }
    public ServerNode get(String id) { return byId.get(id); }
}