package com.daedalus.routing;

import java.time.Duration;
import java.time.Instant;

/**
 * Statistics for pathfinding runs.
 * Generalizes MazeStats for any graph routing problem.
 */
public class PathStats {

    private final Instant startedAt = Instant.now();
    private Instant endedAt;
    private int nodesVisited;
    private int nodesExplored;
    private boolean success;

    public void record(boolean success, long nanos) {
        this.endedAt = Instant.now();
        this.success = success;
    }

    public void incVisited() { nodesVisited++; }
    public void incExplored() { nodesExplored++; }

    public Duration elapsed() {
        return Duration.between(startedAt, endedAt == null ? Instant.now() : endedAt);
    }

    public int nodesVisited() { return nodesVisited; }
    public int nodesExplored() { return nodesExplored; }
    public boolean success() { return success; }

    @Override
    public String toString() {
        return String.format("PathStats{success=%s, visited=%d, explored=%d, time=%dms}",
                success, nodesVisited, nodesExplored, elapsed().toMillis());
    }
}