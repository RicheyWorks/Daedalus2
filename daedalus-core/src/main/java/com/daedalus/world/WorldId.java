// SPDX-License-Identifier: MIT

package com.daedalus.world;

/**
 * Opaque world identity. World Zero is the single well-known id {@link #ZERO}.
 */
public record WorldId(String value) {

    /** The one persistent world this slice is building toward. */
    public static final WorldId ZERO = new WorldId("world-zero");

    public WorldId {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException("WorldId value is required");
        }
    }

    @Override
    public String toString() {
        return value;
    }
}
