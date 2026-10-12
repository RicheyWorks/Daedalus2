// SPDX-License-Identifier: MIT

package com.daedalus.world;

/**
 * Solid-or-empty cubes. AIR is ordinal 0 so a fresh chunk payload reads empty.
 * Maze tiles are not these types — a later stamp projects WALL to STONE.
 *
 * <p><b>Ordinals are the save format.</b> {@link Chunk} stores each cube as its ordinal and
 * {@link WorldStore} writes those bytes to disk, so a constant may only ever be <em>appended</em>.
 * Reordering or removing one silently turns every saved world into different matter. The first
 * five are World Zero's; the rest arrived with island terrain (ADR-018) and keep their place.
 */
public enum BlockType {
    AIR,
    STONE,
    DIRT,
    WOOD,
    GLASS,
    // Island terrain (ADR-018). Appended — see the class note.
    GRASS,
    SAND,
    WATER,
    LOG,
    LEAVES,
    BLOSSOM,
    GRAVEL,
    CRYSTAL,
    CLOUD,
    // Sky gates (ADR-031): a rainbow's bands and the doorway in the clouds. Appended.
    RAINBOW_RED,
    RAINBOW_ORANGE,
    RAINBOW_YELLOW,
    RAINBOW_GREEN,
    RAINBOW_BLUE,
    RAINBOW_VIOLET,
    PORTAL,
    // Parcels worlds (ADR-033): asphalt, the light paving of sidewalks and plazas, a helipad's marking.
    ROAD,
    PAVING,
    HELIPAD,
    // Bricks worlds (ADR-034): the studded baseplate, bright bricks, a spawn pad and the obby's lava.
    BASEPLATE,
    BRICK_RED,
    BRICK_BLUE,
    BRICK_YELLOW,
    BRICK_GREEN,
    BRICK_WHITE,
    SPAWN,
    LAVA,
    // Light (ADR-038): blocks that glow at night. A street lamp's head, neon trim in two colours, a lit window.
    // Renderers draw them unlit and bright, so bloom makes them glow; the realm also hangs a light in each lamp.
    LAMP,
    NEON_PINK,
    NEON_CYAN,
    WINDOW_LIT;

    /** Gives off light: drawn unlit and bright, so a night scene glows. */
    public boolean emissive() {
        return this == LAMP || this == NEON_PINK || this == NEON_CYAN || this == WINDOW_LIT
                || this == CRYSTAL || this == LAVA;
    }

    public boolean solid() {
        return this != AIR;
    }

    /** Light passes through: a renderer must not cull the face of a neighbour behind it. */
    public boolean seeThrough() {
        return this == AIR || this == GLASS || this == WATER || this == CLOUD || this == PORTAL
                || name().startsWith("RAINBOW_");
    }

    /** Every name a client may send, in ordinal order — the error message and the palette. */
    public static String names() {
        StringBuilder out = new StringBuilder();
        for (BlockType t : values()) {
            if (out.length() > 0) {
                out.append(", ");
            }
            out.append(t.name());
        }
        return out.toString();
    }
}
