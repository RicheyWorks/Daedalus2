// SPDX-License-Identifier: MIT

package com.daedalus.world.gate;

import com.daedalus.world.WorldStyle;

/**
 * What carries you up to a sky gate (ADR-031). Gates float in the clouds, past the rainbow, where
 * nobody can walk: every world has its own way to fly there. The ark, the helicopter, the plane and the
 * drone fly; the sky-strider arrives with the Labyrinth (ADR-036).
 */
public enum Mount {
    /** Sky Islands: the arks that already sail between islands (ADR-019/020). */
    ARK(true, "ark"),
    /** Parcels: the helicopter on the plaza's pad (ADR-033). */
    HELICOPTER(true, "helicopter"),
    /** Bricks: the stud-built plane on the runway (ADR-034). */
    PLANE(true, "plane"),
    /** Gallery City: the camera drone on the Origin's pad (ADR-035). */
    DRONE(true, "drone"),
    /** Labyrinth: a great sky-strider bird that knows the way over the walls. */
    SKY_STRIDER(false, "sky-strider");

    /**
     * The slot a world's own aircraft rests at when it is home: the helicopter's pad (ADR-033), the plane's
     * hangar (ADR-034). Past the islands' 0..63 and the gates' 1000..1007.
     */
    public static final int HOME_SLOT = 2000;

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
