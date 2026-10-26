// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import com.daedalus.world.BlockCoordinate;

/**
 * A sky ship (ADR-019). Every raised island launches one, named from the island's seed, and it
 * starts moored at that island's pier. {@code berth} is the world cube at the pier tip a
 * passenger steps off onto; a renderer hangs the hull beside it.
 *
 * @param id       stable id, {@code ark-<home slot>}
 * @param homeSlot lane slot of the island that launched it
 * @param slot     lane slot it is moored at now
 * @param berth    the pier-tip cube of the island it is moored at
 */
public record Ark(String id, String name, int homeSlot, int slot, BlockCoordinate berth) {

    public static String idFor(int homeSlot) {
        return "ark-" + homeSlot;
    }
}
