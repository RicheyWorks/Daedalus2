package com.daedalus.routing;

import java.util.List;

/**
 * Generic weighted graph interface for routing problems.
 * Supports both maze grids and real server/network topologies.
 */
public interface Graph<N> {
    List<N> neighbors(N node);
    double cost(N from, N to);
    default double estimate(N from, N to) { return 0.0; }
}