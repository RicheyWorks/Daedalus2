// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.collect;

/**
 * Exact collector odds for {@code fragments} equally likely chart fragments, one per salvage crate. Without a trade-in,
 * P(all seen in c crates) comes from inclusion-exclusion; with the Keeper's trade-in ({@code rate} spare duplicates buy
 * any one missing fragment) a finite-horizon walk over (distinct, duplicates) gives the exact chance.
 */
public final class ChartFragments {

    private final int fragments;

    public ChartFragments(int fragments) {
        if (fragments < 1 || fragments > 30) {
            throw new IllegalArgumentException("fragments must be in [1, 30]: " + fragments);
        }
        this.fragments = fragments;
    }

    public int fragments() {
        return fragments;
    }

    /** Expected crates to see every fragment with no trade-in: n x H(n). */
    public double expectedCrates() {
        double h = 0;
        for (int k = 1; k <= fragments; k++) {
            h += 1.0 / k;
        }
        return fragments * h;
    }

    /** Expected fragments still missing after {@code crates}: n (1 - 1/n)^c. */
    public double expectedMissing(int crates) {
        checkCrates(crates);
        return fragments * Math.pow(1.0 - 1.0 / fragments, crates);
    }

    /** P(every fragment seen in {@code crates}), no trade-in, by inclusion-exclusion. */
    public double completeNoTrade(int crates) {
        checkCrates(crates);
        double p = 0;
        double choose = 1;
        for (int j = 0; j <= fragments; j++) {
            double term = choose * Math.pow(1.0 - j / (double) fragments, crates);
            p += (j % 2 == 0) ? term : -term;
            choose = choose * (fragments - j) / (j + 1);
        }
        return Math.max(0.0, Math.min(1.0, p));
    }

    /**
     * P(a full chart after {@code crates}) when every {@code rate} duplicates trade for one missing fragment; rate 0
     * means no trade-in.
     */
    public double completeWithTradeIn(int crates, int rate) {
        checkCrates(crates);
        if (rate < 0) {
            throw new IllegalArgumentException("rate must be >= 0: " + rate);
        }
        double[][] p = new double[fragments + 1][crates + 1];
        p[0][0] = 1.0;
        for (int t = 0; t < crates; t++) {
            double[][] next = new double[fragments + 1][crates + 1];
            for (int k = 0; k <= fragments; k++) {
                for (int d = 0; d <= t; d++) {
                    double here = p[k][d];
                    if (here == 0) {
                        continue;
                    }
                    if (k < fragments) {
                        next[k + 1][d] += here * (fragments - k) / fragments;
                    }
                    next[k][d + 1] += here * k / fragments;
                }
            }
            p = next;
        }
        double full = 0;
        for (int k = 0; k <= fragments; k++) {
            for (int d = 0; d <= crates; d++) {
                if (k == fragments || (rate > 0 && rate * (fragments - k) <= d)) {
                    full += p[k][d];
                }
            }
        }
        return Math.min(1.0, full);
    }

    /** Fewest crates for at least {@code confidence} chance of a full chart at trade-in {@code rate}. */
    public int smallestCrates(double confidence, int rate, int maxCrates) {
        if (!(confidence > 0 && confidence < 1)) {
            throw new IllegalArgumentException("confidence must be in (0, 1): " + confidence);
        }
        for (int c = 0; c <= maxCrates; c++) {
            if (completeWithTradeIn(c, rate) >= confidence - 1e-12) {
                return c;
            }
        }
        return -1;
    }

    private static void checkCrates(int crates) {
        if (crates < 0 || crates > 2000) {
            throw new IllegalArgumentException("crates must be in [0, 2000]: " + crates);
        }
    }
}
