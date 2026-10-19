// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.route;

import com.daedalus.world.odds.OddsRng;
import com.daedalus.world.odds.weather.Sky;
import java.util.List;
import java.util.Objects;

/**
 * A named route an ark can take out of the asteroid belt, as an ordered list of legs, carrying {@code lifeAboard}
 * souls (people, pups, seed-song keepers). Exact expectations are closed form; {@link #sail} draws one voyage.
 */
public record ArkRoute(String name, List<RouteLeg> legs, int lifeAboard) {

    public ArkRoute {
        Objects.requireNonNull(name, "name");
        legs = List.copyOf(Objects.requireNonNull(legs, "legs"));
        if (legs.isEmpty()) {
            throw new IllegalArgumentException("route needs at least one leg: " + name);
        }
        if (lifeAboard < 1) {
            throw new IllegalArgumentException("lifeAboard must be >= 1: " + lifeAboard);
        }
    }

    /** Exact chance that no hazard strikes on any leg (a clean voyage). */
    public double cleanChance(Sky sky) {
        double p = 1.0;
        for (RouteLeg leg : legs) {
            p *= 1.0 - leg.strike(sky);
        }
        return p;
    }

    /** Exact expected life brought home under {@code sky}. */
    public double expectedLifeHome(Sky sky) {
        double keep = lifeAboard;
        for (RouteLeg leg : legs) {
            keep *= leg.expectedKeep(sky);
        }
        return keep;
    }

    /** Sails the route once: one uniform draw per leg, in order. */
    public Voyage sail(Sky sky, OddsRng rng) {
        Objects.requireNonNull(rng, "rng");
        double life = lifeAboard;
        int strikes = 0;
        for (RouteLeg leg : legs) {
            if (rng.nextDouble() < leg.strike(sky)) {
                strikes++;
                life *= 1.0 - leg.hazard().lossFraction();
            }
        }
        return new Voyage(life, strikes);
    }

    /** Outcome of one voyage: life home and number of hazard strikes. */
    public record Voyage(double lifeHome, int strikes) {
        public boolean clean() {
            return strikes == 0;
        }
    }
}
