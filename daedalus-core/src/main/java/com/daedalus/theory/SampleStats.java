// SPDX-License-Identifier: MIT

package com.daedalus.theory;

import java.util.Arrays;

/**
 * Summary statistics with honest interval estimates, for comparing algorithms over a sample of
 * mazes rather than over a single lucky one.
 *
 * <h3>What the interval means here, and what it does not</h3>
 *
 * <p>Every solver in this project is <b>deterministic</b>: the same maze always produces the same
 * expansion count. So a confidence interval is not describing run-to-run noise — there is none.
 * It describes <em>sampling</em> noise: the mazes are a random draw from the population a given
 * generator produces at a given size, and the interval says where that population's mean work
 * would sit if the whole population were measured. Quote it as "mean work on mazes of this kind",
 * never as "this solver's speed ±".
 *
 * <h3>Why Student's t and not 1.96</h3>
 *
 * <p>A tournament runs tens of mazes, not thousands. At n = 20 the normal quantile understates the
 * interval by about 7%, which is exactly the size of error that turns "these two solvers differ"
 * into a claim the data does not support. The t critical values below are tabulated for two-sided
 * 95% and fall back to the normal quantile past df = 30, where the difference is under 2%.
 *
 * <h3>Skew is reported rather than smoothed over</h3>
 *
 * <p>Some solvers' work distributions are badly skewed — measured, IDA*'s expansion counts across
 * braided mazes have a coefficient of variation above 130%. A mean and its interval are weak
 * summaries of a distribution like that, so {@link Summary} carries the median and the CV
 * alongside, and {@link Summary#skewed()} flags the case where they disagree enough that the mean
 * should not be read alone. The flag is the standard nonparametric skew, {@code (mean - median) /
 * sd} against {@value #SKEW_THRESHOLD}, rather than a threshold chosen to look strict.
 */
public final class SampleStats {

    /** Two-sided 95% Student-t critical values, indexed by degrees of freedom (1..30). */
    private static final double[] T95 = {
        Double.NaN, 12.706, 4.303, 3.182, 2.776, 2.571, 2.447, 2.365, 2.306, 2.262, 2.228,
        2.201, 2.179, 2.160, 2.145, 2.131, 2.120, 2.110, 2.101, 2.093, 2.086,
        2.080, 2.074, 2.069, 2.064, 2.060, 2.056, 2.052, 2.048, 2.045, 2.042,
    };

    private static final double NORMAL_95 = 1.960;

    /** Nonparametric skew above which the mean stops being a fair summary. */
    public static final double SKEW_THRESHOLD = 0.2;

    private SampleStats() {
    }

    /**
     * @param n      sample size
     * @param mean   arithmetic mean
     * @param median the middle value — worth comparing against the mean before trusting it
     * @param sd     sample standard deviation (n-1 denominator)
     * @param cv     coefficient of variation as a percentage; the comparable measure of spread
     * @param low    lower bound of the two-sided 95% interval for the mean
     * @param high   upper bound of the same interval
     * @param skewed the <b>nonparametric skew</b> {@code (mean - median) / sd} exceeds
     *               {@value #SKEW_THRESHOLD} in absolute value — the conventional marker for a
     *               distribution the mean no longer describes well. A named statistic is used
     *               here rather than a hand-picked gap because the first version of this flag
     *               required half a standard deviation, which failed to notice a sample of
     *               {@code {10, 11, 12, 13, 900}}: an outlier 70x the rest inflates sd faster
     *               than it moves the mean away from the median, so the stricter-looking rule
     *               was blind to exactly the shape it was written for.
     */
    public record Summary(int n, double mean, double median, double sd, double cv,
                          double low, double high, boolean skewed) { }

    /**
     * @param meanDifference average of the per-item differences
     * @param low            lower bound of the 95% interval on that difference
     * @param high           upper bound
     * @param distinguishable whether the interval excludes zero — i.e. the difference survives
     *                        its own error bars
     */
    public record Difference(int n, double meanDifference, double low, double high,
                             boolean distinguishable) { }

    /** Summarise a sample. Requires at least two values — one value has no spread to report. */
    public static Summary summarise(double[] values) {
        if (values == null || values.length < 2) {
            throw new IllegalArgumentException(
                    "a summary needs at least 2 values; got "
                            + (values == null ? "null" : values.length));
        }
        int n = values.length;
        double mean = mean(values);
        double sd = standardDeviation(values, mean);
        double halfWidth = critical(n - 1) * sd / Math.sqrt(n);
        double median = median(values);
        boolean skewed = sd > 0 && Math.abs(mean - median) / sd > SKEW_THRESHOLD;
        return new Summary(n, mean, median, sd, sd == 0 ? 0 : 100.0 * sd / Math.abs(mean),
                mean - halfWidth, mean + halfWidth, skewed);
    }

    /**
     * A <b>paired</b> comparison: differences are taken item by item, so anything that makes one
     * maze harder for both solvers cancels out instead of inflating both spreads.
     *
     * <p>Pairing is the right default whenever both series were measured on the same items, but it
     * is not magic — measured on this project's own data it bought nothing (1.0×) for A* against
     * BFS, because BFS's expansion count is very nearly constant and so there is no shared
     * per-maze variation left to cancel. It helps exactly when both series move together.
     */
    public static Difference comparePaired(double[] a, double[] b) {
        if (a == null || b == null || a.length != b.length) {
            throw new IllegalArgumentException("paired comparison needs two samples of equal size");
        }
        double[] differences = new double[a.length];
        for (int i = 0; i < a.length; i++) {
            differences[i] = a[i] - b[i];
        }
        Summary summary = summarise(differences);
        boolean distinguishable = summary.low() > 0 || summary.high() < 0;
        return new Difference(a.length, summary.mean(), summary.low(), summary.high(),
                distinguishable);
    }

    private static double critical(int degreesOfFreedom) {
        return degreesOfFreedom >= 1 && degreesOfFreedom < T95.length
                ? T95[degreesOfFreedom] : NORMAL_95;
    }

    private static double mean(double[] values) {
        double sum = 0;
        for (double v : values) {
            sum += v;
        }
        return sum / values.length;
    }

    private static double standardDeviation(double[] values, double mean) {
        double sum = 0;
        for (double v : values) {
            sum += (v - mean) * (v - mean);
        }
        return Math.sqrt(sum / (values.length - 1));
    }

    private static double median(double[] values) {
        double[] sorted = values.clone();
        Arrays.sort(sorted);
        int mid = sorted.length / 2;
        return sorted.length % 2 == 1 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2.0;
    }
}
