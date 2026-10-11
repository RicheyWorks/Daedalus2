// SPDX-License-Identifier: MIT

package com.daedalus.world.export;

import com.daedalus.world.BlockType;

import java.util.EnumMap;
import java.util.Map;

/**
 * The colour of every cube type, one table for every engine (ADR-032): the web realm, the deed
 * portraits (ADR-027), World Packages and the Unreal plugin all draw a cube the same colour.
 */
public final class BlockColors {

    private static final Map<BlockType, Integer> RGB = new EnumMap<>(BlockType.class);

    static {
        RGB.put(BlockType.STONE, 0x7d7b84);
        RGB.put(BlockType.DIRT, 0x7a5230);
        RGB.put(BlockType.WOOD, 0x9a6b3f);
        RGB.put(BlockType.GLASS, 0xa8d8e8);
        RGB.put(BlockType.GRASS, 0x6cc046);
        RGB.put(BlockType.SAND, 0xe2d08c);
        RGB.put(BlockType.WATER, 0x2f80d8);
        RGB.put(BlockType.LOG, 0x7a5232);
        RGB.put(BlockType.LEAVES, 0x4aa44f);
        RGB.put(BlockType.BLOSSOM, 0xf29bc0);
        RGB.put(BlockType.GRAVEL, 0x9b9387);
        RGB.put(BlockType.CRYSTAL, 0xa070ff);
        RGB.put(BlockType.CLOUD, 0xf4f6fb);
        RGB.put(BlockType.RAINBOW_RED, 0xff4d4d);
        RGB.put(BlockType.RAINBOW_ORANGE, 0xff9a3c);
        RGB.put(BlockType.RAINBOW_YELLOW, 0xffe25a);
        RGB.put(BlockType.RAINBOW_GREEN, 0x5ee07a);
        RGB.put(BlockType.RAINBOW_BLUE, 0x4aa8ff);
        RGB.put(BlockType.RAINBOW_VIOLET, 0xa66bff);
        RGB.put(BlockType.PORTAL, 0xd7b8ff);
    }

    private BlockColors() {
    }

    /** 0xRRGGBB; grey for a type with no colour of its own (AIR is never drawn). */
    public static int rgb(BlockType type) {
        return RGB.getOrDefault(type, 0x888888);
    }

    /** Light passes through and blends: water, glass, the rainbow and the gate's doorway. */
    public static boolean translucent(BlockType type) {
        return type == BlockType.GLASS || type == BlockType.WATER || type == BlockType.PORTAL
                || type.name().startsWith("RAINBOW_");
    }

    /** The realm mesher's per-cube brightness (0.94..1.06), so every engine has the same grain. */
    public static double jitter(int x, int y, int z) {
        int h = x * 374761393 + y * 668265263 + z * 2147483647;
        h = (h ^ (h >>> 13)) * 1274126177;
        return 0.94 + Integer.toUnsignedLong(h ^ (h >>> 16)) % 1000 / 1000.0 * 0.12;
    }
}
