// SPDX-License-Identifier: MIT

package com.daedalus.world.gate;

import com.daedalus.world.WorldStyle;

/**
 * What carries you up to a sky gate (ADR-031). Gates float in the clouds, past the rainbow, where
 * nobody can walk: every world has its own way to fly there. Only the ark exists yet; the others
 * arrive with their worlds (ADR-032..035).
 */
public enum Mount {
    /** Sky Islands: the arks that already sail between islands (ADR-019/020). */
    ARK(true, "ark"),
    /** Parcels: a helicopter from the parcel's pad. */
    HELICOPTER(false, "helicopter"),
    /** Bricks: a stud-built plane. */
    PLANE(false, "plane"),
    /** Gallery City: a camera drone. */
    DRONE(false, "drone"),
    /** Labyrinth: a great sky-strider bird that knows the way over the walls. */
    SKY_STRIDER(false, "sky-strider");

    private final boolean ready;
    private final String noun;

    Mount(boolean ready, String noun) {
        this.ready = ready;
        this.noun = noun;
    }

    public boolean ready() {
        return ready;
    }

    public String noun() {
        return noun;
    }

    /** The mount a world of this style flies to its gates with. */
    public static Mount of(WorldStyle style) {
        return switch (style) {
            case SKY_ISLANDS -> ARK;
            case PARCELS -> HELICOPTER;
            case BRICKS -> PLANE;
            case GALLERY -> DRONE;
            case LABYRINTH -> SKY_STRIDER;
        };
    }
}
