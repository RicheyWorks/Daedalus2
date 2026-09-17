// SPDX-License-Identifier: MIT

package com.daedalus.world;

import java.util.Objects;

/**
 * First programmable world object. Human REST and automation call the same methods.
 */
public final class Door {

    public static final String ZERO_ID = "door-zero";
    public static final BlockCoordinate ZERO_AT = new BlockCoordinate(0, 1, 0);

    private final String id;
    private final WorldId worldId;
    private final BlockCoordinate at;
    private DoorState state;

    public Door(String id, WorldId worldId, BlockCoordinate at, DoorState state) {
        this.id = Objects.requireNonNull(id, "Door id is required");
        this.worldId = Objects.requireNonNull(worldId, "WorldId is required");
        this.at = Objects.requireNonNull(at, "Door position is required");
        this.state = Objects.requireNonNull(state, "DoorState is required");
        if (id.isBlank()) {
            throw new IllegalArgumentException("Door id is required");
        }
    }

    public static Door zero() {
        return new Door(ZERO_ID, WorldId.ZERO, ZERO_AT, DoorState.CLOSED);
    }

    public String id() {
        return id;
    }

    public WorldId worldId() {
        return worldId;
    }

    public BlockCoordinate at() {
        return at;
    }

    public DoorState state() {
        return state;
    }

    public DoorResult open() {
        if (state == DoorState.OPEN) {
            return DoorResult.ALREADY_OPEN;
        }
        state = DoorState.OPEN;
        return DoorResult.OPENED;
    }

    public DoorResult close() {
        if (state == DoorState.CLOSED) {
            return DoorResult.ALREADY_CLOSED;
        }
        state = DoorState.CLOSED;
        return DoorResult.CLOSED;
    }

    public Door copy() {
        return new Door(id, worldId, at, state);
    }
}
