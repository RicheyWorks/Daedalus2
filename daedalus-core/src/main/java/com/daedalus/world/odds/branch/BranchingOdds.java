// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.branch;

import java.util.Arrays;

/**
 * Galton-Watson odds for word passed mouth to mouth: each teller passes it on to k new tellers with chance {@code
 * offspring[k]}. Extinction is the smallest root of f(s) = s for the generating function f; the chance the word is dead
 * by generation g is f applied g times to 0. Several first tellers spread independently.
 */
public final class BranchingOdds {

    public static final int MAX_CHILDREN = 64;
    private static final double TOL = 1e-15;
    private static final int MAX_ITER = 5_000_000;

    private final double[] offspring;

    public BranchingOdds(double[] offspring) {
        if (offspring == null || offspring.length < 1 || offspring.length > MAX_CHILDREN + 1) {
            throw new IllegalArgumentException("offspring needs 1.." + (MAX_CHILDREN + 1) + " entries");
        }
        double sum = 0;
        for (double p : offspring) {
            if (!(p >= 0 && p <= 1)) {
                throw new IllegalArgumentException("offspring chances must be in [0, 1]: " + p);
            }
            sum += p;
        }
        if (Math.abs(sum - 1.0) > 1e-9) {
            throw new IllegalArgumentException("offspring chances must sum to 1: " + sum);
        }
        this.offspring = offspring.clone();
    }

    /** Each teller tells {@code mates} mates and each believes and passes it on with chance {@code belief}. */
    public static BranchingOdds binomial(int mates, double belief) {
        if (mates < 0 || mates > MAX_CHILDREN) {
            throw new IllegalArgumentException("mates must be in [0, " + MAX_CHILDREN + "]: " + mates);
        }
        if (!(belief >= 0 && belief <= 1)) {
            throw new IllegalArgumentException("belief must be in [0, 1]: " + belief);
        }
        double[] p = new double[mates + 1];
        double choose = 1;
        double sum = 0;
        for (int k = 0; k <= mates; k++) {
            p[k] = choose * Math.pow(belief, k) * Math.pow(1.0 - belief, mates - k);
            sum += p[k];
            choose = Math.rint(choose * (mates - k) / (k + 1));
        }
        for (int k = 0; k <= mates; k++) {
            p[k] = Math.min(1.0, p[k] / sum);
        }
        return new BranchingOdds(p);
    }

    /** The offspring chances (a copy). */
    public double[] offspring() {
        return Arrays.copyOf(offspring, offspring.length);
    }

    /** Mean new tellers per teller, m. */
    public double mean() {
        double m = 0;
        for (int k = 1; k < offspring.length; k++) {
            m += k * offspring[k];
        }
        return m;
    }

    /** The generating function f(s) = sum p_k s^k (Horner). */
    public double generating(double s) {
        double v = 0;
        for (int k = offspring.length - 1; k >= 0; k--) {
            v = v * s + offspring[k];
        }
        return v;
    }

    /** P(the word from one teller is dead by generation {@code generations}). */
    public double extinctBy(int generations) {
        if (generations < 0) {
            throw new IllegalArgumentException("generations must be >= 0: " + generations);
        }
        double s = 0;
        for (int g = 0; g < generations; g++) {
            s = generating(s);
        }
        return s;
    }

    /** P(the word from one teller eventually dies): smallest fixed point of f in [0, 1]. */
    public double extinction() {
        if (mean() <= 1.0 && offspring[0] > 0) {
            return 1.0;
        }
        double s = 0;
        for (int i = 0; i < MAX_ITER; i++) {
            double next = generating(s);
            if (Math.abs(next - s) < TOL) {
                return next;
            }
            s = next;
        }
        return s;
    }

    /** P(the word lives forever) from {@code seeds} first tellers: 1 - q^seeds. */
    public double survival(int seeds) {
        checkSeeds(seeds);
        return 1.0 - Math.pow(extinction(), seeds);
    }

    /** P(the word is still alive at generation {@code generations}) from {@code seeds} first tellers. */
    public double aliveAt(int generations, int seeds) {
        checkSeeds(seeds);
        return 1.0 - Math.pow(extinctBy(generations), seeds);
    }

    /** Expected total tellers from one first teller (1 / (1 - m) when m &lt; 1, infinite otherwise). */
    public double expectedTotal() {
        double m = mean();
        return m < 1.0 ? 1.0 / (1.0 - m) : Double.POSITIVE_INFINITY;
    }

    /** Fewest first tellers for at least {@code confidence} chance the word lives forever, or -1 if none. */
    public int seedsFor(double confidence, int maxSeeds) {
        if (!(confidence > 0 && confidence < 1)) {
            throw new IllegalArgumentException("confidence must be in (0, 1): " + confidence);
        }
        for (int s = 1; s <= maxSeeds; s++) {
            if (survival(s) >= confidence - 1e-12) {
                return s;
            }
        }
        return -1;
    }

    private static void checkSeeds(int seeds) {
        if (seeds < 1 || seeds > 1000) {
            throw new IllegalArgumentException("seeds must be in [1, 1000]: " + seeds);
        }
    }
}
