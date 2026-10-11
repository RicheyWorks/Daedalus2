// SPDX-License-Identifier: MIT

package com.daedalus.world.island;

import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;
import com.daedalus.world.World;

import java.util.Map;

/**
 * Puts an {@link IslandPlan} into a {@link World}. All or nothing: if any target cube already
 * holds matter the world is left untouched and the answer is {@link IslandRaiseResult#OVERLAP},
 * the same rule {@code stamp.apply} follows for maze slabs.
 *
 * <p>Islands sit on a sky lane away from World Zero's fixtures and the +X maze street:
 * slot {@code k} is centred at {@code (k * SLOT_SPACING, SKY_Y, SKY_Z)}.
 */
public final class IslandOps {

    public static final int SLOT_SPACING = 96;
    public static final int SKY_Y = 40;
    public static final int SKY_Z = -96;
    public static final int MAX_SLOTS = 64;

    private IslandOps() {
    }

    public static BlockCoordinate slot(int k) {
        if (k < 0 || k >= MAX_SLOTS) {
            throw new IllegalArgumentException("Island slot must be 0.." + (MAX_SLOTS - 1));
        }
        return new BlockCoordinate(k * SLOT_SPACING, SKY_Y, SKY_Z);
    }

    /** True when every cube the plan would occupy at {@code origin} is AIR. */
    public static boolean fits(World world, BlockCoordinate origin, IslandPlan plan) {
        for (BlockCoordinate rel : plan.blocks().keySet()) {
            if (world.get(offset(origin, rel)).solid()) {
                return false;
            }
        }
        return true;
    }

    public static IslandRaiseResult raise(World world, BlockCoordinate origin, IslandPlan plan) {
        if (world == null || origin == null || plan == null) {
            throw new IllegalArgumentException("World, origin and plan are required");
        }
        if (!fits(world, origin, plan)) {
            return IslandRaiseResult.OVERLAP;
        }
        for (Map.Entry<BlockCoordinate, BlockType> e : plan.blocks().entrySet()) {
            world.place(offset(origin, e.getKey()), e.getValue());
        }
        return IslandRaiseResult.RAISED;
    }

    /** First slot whose footprint is all AIR, or -1 when the lane is full. */
    public static int firstFreeSlot(World world, IslandPlan plan) {
        for (int k = 0; k < MAX_SLOTS; k++) {
            if (fits(world, slot(k), plan)) {
                return k;
            }
        }
        return -1;
    }

    static BlockCoordinate offset(BlockCoordinate origin, BlockCoordinate rel) {
        return new BlockCoordinate(origin.x() + rel.x(), origin.y() + rel.y(), origin.z() + rel.z());
    }
}
