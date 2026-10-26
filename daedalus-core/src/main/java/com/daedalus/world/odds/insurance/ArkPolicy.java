// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.insurance;

import com.daedalus.world.odds.route.ArkRoute;
import com.daedalus.world.odds.weather.Sky;
import java.util.Objects;

/**
 * One ark's voyage cover: the underwriter pays {@code coverPerSoul} storm herbs for every soul lost on the G47
 * {@code route} under {@code sky}. The fair premium is the expected claim; the posted premium adds a loading.
 */
public record ArkPolicy(ArkRoute route, Sky sky, double coverPerSoul) {

    /** The most loading the Keeper allows on any premium. */
    public static final double MAX_LOADING = 0.50;

    public ArkPolicy {
        Objects.requireNonNull(route, "route");
        Objects.requireNonNull(sky, "sky");
        if (!(coverPerSoul > 0) || Double.isInfinite(coverPerSoul)) {
            throw new IllegalArgumentException("coverPerSoul must be finite and > 0: " + coverPerSoul);
        }
    }

    /** Expected herbs paid out: cover x (souls aboard - expected souls home). */
    public double expectedClaim() {
        return coverPerSoul * (route.lifeAboard() - route.expectedLifeHome(sky));
    }

    /** Claim for a voyage that brought {@code lifeHome} souls home. */
    public double claim(double lifeHome) {
        return coverPerSoul * Math.max(0.0, route.lifeAboard() - lifeHome);
    }

    /** Posted premium in whole herbs: ceil(expected claim x (1 + loading)), loading clamped to [0, MAX_LOADING]. */
    public int premium(double loading) {
        double l = Double.isNaN(loading) ? 0 : Math.max(0, Math.min(MAX_LOADING, loading));
        return (int) Math.ceil(expectedClaim() * (1 + l) - 1e-9);
    }
}
