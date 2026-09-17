// SPDX-License-Identifier: MIT

package com.daedalus.world;

import java.util.Objects;

/**
 * One stamped slab inside a world. {@code ownerId} and {@code leaseId} are
 * string account keys — never wallet types. Buy/rent is a later market
 * provider on these strings. NFT binding is a later provider, not this record.
 */
public record Parcel(
        ParcelId id,
        WorldId worldId,
        String ownerId,
        ParcelBounds bounds,
        long version,
        String placeName,
        String leaseId) {

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
        placeName = placeName == null ? "" : placeName.trim();
        leaseId = leaseId == null ? "" : leaseId.trim();
    }

    public Parcel(ParcelId id, WorldId worldId, String ownerId, ParcelBounds bounds, long version) {
        this(id, worldId, ownerId, bounds, version, "", "");
    }

    public Parcel(ParcelId id, WorldId worldId, String ownerId, ParcelBounds bounds,
            long version, String placeName) {
        this(id, worldId, ownerId, bounds, version, placeName, "");
    }
}
