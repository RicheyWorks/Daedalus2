// SPDX-License-Identifier: MIT

package com.daedalus.world.auto;

import com.daedalus.world.BlockType;
import com.daedalus.world.Door;
import com.daedalus.world.World;

import java.util.Objects;

/**
 * Read-back after a drive. Inspect: taking an observation does not mutate revision.
 */
public record Observation(String worldId, long revision, int x, int y, int z,
                          String blockType, String doorState, String place, String lot,
                          String occupant, String acl) {

    public Observation {
        Objects.requireNonNull(worldId, "worldId is required");
        Objects.requireNonNull(blockType, "blockType is required");
        place = place == null ? "" : place;
        lot = lot == null ? "" : lot;
        occupant = occupant == null ? "" : occupant;
        acl = acl == null ? "" : acl;
    }

    public Observation(String worldId, long revision, int x, int y, int z,
                       String blockType, String doorState, String place, String lot,
                       String occupant) {
        this(worldId, revision, x, y, z, blockType, doorState, place, lot, occupant, "");
    }

    public static Observation take(World world, WorldAddress address) {
        Objects.requireNonNull(world, "World is required");
        Objects.requireNonNull(address, "WorldAddress is required");
        if (!world.id().equals(address.worldId())) {
            throw new IllegalArgumentException("Address is for " + address.worldId()
                    + ", not " + world.id());
        }
        BlockType type = world.get(address.at());
        Door door = world.door();
        return new Observation(
                world.id().value(),
                world.revision().value(),
                address.at().x(),
                address.at().y(),
                address.at().z(),
                type.name(),
                door == null ? null : door.state().name(),
                WorldOps.placeAt(world, address.at()),
                WorldOps.lotAt(world, address.at()),
                WorldOps.occupantAt(world, address.at()),
                WorldOps.aclAt(world, address.at()));
    }
}
