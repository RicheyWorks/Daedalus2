// SPDX-License-Identifier: MIT

package com.daedalus.world.fishing;

import com.daedalus.world.odds.OddsRng;

/**
 * How fast an angler strikes once the float dips: reaction time ~ Normal(mean, sd) seconds, floored at zero. A bite is
 * landed when the strike comes inside the fish's window, so {@link #catchChance} is the normal CDF at the window. The
 * same model drives {@link #sampleReaction}, so simulated and exact odds agree.
 */
public record AnglerSkill(double reactionMean, double reactionSd) {

    /** A first cast at Windmere's pond. */
    public static final AnglerSkill NOVICE = new AnglerSkill(0.55, 0.15);
    /** Someone who has filled half the fish log. */
    public static final AnglerSkill STEADY = new AnglerSkill(0.40, 0.10);
    /** OddsReaper Island's storm fishers. */
    public static final AnglerSkill OLD_HAND = new AnglerSkill(0.28, 0.06);

    public AnglerSkill {
        if (!(reactionMean > 0) || Double.isInfinite(reactionMean)) {
            throw new IllegalArgumentException("reaction mean must be positive seconds, got " + reactionMean);
        }
        if (!(reactionSd >= 0) || Double.isInfinite(reactionSd)) {
            throw new IllegalArgumentException("reaction sd must be >= 0, got " + reactionSd);
        }
    }

    /** Chance a strike lands inside a bite window of {@code windowSeconds}. */
    public double catchChance(double windowSeconds) {
        if (reactionSd == 0) {
            return reactionMean <= windowSeconds ? 1.0 : 0.0;
        }
        return phi((windowSeconds - reactionMean) / reactionSd);
    }

    /** One reaction time, from two uniform draws (Box-Muller), floored at zero. */
    public double sampleReaction(OddsRng rng) {
        double u1 = 1.0 - rng.nextDouble();
        double u2 = rng.nextDouble();
        double z = Math.sqrt(-2.0 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
        return Math.max(0, reactionMean + reactionSd * z);
    }

    /** Standard normal CDF. */
    static double phi(double z) {
        return 0.5 * (1 + erf(z / Math.sqrt(2)));
    }

    /** Error function, Abramowitz and Stegun 7.1.26 (absolute error below 1.5e-7). */
    static double erf(double x) {
        double sign = Math.signum(x);
        double a = Math.abs(x);
        double t = 1 / (1 + 0.3275911 * a);
        double y = 1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592)
                * t * Math.exp(-a * a);
        return sign * y;
    }
}
