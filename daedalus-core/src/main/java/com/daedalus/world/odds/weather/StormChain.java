// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.weather;

import com.daedalus.world.odds.OddsRng;
import java.util.ArrayList;
import java.util.List;

/**
 * Day-to-day weather as a three-state Markov chain (CALM, SQUALL, STORM). Tomorrow depends only on today, by a
 * transition matrix whose rows sum to 1. The island's weather for day {@code d} is a pure function of (island seed,
 * start sky, d): each day draws from its own {@link OddsRng} stream, so every player on an island lives the same storms.
 */
public final class StormChain {

    /** Declared before ODDSREAPER: static fields initialise in order. */
    private static final int N = Sky.values().length;
    private static final double SUM_TOLERANCE = 1e-9;

    /** OddsReaper Island sits on the storm line: storms linger, calm breaks into squalls. */
    public static final StormChain ODDSREAPER = new StormChain(new double[][] {
        {0.70, 0.22, 0.08},
        {0.30, 0.40, 0.30},
        {0.15, 0.35, 0.50}});

    private final double[][] p;

    /** A chain from a 3x3 row-stochastic matrix (rows and columns in {@link Sky} order). The matrix is copied. */
    public StormChain(double[][] transitions) {
        p = copyStochastic(transitions);
    }

    /** Checks a 3x3 matrix whose rows are probability distributions and returns a deep copy. */
    static double[][] copyStochastic(double[][] m) {
        if (m == null || m.length != N) {
            throw new IllegalArgumentException("matrix must be 3x3");
        }
        double[][] out = new double[N][];
        for (int i = 0; i < N; i++) {
            if (m[i] == null || m[i].length != N) {
                throw new IllegalArgumentException("matrix must be 3x3");
            }
            double sum = 0;
            for (double v : m[i]) {
                if (!(v >= 0 && v <= 1)) {
                    throw new IllegalArgumentException("probabilities must be in [0, 1], got " + v);
                }
                sum += v;
            }
            if (Math.abs(sum - 1) > SUM_TOLERANCE) {
                throw new IllegalArgumentException("row " + i + " sums to " + sum + ", not 1");
            }
            out[i] = m[i].clone();
        }
        return out;
    }

    /** P(tomorrow = {@code to} | today = {@code from}). */
    public double p(Sky from, Sky to) {
        return p[from.ordinal()][to.ordinal()];
    }

    /** Tomorrow's sky given today's and a uniform draw {@code u} in [0, 1). */
    public Sky next(Sky today, double u) {
        if (!(u >= 0 && u < 1)) {
            throw new IllegalArgumentException("next needs u in [0, 1), got " + u);
        }
        double[] row = p[today.ordinal()];
        double r = u;
        for (int j = 0; j < N; j++) {
            r -= row[j];
            if (r < 0) {
                return Sky.values()[j];
            }
        }
        return Sky.values()[N - 1];
    }

    /** The island's skies for days 0..days-1, day 0 being {@code start}. */
    public List<Sky> season(long islandSeed, Sky start, int days) {
        if (days < 1) {
            throw new IllegalArgumentException("days must be >= 1, got " + days);
        }
        List<Sky> out = new ArrayList<>(days);
        Sky s = start;
        out.add(s);
        for (int d = 1; d < days; d++) {
            s = next(s, OddsRng.forTrial(islandSeed, d).nextDouble());
            out.add(s);
        }
        return out;
    }

    /** The island's sky on {@code day}. */
    public Sky skyOn(long islandSeed, Sky start, int day) {
        if (day < 0) {
            throw new IllegalArgumentException("day must be >= 0, got " + day);
        }
        return season(islandSeed, start, day + 1).get(day);
    }

    /** One step of the chain applied to a distribution over skies. */
    public double[] step(double[] dist) {
        checkDist(dist);
        double[] out = new double[N];
        for (int i = 0; i < N; i++) {
            for (int j = 0; j < N; j++) {
                out[j] += dist[i] * p[i][j];
            }
        }
        return out;
    }

    /** The distribution {@code steps} days after {@code dist}. */
    public double[] after(double[] dist, int steps) {
        if (steps < 0) {
            throw new IllegalArgumentException("steps must be >= 0, got " + steps);
        }
        double[] d = dist.clone();
        checkDist(d);
        for (int k = 0; k < steps; k++) {
            d = step(d);
        }
        return d;
    }

    /** The long-run share of each sky (the island's climate), by power iteration from an even start. */
    public double[] climate() {
        return after(new double[] {1.0 / 3, 1.0 / 3, 1.0 / 3}, 500);
    }

    /** A distribution that is certain of {@code sky}. */
    public static double[] certain(Sky sky) {
        double[] d = new double[N];
        d[sky.ordinal()] = 1;
        return d;
    }

    static void checkDist(double[] dist) {
        if (dist == null || dist.length != N) {
            throw new IllegalArgumentException("a sky distribution has 3 entries");
        }
        double sum = 0;
        for (double v : dist) {
            if (!(v >= 0)) {
                throw new IllegalArgumentException("sky probabilities must be >= 0");
            }
            sum += v;
        }
        if (Math.abs(sum - 1) > 1e-6) {
            throw new IllegalArgumentException("sky probabilities must sum to 1, got " + sum);
        }
    }
}
