// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

/**
 * One ark crossing between islands (ADR-020). Times are server epoch milliseconds; a client turns
 * them into a position with {@link #progress(long)} and its own curve between the two berths.
 */
public record Voyage(String arkId, int fromSlot, int toSlot, long departAt, long arriveAt) {

    public Voyage {
        if (arriveAt <= departAt) {
            throw new IllegalArgumentException("A voyage must take time");
        }
    }

    /** 0 at departure, 1 at arrival, clamped. */
    public double progress(long now) {
        if (now <= departAt) {
            return 0;
        }
        if (now >= arriveAt) {
            return 1;
        }
        return (double) (now - departAt) / (arriveAt - departAt);
    }

    public boolean arrived(long now) {
        return now >= arriveAt;
    }
}
