// SPDX-License-Identifier: MIT

package com.daedalus.world.gate;

import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;
import com.daedalus.world.World;

import java.util.Map;
import java.util.TreeMap;

/**
 * Sky gates (ADR-031): portals in the clouds on the other side of the rainbow.
 *
 * <p>Gate {@code g} sits on the gate row, far past the island lane: centre
 * {@code (48 + 96g, 72, −210)}. Looking from the islands (+Z) you see, in order, a rainbow arch at
 * {@code z = −170} that a mount flies through, then a cloud bank holding a crystal ring whose
 * doorway is {@link BlockType#PORTAL}. Below the ring, on the islands' side, is the sky berth where
 * a mount ties up. Every cube is out of reach on foot and outside every island's claim box (which
 * ends at {@code z = −143}).
 *
 * <p>Built all or nothing, like an island: if any cube is taken, nothing is placed.
 */
public final class GateOps {

    public static final int MAX_GATES = 8;
    public static final int GATE_Y = 72;
    public static final int GATE_Z = -210;
    public static final int RING_RADIUS = 7;
    public static final int RAINBOW_Z = -170;
    public static final int RAINBOW_INNER = 17;
    private static final BlockType[] BANDS = {BlockType.RAINBOW_VIOLET, BlockType.RAINBOW_BLUE, BlockType.RAINBOW_GREEN,
        BlockType.RAINBOW_YELLOW, BlockType.RAINBOW_ORANGE, BlockType.RAINBOW_RED};

    /**
     * Where arks see a gate: as lane slot {@code GATE_BASE + g}. Island slots stop at 63, so a voyage,
     * a saved fleet row and a frame can name a gate with the same integer field an island uses.
     */
    public static final int GATE_BASE = 1000;

    private GateOps() {
    }

    public static boolean isGateSlot(int slot) {
        return slot >= GATE_BASE && slot < GATE_BASE + MAX_GATES;
    }

    public static int gateOfSlot(int slot) {
        if (!isGateSlot(slot)) {
            throw new IllegalArgumentException("not a gate slot: " + slot);
        }
        return slot - GATE_BASE;
    }

    public static int slotOfGate(int g) {
        center(g);
        return GATE_BASE + g;
    }

    public static BlockCoordinate center(int g) {
        if (g < 0 || g >= MAX_GATES) {
            throw new IllegalArgumentException("Gate must be 0.." + (MAX_GATES - 1));
        }
        return new BlockCoordinate(48 + 96 * g, GATE_Y, GATE_Z);
    }

    /** Where a mount ties up: on the cloud shelf below the ring, facing the islands. */
    public static BlockCoordinate berth(int g) {
        BlockCoordinate c = center(g);
        return new BlockCoordinate(c.x(), c.y() - RING_RADIUS - 3, c.z() + 12);
    }

    /** Every cube of gate {@code g}, world coordinates. Deterministic: no randomness at all. */
    public static Map<BlockCoordinate, BlockType> plan(int g) {
        BlockCoordinate c = center(g);
        TreeMap<BlockCoordinate, BlockType> out = new TreeMap<>(GateOps::compare);
        // Cloud bank: an ellipsoid around the ring, with the doorway's tunnel left open along Z.
        for (int dx = -16; dx <= 16; dx++) {
            for (int dy = -11; dy <= 10; dy++) {
                for (int dz = -9; dz <= 9; dz++) {
                    double e = (dx * dx) / 256.0 + (dy * dy) / (dy < 0 ? 121.0 : 100.0) + (dz * dz) / 81.0;
                    boolean shell = e <= 1.0 && e >= 0.62;
                    boolean tunnel = dx * dx + dy * dy <= (RING_RADIUS + 1) * (RING_RADIUS + 1);
                    if (shell && !tunnel) {
                        out.put(at(c, dx, dy, dz), BlockType.CLOUD);
                    }
                }
            }
        }
        // The ring (crystal) and its doorway (portal), standing in the XY plane at the bank's centre.
        for (int dx = -RING_RADIUS - 1; dx <= RING_RADIUS + 1; dx++) {
            for (int dy = -RING_RADIUS - 1; dy <= RING_RADIUS + 1; dy++) {
                double r = Math.sqrt(dx * dx + dy * dy);
                if (r <= RING_RADIUS - 0.6) {
                    out.put(at(c, dx, dy, 0), BlockType.PORTAL);
                } else if (r <= RING_RADIUS + 0.9) {
                    out.put(at(c, dx, dy, 0), BlockType.CRYSTAL);
                    out.put(at(c, dx, dy, 1), BlockType.CRYSTAL);
                }
            }
        }
        // The sky berth: a cloud shelf below the ring on the islands' side.
        BlockCoordinate b = berth(g);
        for (int dx = -5; dx <= 5; dx++) {
            for (int dz = -4; dz <= 4; dz++) {
                if (dx * dx / 25.0 + dz * dz / 16.0 <= 1.0) {
                    out.put(new BlockCoordinate(b.x() + dx, b.y() - 1, b.z() + dz), BlockType.CLOUD);
                }
            }
        }
        // The rainbow: six bands in a half circle, standing in the XY plane between the islands and the
        // bank, its feet in two little clouds. Flying through it is the way in.
        int base = c.y() - 14;
        for (int dx = -RAINBOW_INNER - BANDS.length; dx <= RAINBOW_INNER + BANDS.length; dx++) {
            for (int dy = 0; dy <= RAINBOW_INNER + BANDS.length; dy++) {
                double r = Math.sqrt(dx * dx + dy * dy);
                int band = (int) Math.floor(r) - RAINBOW_INNER;
                if (band >= 0 && band < BANDS.length) {
                    out.put(new BlockCoordinate(c.x() + dx, base + dy, RAINBOW_Z), BANDS[band]);
                }
            }
        }
        for (int side : new int[] {-1, 1}) {
            int fx = c.x() + side * (RAINBOW_INNER + BANDS.length / 2);
            for (int dx = -4; dx <= 4; dx++) {
                for (int dy = -3; dy <= 1; dy++) {
                    for (int dz = -3; dz <= 3; dz++) {
                        if (dx * dx / 16.0 + dy * dy / 9.0 + dz * dz / 9.0 <= 1.0
                                && !out.containsKey(new BlockCoordinate(fx + dx, base + dy, RAINBOW_Z + dz))) {
                            out.put(new BlockCoordinate(fx + dx, base + dy, RAINBOW_Z + dz), BlockType.CLOUD);
                        }
                    }
                }
            }
        }
        return out;
    }

    /** True when every cube of gate {@code g} is free in {@code world}. */
    public static boolean fits(World world, int g) {
        for (BlockCoordinate at : plan(g).keySet()) {
            if (world.get(at).solid()) {
                return false;
            }
        }
        return true;
    }

    /** Build gate {@code g}; false (and nothing placed) when any of its cubes is taken. */
    public static boolean build(World world, int g) {
        Map<BlockCoordinate, BlockType> plan = plan(g);
        if (!fits(world, g)) {
            return false;
        }
        plan.forEach(world::place);
        return true;
    }

    private static BlockCoordinate at(BlockCoordinate c, int dx, int dy, int dz) {
        return new BlockCoordinate(c.x() + dx, c.y() + dy, c.z() + dz);
    }

    private static int compare(BlockCoordinate a, BlockCoordinate b) {
        int y = Integer.compare(a.y(), b.y());
        if (y != 0) {
            return y;
        }
        int z = Integer.compare(a.z(), b.z());
        return z != 0 ? z : Integer.compare(a.x(), b.x());
    }
}
