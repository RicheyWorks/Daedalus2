// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.route;

import com.daedalus.world.odds.weather.Sky;

/**
 * What can strike an ark on one leg of its route out of the asteroid belt. A strike costs a fraction of the life still
 * aboard: debris holes the hull, a squall washes pens overboard, drift burns supplies. Only squalls care about the sky.
 */
public enum Hazard {
    /** Asteroid debris: rare to dodge in a narrow belt, heavy losses. */
    DEBRIS(0.50),
    /** Storm-lane squall: scales with the G22 sky. */
    SQUALL(0.25),
    /** Becalmed drift: light, slow losses from short rations. */
    DRIFT(0.10);

    private final double lossFraction;

    Hazard(double lossFraction) {
        this.lossFraction = lossFraction;
    }

    /** Fraction of the life aboard lost when this hazard strikes. */
    public double lossFraction() {
        return lossFraction;
    }

    /** Multiplier on the leg's base strike chance under {@code sky}; only squalls change with the weather. */
    public double skyFactor(Sky sky) {
        if (this != SQUALL) {
            return 1.0;
        }
        return switch (sky) {
            case CALM -> 0.5;
            case SQUALL -> 1.0;
            case STORM -> 2.0;
        };
    }
}
