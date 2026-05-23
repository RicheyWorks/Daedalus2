package com.daedalus.routing.server;

/**
 * Represents a server, microservice, or network node in a routing graph.
 */
public record ServerNode(
        String id,
        String region,
        String type,           // e.g. "api-gateway", "service", "database", "cache"
        double latency,        // base latency in ms
        double load            // current load factor (0.0 - 1.0)
) {
    public double effectiveCost() {
        return latency * (1.0 + load * 2.0); // penalize high load
    }
}