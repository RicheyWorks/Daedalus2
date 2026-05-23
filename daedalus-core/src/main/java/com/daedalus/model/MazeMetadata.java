// SPDX-License-Identifier: MIT

package com.daedalus.model;

import java.time.Instant;
import java.util.UUID;

/** Descriptive header for any maze. Carried alongside the grid for replay + leaderboard purposes. */
public record MazeMetadata(
        UUID id,
        int rows,
        int cols,
        long seed,
        String generatorId,
        Point start,
        Point goal,
        Instant createdAt
) {
    public static MazeMetadata of(int rows, int cols, long seed, String generatorId,
                                   Point start, Point goal) {
        return new MazeMetadata(
                UUID.randomUUID(), rows, cols, seed, generatorId, start, goal, Instant.now());
    }
}
