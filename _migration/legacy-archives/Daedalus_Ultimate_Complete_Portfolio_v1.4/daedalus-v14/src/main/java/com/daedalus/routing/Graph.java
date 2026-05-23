package com.daedalus.routing;

import java.util.List;

/**
 * Generic weighted graph interface.
 * Used for both maze routing and real-world server/network routing.
 */
public interface Graph<N> {

    /** Returns all neighbors of a node. */
    List<N> neighbors(N node);

    /** Returns the cost/weight of the edge from → to. */
    double cost(N from, N to);

    /** Optional heuristic estimate from → to (used by A*). */
    default double estimate(N from, N to) {
        return 0.0;
    }

    /** Whether a direct edge exists. */
    default boolean hasEdge(N from, N to) {
        return neighbors(from).contains(to);
    }
}