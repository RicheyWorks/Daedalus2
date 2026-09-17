// SPDX-License-Identifier: MIT

package com.daedalus.world;

import java.util.Objects;

/**
 * One stamped slab inside a world. {@code ownerId} is a string account key —
 * never a wallet type. NFT binding is a later provider, not this record.
 */
public record Parcel(
        ParcelId id,
        WorldId worldId,
        String ownerId,
        ParcelBounds bounds,
        long version) {

    public static final String SYSTEM_OWNER = "system";

    public Parcel {
        Objects.requireNonNull(id, "ParcelId is required");
        Objects.requireNonNull(worldId, "WorldId is required");
        Objects.requireNonNull(ownerId, "ownerId is required");
        Objects.requireNonNull(bounds, "ParcelBounds is required");
        if (ownerId.isBlank()) {
            throw new IllegalArgumentException("ownerId is required");
        }
        if (version < 1) {
            throw new IllegalArgumentException("Parcel version must be at least 1");
        }
    }
}
