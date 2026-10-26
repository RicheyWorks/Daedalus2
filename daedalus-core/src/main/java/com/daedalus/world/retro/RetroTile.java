// SPDX-License-Identifier: MIT

package com.daedalus.world.retro;

/**
 * The tiles of the 8-bit realm behind a portal (ADR-052). Each has one character in the realm spec ({@link RetroCodec});
 * the C++ core ({@code DaedalusRealmCore.h}) reads the same characters and draws each tile itself.
 */
public enum RetroTile {
    GRASS('.', true),
    TREE('T', true),
    WATER('~', false),
    HILL('h', true),
    MOUNTAIN('^', false),
    SAND(':', true),
    BRIDGE('=', true),
    SWAMP('%', true),
    COBBLE(',', true),
    STONE('#', false),
    BRICK('b', true),
    DOOR('D', true),
    /** A locked door: which key opens it is in the spec's {@code door} line. */
    LOCKED('L', false),
    /** A chest: what is inside is in the spec's {@code chest} line. */
    CHEST('C', false),
    STAIRS_DOWN('>', true),
    STAIRS_UP('<', true),
    TOWN('V', true),
    CASTLE('K', true),
    CAVE('A', true),
    PORTAL('O', true),
    THRONE('Q', false),
    CARPET('|', true),
    /** A shop counter: talk across it to the keeper behind. */
    COUNTER('-', false),
    FLOOR('_', true),
    WALL('W', false);

    private final char code;
    private final boolean walkable;

    RetroTile(char code, boolean walkable) {
        this.code = code;
        this.walkable = walkable;
    }

    public char code() {
        return code;
    }

    /** True when the party can stand on it (chests, locked doors and counters are walked up to, not onto). */
    public boolean walkable() {
        return walkable;
    }

    public static RetroTile of(char code) {
        for (RetroTile t : values()) {
            if (t.code == code) {
                return t;
            }
        }
        throw new IllegalArgumentException("no realm tile '" + code + "'");
    }
}
