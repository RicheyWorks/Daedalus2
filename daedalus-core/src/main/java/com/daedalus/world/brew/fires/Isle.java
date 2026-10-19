// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.fires;

/** A place on the sea map. A relay (sea stack) may carry a fire but need not be joined. */
public record Isle(String id, double x, double y, boolean relay) {
    /** Wood for a fire link: the distance rounded up. */
    public int woodTo(Isle o) {
        return (int) Math.ceil(Math.hypot(x - o.x, y - o.y) - 1e-9);
    }
}
