// SPDX-License-Identifier: MIT

package com.daedalus.world;

import java.util.Objects;

/**
 * Second programmable world object. Human REST and automation call the same methods.
 * Door stays {@code door-zero}; this is {@code trap-zero}.
 */
public final class Trap {

    public static final String ZERO_ID = "trap-zero";
    public static final BlockCoordinate ZERO_AT = new BlockCoordinate(1, 1, 0);

    private final String id;
    private final WorldId worldId;
    private final BlockCoordinate at;
    private TrapState state;

    public Trap(String id, WorldId worldId, BlockCoordinate at, TrapState state) {
        this.id = Objects.requireNonNull(id, "Trap id is required");
        this.worldId = Objects.requireNonNull(worldId, "WorldId is required");
        this.at = Objects.requireNonNull(at, "Trap position is required");
        this.state = Objects.requireNonNull(state, "TrapState is required");
        if (id.isBlank()) {
            throw new IllegalArgumentException("Trap id is required");
        }
    }

    public static Trap zero() {
        return new Trap(ZERO_ID, WorldId.ZERO, ZERO_AT, TrapState.DISARMED);
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

    public TrapState state() {
        return state;
    }

    public TrapResult arm() {
        if (state == TrapState.ARMED) {
            return TrapResult.ALREADY_ARMED;
        }
        state = TrapState.ARMED;
        return TrapResult.ARMED;
    }

    public TrapResult disarm() {
        if (state == TrapState.DISARMED) {
            return TrapResult.ALREADY_DISARMED;
        }
        state = TrapState.DISARMED;
        return TrapResult.DISARMED;
    }

    public Trap copy() {
        return new Trap(id, worldId, at, state);
    }
}
