// SPDX-License-Identifier: MIT

package com.daedalus.model;

import java.time.Duration;
import java.time.Instant;

/**
 * Runtime metrics for one generation or solve. Fed into {@code theory.ComplexityAnalyzer}
 * for empirical complexity tracking.
 */
public class MazeStats {

    private final Instant startedAt;
    private Instant endedAt;
    private long cellsVisited;
    private long cellsExplored;     // for solvers: nodes popped
    private long pathLength;
    private long backtrackCount;
    private long maxFrontierSize;
    private boolean success;

    public MazeStats() {
        this.startedAt = Instant.now();
    }

    public void finish(boolean success) {
        this.endedAt = Instant.now();
        this.success = success;
    }

    public void incVisited() { cellsVisited++; }
    public void incExplored() { cellsExplored++; }
    public void incBacktrack() { backtrackCount++; }
    public void setPathLength(long len) { this.pathLength = len; }
    public void recordFrontier(long size) {
        if (size > maxFrontierSize) maxFrontierSize = size;
    }

    public Duration elapsed() {
        return Duration.between(startedAt, endedAt == null ? Instant.now() : endedAt);
    }

    public long cellsVisited()       { return cellsVisited; }
    public long cellsExplored()      { return cellsExplored; }
    public long pathLength()         { return pathLength; }
    public long backtrackCount()     { return backtrackCount; }
    public long maxFrontierSize()    { return maxFrontierSize; }
    public boolean success()         { return success; }
    public Instant startedAt()       { return startedAt; }
    public Instant endedAt()         { return endedAt; }

    @Override
    public String toString() {
        return String.format(
                "MazeStats{success=%s, visited=%d, explored=%d, path=%d, backtracks=%d, peakFrontier=%d, elapsed=%dms}",
                success, cellsVisited, cellsExplored, pathLength, backtrackCount, maxFrontierSize, elapsed().toMillis());
    }
}
