// SPDX-License-Identifier: MIT

package com.daedalus.world.stamp;

import com.daedalus.engine.MazeGrid;
import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.WorldId;

import java.util.Objects;

/**
 * Project an already-built maze into a world slab. Generators are not called from here.
 */
public record StampRequest(
        WorldId worldId,
        BlockCoordinate origin,
        MazeGrid maze,
        int floorY,
        int wallHeight) {

    public StampRequest {
        Objects.requireNonNull(worldId, "WorldId is required");
        Objects.requireNonNull(origin, "Stamp origin is required");
        Objects.requireNonNull(maze, "MazeGrid is required");
        if (origin.y() != floorY) {
            throw new IllegalArgumentException("Stamp origin Y must match floorY");
        }
        if (wallHeight < 1) {
            throw new IllegalArgumentException("wallHeight must be at least 1");
        }
    }
}
