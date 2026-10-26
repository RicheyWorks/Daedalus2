// SPDX-License-Identifier: MIT

package com.daedalus.world;

import java.util.Objects;

/**
 * Third programmable world object. Human REST and automation call the same methods.
 * Door and trap stay first; this is {@code portal-zero}.
 */
public final class Portal {

    public static final String ZERO_ID = "portal-zero";
    public static final BlockCoordinate ZERO_AT = new BlockCoordinate(2, 1, 0);

    private final String id;
    private final WorldId worldId;
    private final BlockCoordinate at;
    private PortalState state;

    public Portal(String id, WorldId worldId, BlockCoordinate at, PortalState state) {
        this.id = Objects.requireNonNull(id, "Portal id is required");
        this.worldId = Objects.requireNonNull(worldId, "WorldId is required");
        this.at = Objects.requireNonNull(at, "Portal position is required");
        this.state = Objects.requireNonNull(state, "PortalState is required");
        if (id.isBlank()) {
            throw new IllegalArgumentException("Portal id is required");
        }
    }

    public static Portal zero() {
        return new Portal(ZERO_ID, WorldId.ZERO, ZERO_AT, PortalState.SEALED);
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

    public PortalState state() {
        return state;
    }

    public PortalResult open() {
        if (state == PortalState.OPEN) {
            return PortalResult.ALREADY_OPEN;
        }
        state = PortalState.OPEN;
        return PortalResult.OPENED;
    }

    public PortalResult seal() {
        if (state == PortalState.SEALED) {
            return PortalResult.ALREADY_SEALED;
        }
        state = PortalState.SEALED;
        return PortalResult.SEALED;
    }

    public Portal copy() {
        return new Portal(id, worldId, at, state);
    }
}
