package com.daedalus.routing.server;

public record ServerNode(String id, String region, String type, double latency, double load) {
    public double effectiveCost() { return latency * (1 + load * 2); }
}