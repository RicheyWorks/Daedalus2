// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.poisson;

/**
 * Exact odds for sky ferries that reach the dock as a Poisson stream with mean gap {@code meanGap} minutes. Counts in
 * a window are Poisson, the wait from any moment is exponential with the same mean as a gap (memoryless), and the gap a
 * random traveller lands in is length-biased, averaging twice the mean gap (the inspection paradox).
 */
public final class FerryClock {

    private final double meanGap;

    public FerryClock(double meanGap) {
        if (!(meanGap > 0 && meanGap <= 10_000)) {
            throw new IllegalArgumentException("meanGap must be in (0, 10000]: " + meanGap);
        }
        this.meanGap = meanGap;
    }

    public double meanGap() {
        return meanGap;
    }

    /** Ferries per minute, lambda = 1 / mean gap. */
    public double rate() {
        return 1.0 / meanGap;
    }

    /** P(exactly {@code k} ferries in {@code minutes}): (lambda t)^k e^(-lambda t) / k!. */
    public double countChance(int k, double minutes) {
        if (k < 0) {
            throw new IllegalArgumentException("k must be >= 0: " + k);
        }
        checkMinutes(minutes);
        double mu = minutes / meanGap;
        double logP = -mu - logFactorial(k) + (k == 0 ? 0.0 : k * Math.log(mu));
        return mu == 0 ? (k == 0 ? 1.0 : 0.0) : Math.exp(logP);
    }

    /** P(the wait from a random moment exceeds {@code minutes}) = e^(-lambda t). */
    public double waitBeyond(double minutes) {
        checkMinutes(minutes);
        return Math.exp(-minutes / meanGap);
    }

    /** Expected wait from a random moment: the full mean gap (not half). */
    public double expectedWait() {
        return meanGap;
    }

    /** Expected length of the gap a random traveller lands in: E[G^2] / E[G] = 2 x mean gap. */
    public double landedGapMean() {
        return 2.0 * meanGap;
    }

    /** Expected wait if ferries kept a fixed timetable with the same mean gap: half the gap. */
    public double timetableWait() {
        return meanGap / 2.0;
    }

    /** Wait that is exceeded with chance {@code 1 - p}: -mean ln(1 - p). */
    public double waitQuantile(double p) {
        if (!(p >= 0 && p < 1)) {
            throw new IllegalArgumentException("p must be in [0, 1): " + p);
        }
        return -meanGap * Math.log(1.0 - p);
    }

    private static double logFactorial(int k) {
        double s = 0;
        for (int i = 2; i <= k; i++) {
            s += Math.log(i);
        }
        return s;
    }

    private static void checkMinutes(double minutes) {
        if (!(minutes >= 0 && minutes <= 1e7)) {
            throw new IllegalArgumentException("minutes must be in [0, 1e7]: " + minutes);
        }
    }
}
