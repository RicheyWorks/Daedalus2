// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.urn;

/**
 * Exact Polya-urn odds: a jar starts with {@code white} white and {@code black} black pearls; each draw is put back
 * with {@code add} more of the same colour. The count of white draws in n is beta-binomial; the next-draw chance after
 * w white of m drawn is (white + add w) / (white + black + add m) (Laplace's rule when 1, 1, 1).
 */
public final class PolyaUrn {

    public static final int MAX_DRAWS = 1_000;

    private final int white;
    private final int black;
    private final int add;

    public PolyaUrn(int white, int black, int add) {
        if (white < 1 || black < 1 || white > 1_000 || black > 1_000) {
            throw new IllegalArgumentException("start with 1..1000 of each colour: " + white + ", " + black);
        }
        if (add < 0 || add > 100) {
            throw new IllegalArgumentException("add must be in [0, 100]: " + add);
        }
        this.white = white;
        this.black = black;
        this.add = add;
    }

    public int white() {
        return white;
    }

    public int black() {
        return black;
    }

    public int add() {
        return add;
    }

    /** P(next draw white | {@code whites} white among {@code drawn} so far). */
    public double nextWhite(int whites, int drawn) {
        checkCounts(whites, drawn);
        return (white + (double) add * whites) / (white + black + (double) add * drawn);
    }

    /** Exact P(k white draws in {@code draws}) for every k, built draw by draw. */
    public double[] whiteCounts(int draws) {
        if (draws < 0 || draws > MAX_DRAWS) {
            throw new IllegalArgumentException("draws must be in [0, " + MAX_DRAWS + "]: " + draws);
        }
        double[] p = new double[draws + 1];
        p[0] = 1.0;
        for (int m = 0; m < draws; m++) {
            double[] next = new double[draws + 1];
            for (int w = 0; w <= m; w++) {
                if (p[w] == 0) {
                    continue;
                }
                double q = nextWhite(w, m);
                next[w + 1] += p[w] * q;
                next[w] += p[w] * (1.0 - q);
            }
            p = next;
        }
        return p;
    }

    /** P(the white share of the jar after {@code draws} lands in [lo, hi]), both inclusive, as fractions. */
    public double shareBetween(int draws, double lo, double hi) {
        if (!(lo >= 0 && hi <= 1 && lo <= hi)) {
            throw new IllegalArgumentException("need 0 <= lo <= hi <= 1: " + lo + ", " + hi);
        }
        double[] p = whiteCounts(draws);
        double total = white + black + (double) add * draws;
        double sum = 0;
        for (int w = 0; w <= draws; w++) {
            double share = (white + (double) add * w) / total;
            if (share >= lo - 1e-12 && share <= hi + 1e-12) {
                sum += p[w];
            }
        }
        return Math.min(1.0, sum);
    }

    /** Expected white share at any time: white / (white + black) (a martingale). */
    public double expectedShare() {
        return white / (double) (white + black);
    }

    private static void checkCounts(int whites, int drawn) {
        if (drawn < 0 || whites < 0 || whites > drawn) {
            throw new IllegalArgumentException("need 0 <= whites <= drawn: " + whites + ", " + drawn);
        }
    }
}
