// SPDX-License-Identifier: MIT

package com.daedalus.world.auto;

import java.util.Set;

/**
 * Harness drive script. A separate list from {@link WorldZeroCapabilities} so
 * a newly registered capability that nobody drives fails the build.
 */
public final class WorldZeroDrive {

    public static final Set<String> DRIVEN = Set.of(
            "world.inspect",
            "chunk.inspect",
            "block.inspect",
            "block.place",
            "block.remove",
            "door.inspect",
            "door.open",
            "door.close",
            "trap.inspect",
            "trap.arm",
            "trap.disarm",
            "portal.inspect",
            "portal.open",
            "portal.seal",
            "npc.inspect",
            "npc.talk",
            "npc.hush",
            "parcel.lease",
            "parcel.grant",
            "stamp.apply");

    private WorldZeroDrive() {
    }
}
