// SPDX-License-Identifier: MIT

package com.daedalus.model;

public enum TileType {
    WALL    ('#'),
    PASSAGE (' '),
    START   ('S'),
    GOAL    ('G'),
    PLAYER  ('@'),
    PATH    ('.'),
    VISITED ('o'),
    FRONTIER('?');

    private final char glyph;

    TileType(char glyph) {
        this.glyph = glyph;
    }

    public char glyph() { return glyph; }

    public boolean walkable() {
        return this != WALL;
    }
}
