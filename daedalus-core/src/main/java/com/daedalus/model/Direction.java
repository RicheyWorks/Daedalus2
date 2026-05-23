// SPDX-License-Identifier: MIT

package com.daedalus.model;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;

public enum Direction {
    NORTH(-1,  0),
    SOUTH( 1,  0),
    EAST ( 0,  1),
    WEST ( 0, -1);

    private final int dr;
    private final int dc;

    Direction(int dr, int dc) {
        this.dr = dr;
        this.dc = dc;
    }

    public int dr() { return dr; }
    public int dc() { return dc; }

    public Direction opposite() {
        return switch (this) {
            case NORTH -> SOUTH;
            case SOUTH -> NORTH;
            case EAST  -> WEST;
            case WEST  -> EAST;
        };
    }

    public static List<Direction> shuffled(java.util.Random rng) {
        List<Direction> dirs = new java.util.ArrayList<>(Arrays.asList(values()));
        Collections.shuffle(dirs, rng);
        return dirs;
    }
}
