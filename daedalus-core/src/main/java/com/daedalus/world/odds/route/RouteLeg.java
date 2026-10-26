// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.route;

import com.daedalus.world.odds.weather.Sky;
import java.util.Objects;

/**
 * One leg of an ark route: a named stretch with one hazard and a base chance that the hazard strikes on an
 * ordinary SQUALL-sky day. The effective chance under a given sky is capped at {@link #MAX_STRIKE}.
 */
public record RouteLeg(String name, Hazard hazard, double baseStrike) {

    /** No leg is ever certain death; the Keeper will not price a sure thing. */
    public static final double MAX_STRIKE = 0.95;

    public RouteLeg {
        Objects.requireNonNull(name, "name");
        Objects.requireNonNull(hazard, "hazard");
        if (!(baseStrike >= 0 && baseStrike <= MAX_STRIKE)) {
            throw new IllegalArgumentException("baseStrike must be in [0, " + MAX_STRIKE + "]: " + baseStrike);
        }
    }

    /** Chance the hazard strikes this leg under {@code sky}. */
    public double strike(Sky sky) {
        return Math.min(MAX_STRIKE, baseStrike * hazard.skyFactor(Objects.requireNonNull(sky, "sky")));
    }

    /** Expected fraction of life kept through this leg under {@code sky}. */
    public double expectedKeep(Sky sky) {
        return 1.0 - strike(sky) * hazard.lossFraction();
    }
}
