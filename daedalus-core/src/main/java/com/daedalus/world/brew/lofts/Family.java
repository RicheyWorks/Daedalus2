// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.lofts;

/** A visiting family from a far island: on the homestead from day {@code arrive} up to (not including) {@code leave}. */
public record Family(String id, String home, int arrive, int leave) {
    public Family {
        if (leave <= arrive) {
            throw new IllegalArgumentException("a family stays at least one day: " + id);
        }
    }

    /** Whether two stays share a night. A family leaving on a day frees the loft for one arriving that day. */
    public boolean overlaps(Family o) {
        return arrive < o.leave && o.arrive < leave;
    }
}
