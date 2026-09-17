// SPDX-License-Identifier: MIT

package com.daedalus.world;

import java.util.Objects;

/**
 * Fourth programmable world object. Human REST and automation call the same methods.
 * Door, trap, and portal stay first; this is {@code npc-zero}.
 */
public final class Npc {

    public static final String ZERO_ID = "npc-zero";
    public static final BlockCoordinate ZERO_AT = new BlockCoordinate(3, 1, 0);

    private final String id;
    private final WorldId worldId;
    private final BlockCoordinate at;
    private NpcState state;

    public Npc(String id, WorldId worldId, BlockCoordinate at, NpcState state) {
        this.id = Objects.requireNonNull(id, "Npc id is required");
        this.worldId = Objects.requireNonNull(worldId, "WorldId is required");
        this.at = Objects.requireNonNull(at, "Npc position is required");
        this.state = Objects.requireNonNull(state, "NpcState is required");
        if (id.isBlank()) {
            throw new IllegalArgumentException("Npc id is required");
        }
    }

    public static Npc zero() {
        return new Npc(ZERO_ID, WorldId.ZERO, ZERO_AT, NpcState.IDLE);
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

    public NpcState state() {
        return state;
    }

    public NpcResult talk() {
        if (state == NpcState.SPEAKING) {
            return NpcResult.ALREADY_SPEAKING;
        }
        state = NpcState.SPEAKING;
        return NpcResult.SPOKE;
    }

    public NpcResult hush() {
        if (state == NpcState.IDLE) {
            return NpcResult.ALREADY_IDLE;
        }
        state = NpcState.IDLE;
        return NpcResult.HUSHED;
    }

    public Npc copy() {
        return new Npc(id, worldId, at, state);
    }
}
