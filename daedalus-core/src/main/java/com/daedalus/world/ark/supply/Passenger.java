// SPDX-License-Identifier: MIT
package com.daedalus.world.ark.supply;

/**
 * A living passenger on the crossing (an individual or a colony) and what it needs per started watch (15 s of sailing):
 * water casks and fodder bales. A seed cache or a microbial culture can need nothing.
 */
public record Passenger(String instanceId, String profile, int waterPerWatch, int fodderPerWatch) {
    public Passenger {
        SupplyRun.key(instanceId, "instanceId");
        SupplyRun.key(profile, "profile");
        if (waterPerWatch < 0 || fodderPerWatch < 0 || waterPerWatch > 50 || fodderPerWatch > 50)
            throw new IllegalArgumentException("rations per watch 0..50");
    }
}
