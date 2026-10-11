// SPDX-License-Identifier: MIT

package com.daedalus.world.auto;

import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.WorldId;

import java.util.Objects;

/**
 * Where a drive or observe lands. Address is a pipeline step, not a capability.
 */
public record WorldAddress(WorldId worldId, BlockCoordinate at) {

    public WorldAddress {
        Objects.requireNonNull(worldId, "WorldId is required");
        Objects.requireNonNull(at, "BlockCoordinate is required");
    }
}
