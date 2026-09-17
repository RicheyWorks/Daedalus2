// SPDX-License-Identifier: MIT

package com.daedalus.world;

/**
 * Five solid-or-empty cubes. AIR is ordinal 0 so a fresh chunk payload reads empty.
 * Maze tiles are not these types — a later stamp projects WALL to STONE.
 */
public enum BlockType {
    AIR,
    STONE,
    DIRT,
    WOOD,
    GLASS;

    public boolean solid() {
        return this != AIR;
    }
}
