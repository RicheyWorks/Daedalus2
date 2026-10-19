// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.weather;

/**
 * Brier scoring for storm forecasts: (p - outcome)^2, lower is better, 0 is perfect, 0.25 is a coin flip. It also runs
 * the Odds Keeper's quest "Read the Glass": make at least {@value #QUEST_FORECASTS} storm calls and keep the mean Brier
 * score at or under {@value #QUEST_BRIER}, and she gives you a pocket storm glass.
 */
public final class ForecastScore {

    public static final int QUEST_FORECASTS = 5;
    public static final double QUEST_BRIER = 0.20;

    private int n;
    private double sum;
    private int storms;

    /** One forecast's Brier score. */
    public static double brier(double p, boolean storm) {
        if (!(p >= 0 && p <= 1)) {
            throw new IllegalArgumentException("forecast probability must be in [0, 1], got " + p);
        }
        double o = storm ? 1 : 0;
        return (p - o) * (p - o);
    }

    /** Scores a forecast of {@code p} for a storm against what happened. Returns that forecast's score. */
    public double add(double p, boolean storm) {
        double b = brier(p, storm);
        n++;
        sum += b;
        if (storm) {
            storms++;
        }
        return b;
    }

    public int count() {
        return n;
    }

    /** Mean Brier score; 0 before any forecast. */
    public double mean() {
        return n == 0 ? 0 : sum / n;
    }

    /**
     * Brier skill against always forecasting {@code climateStorm} (1 = perfect, 0 = no better than the almanac,
     * negative = worse). NaN before any forecast.
     */
    public double skill(double climateStorm) {
        if (n == 0) {
            return Double.NaN;
        }
        double ref = (storms * brier(climateStorm, true) + (n - storms) * brier(climateStorm, false)) / n;
        return ref == 0 ? (mean() == 0 ? 1 : Double.NEGATIVE_INFINITY) : 1 - mean() / ref;
    }

    /** True once "Read the Glass" is passed. */
    public boolean questPassed() {
        return n >= QUEST_FORECASTS && mean() <= QUEST_BRIER;
    }
}
