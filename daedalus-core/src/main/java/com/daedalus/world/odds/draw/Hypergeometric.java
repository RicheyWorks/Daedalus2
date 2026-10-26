// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.draw;

/**
 * Exact draws without replacement: a sack of {@code total} items, {@code good} of them good; draw {@code n}. P(X = k)
 * = C(good, k) C(total - good, n - k) / C(total, n), computed in log space so sacks of a few thousand stay exact to
 * double precision.
 */
public final class Hypergeometric {

    private final int total;
    private final int good;

    public Hypergeometric(int total, int good) {
        if (total < 1 || good < 0 || good > total) {
            throw new IllegalArgumentException("need total >= 1 and 0 <= good <= total");
        }
        this.total = total;
        this.good = good;
    }

    public int total() {
        return total;
    }

    public int good() {
        return good;
    }

    /** P(exactly {@code k} good in a draw of {@code n}). */
    public double pmf(int n, int k) {
        checkDraw(n);
        if (k < Math.max(0, n - (total - good)) || k > Math.min(n, good)) {
            return 0.0;
        }
        return Math.exp(logChoose(good, k) + logChoose(total - good, n - k) - logChoose(total, n));
    }

    /** P(at least {@code m} good in a draw of {@code n}). */
    public double atLeast(int n, int m) {
        checkDraw(n);
        double p = 0;
        for (int k = Math.max(0, m); k <= Math.min(n, good); k++) {
            p += pmf(n, k);
        }
        return Math.min(1.0, p);
    }

    /** Expected good items in a draw of {@code n}: n x good / total. */
    public double mean(int n) {
        checkDraw(n);
        return n * (double) good / total;
    }

    /** Smallest draw with P(at least {@code m} good) >= {@code confidence}, or -1 if even the whole sack fails. */
    public int smallestDraw(int m, double confidence) {
        if (!(confidence > 0 && confidence <= 1)) {
            throw new IllegalArgumentException("confidence must be in (0, 1]: " + confidence);
        }
        for (int n = 0; n <= total; n++) {
            if (atLeast(n, m) >= confidence - 1e-12) {
                return n;
            }
        }
        return -1;
    }

    private void checkDraw(int n) {
        if (n < 0 || n > total) {
            throw new IllegalArgumentException("draw must be in [0, " + total + "]: " + n);
        }
    }

    static double logChoose(int n, int k) {
        if (k < 0 || k > n) {
            return Double.NEGATIVE_INFINITY;
        }
        double s = 0;
        int kk = Math.min(k, n - k);
        for (int i = 1; i <= kk; i++) {
            s += Math.log(n - kk + i) - Math.log(i);
        }
        return s;
    }
}
