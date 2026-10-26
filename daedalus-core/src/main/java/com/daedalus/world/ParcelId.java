// SPDX-License-Identifier: MIT

package com.daedalus.world;

/**
 * Opaque parcel identity. World Zero's implicit whole-world parcel is not this type;
 * the first stamp allocates {@code parcel-1}.
 */
public record ParcelId(String value) {

    public ParcelId {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException("ParcelId value is required");
        }
    }

    @Override
    public String toString() {
        return value;
    }
}
