// SPDX-License-Identifier: MIT

package com.daedalus.world;

/**
 * Monotonic world clock. Inspect never advances it; place and remove do.
 */
public record WorldRevision(long value) {

    public static final WorldRevision ZERO = new WorldRevision(0);

    public WorldRevision {
        if (value < 0) {
            throw new IllegalArgumentException("WorldRevision cannot be negative");
        }
    }

    public WorldRevision next() {
        return new WorldRevision(value + 1);
    }
}
