// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.SplittableRandom;

/**
 * Ember Lottery (contest gap G273): every strike, the forge's loot drop draws a weighted reward, from common slag to
 * rare starmetal. It must draw in O(1) and replay exactly from a seed.
 *
 * <p>The tool is plain: Vose's alias method over a {@code double[]} of non-negative weights, with O(n) build and O(1)
 * {@link #draw}. {@link #probability} rebuilds each outcome's exact odds from the table. Any project can use it for
 * weighted random choice.
 */
public final class EmberLottery {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_ember_lottery";

    /** How a claim about the odds went. */
    public enum Grade { FAIR, RIGGED }

    private final double[] prob;
    private final int[] alias;

    /** Builds the table; weights must be finite, non-negative and not all zero. */
    public EmberLottery(double[] weights) {
        int n = weights.length;
        double total = 0;
        for (double w : weights) {
            if (!(w >= 0) || Double.isInfinite(w)) {
                throw new IllegalArgumentException("weights must be finite and >= 0");
            }
            total += w;
        }
        if (n == 0 || total <= 0) {
            throw new IllegalArgumentException("need at least one positive weight");
        }
        prob = new double[n];
        alias = new int[n];
        double[] scaled = new double[n];
        int[] small = new int[n];
        int[] large = new int[n];
        int ns = 0;
        int nl = 0;
        for (int i = 0; i < n; i++) {
            scaled[i] = weights[i] * n / total;
            alias[i] = i;
            if (scaled[i] < 1.0) {
                small[ns++] = i;
            } else {
                large[nl++] = i;
            }
        }
        while (ns > 0 && nl > 0) {
            int s = small[--ns];
            int l = large[--nl];
            prob[s] = scaled[s];
            alias[s] = l;
            scaled[l] = scaled[l] + scaled[s] - 1.0;
            if (scaled[l] < 1.0) {
                small[ns++] = l;
            } else {
                large[nl++] = l;
            }
        }
        while (nl > 0) {
            prob[large[--nl]] = 1.0;
        }
        while (ns > 0) {
            prob[small[--ns]] = 1.0;
        }
    }

    /** Number of outcomes. */
    public int size() {
        return prob.length;
    }

    /** One weighted draw using the caller's generator. */
    public int draw(SplittableRandom r) {
        int i = r.nextInt(prob.length);
        return r.nextDouble() < prob[i] ? i : alias[i];
    }

    /** {@code count} draws replayed from {@code seed}. Same seed, same drops. */
    public int[] draws(long seed, int count) {
        if (count < 0) {
            throw new IllegalArgumentException("need count >= 0");
        }
        SplittableRandom r = new SplittableRandom(seed);
        int[] out = new int[count];
        for (int k = 0; k < count; k++) {
            out[k] = draw(r);
        }
        return out;
    }

    /** Exact chance of outcome {@code i}, rebuilt from the alias table. */
    public double probability(int i) {
        if (i < 0 || i >= prob.length) {
            throw new IllegalArgumentException("no outcome " + i);
        }
        double p = prob[i];
        for (int j = 0; j < prob.length; j++) {
            if (alias[j] == i && j != i) {
                p += 1.0 - prob[j];
            }
        }
        return p / prob.length;
    }

    /** FAIR only if the claimed chance of outcome {@code i} is within 1e-9 of the truth. */
    public Grade grade(int i, double claimed) {
        return Math.abs(probability(i) - claimed) <= 1e-9 ? Grade.FAIR : Grade.RIGGED;
    }

    /** The Forgemaster's line for a claim. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case FAIR -> "Forgemaster: you read the embers true. Starmetal stays rare.";
            case RIGGED -> "Forgemaster: those are not the odds the embers keep. Count them again.";
        };
    }
}
