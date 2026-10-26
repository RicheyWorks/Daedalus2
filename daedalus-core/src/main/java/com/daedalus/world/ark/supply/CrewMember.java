// SPDX-License-Identifier: MIT
package com.daedalus.world.ark.supply;

/**
 * An animal that carries cargo up the gangway: how much it can carry per trip and how many trips it can make before
 * it must rest. Loading never pushes a crew member past its trips (rest is part of the rules, not a penalty).
 */
public record CrewMember(String instanceId, String profile, int carryKg, int maxTrips) {
    public CrewMember {
        SupplyRun.key(instanceId, "instanceId");
        SupplyRun.key(profile, "profile");
        if (carryKg < 1 || carryKg > 500 || maxTrips < 1 || maxTrips > 100)
            throw new IllegalArgumentException("carryKg 1..500, maxTrips 1..100");
    }

    /** Total kilograms this crew member can carry before resting. */
    public int capacityKg() { return carryKg * maxTrips; }
}
