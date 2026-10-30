// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.rival;

import com.daedalus.world.odds.OddsRng;
import java.util.Arrays;

/**
 * The rival bookmaker on the ark docks: he copies the Odds Keeper's chances, takes his own margin, and gets each line
 * wrong by a seeded error. Posted decimal odds for outcome {@code i} are {@code 1 / (p_i x (1 + margin) x e_i)}, where
 * {@code e_i = exp(u)} with {@code u} drawn uniformly from [-spread, spread]. Pure in (chances, margin, spread,
 * seed).
 */
public final class RivalBook {

    /** Odds are never posted shorter than this (evens is the floor for any book). */
    public static final double MIN_ODDS = 1.01;

    private final double[] odds;

    private RivalBook(double[] odds) {
        this.odds = odds;
    }

    /**
     * Posts the rival's line on a board whose true chances are {@code chances} (must sum to ~1).
     *
     * @param margin the rival's overround, e.g. 0.08 for 8%
     * @param spread max log-error per line, e.g. 0.25
     */
    public static RivalBook post(double[] chances, double margin, double spread, long seed) {
        double[] p = check(chances);
        if (!(margin >= 0 && margin < 1) || !(spread >= 0 && spread < 2)) {
            throw new IllegalArgumentException("margin in [0, 1) and spread in [0, 2) required");
        }
        OddsRng rng = new OddsRng(seed);
        double[] odds = new double[p.length];
        for (int i = 0; i < p.length; i++) {
            double err = Math.exp((rng.nextDouble() * 2 - 1) * spread);
            odds[i] = p[i] == 0 ? 0.0 : Math.max(MIN_ODDS, 1.0 / (p[i] * (1 + margin) * err));
        }
        return new RivalBook(odds);
    }

    /** A book from explicit posted odds (0 = not offered). */
    public static RivalBook of(double... odds) {
        double[] o = odds.clone();
        for (double x : o) {
            if (!(x == 0 || x >= 1) || Double.isInfinite(x)) {
                throw new IllegalArgumentException("odds must be 0 (not offered) or finite >= 1: " + x);
            }
        }
        return new RivalBook(o);
    }

    public int size() {
        return odds.length;
    }

    /** Posted decimal odds on outcome {@code i}; 0 when not offered. */
    public double odds(int i) {
        return odds[i];
    }

    /** All posted odds (copy). */
    public double[] all() {
        return odds.clone();
    }

    /** Overround: sum of 1 / odds over offered lines, minus 1. */
    public double overround() {
        double s = 0;
        for (double o : odds) {
            if (o > 0) {
                s += 1 / o;
            }
        }
        return s - 1;
    }

    static double[] check(double[] chances) {
        if (chances == null || chances.length < 2) {
            throw new IllegalArgumentException("need at least two outcomes");
        }
        double s = 0;
        for (double c : chances) {
            if (!(c >= 0 && c <= 1)) {
                throw new IllegalArgumentException("chance must be in [0, 1]: " + c);
            }
            s += c;
        }
        if (Math.abs(s - 1) > 1e-6) {
            throw new IllegalArgumentException("chances must sum to 1: " + s);
        }
        return Arrays.copyOf(chances, chances.length);
    }
}
