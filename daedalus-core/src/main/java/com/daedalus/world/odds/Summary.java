// SPDX-License-Identifier: MIT

package com.daedalus.world.odds;

import java.util.Arrays;
import java.util.Locale;

/** Spread of a sample: mean, sample variance and nearest-rank percentiles. All zero when there are no samples. */
public record Summary(int n, double mean, double variance, double stdDev, double min, double p50, double p90,
                      double p99, double max) {

    public static final Summary EMPTY = new Summary(0, 0, 0, 0, 0, 0, 0, 0, 0);

    /** Summarise {@code count} values from the front of {@code values}. The array is not modified. */
    static Summary of(double[] values, int count) {
        if (count <= 0) {
            return EMPTY;
        }
        double[] v = Arrays.copyOf(values, count);
        Arrays.sort(v);
        double sum = 0;
        for (double x : v) {
            sum += x;
        }
        double mean = sum / count;
        double ss = 0;
        for (double x : v) {
            ss += (x - mean) * (x - mean);
        }
        double variance = count > 1 ? ss / (count - 1) : 0;
        return new Summary(count, mean, variance, Math.sqrt(variance), v[0], rank(v, 0.50), rank(v, 0.90),
                rank(v, 0.99), v[count - 1]);
    }

    /** Nearest-rank percentile of a sorted array. */
    static double rank(double[] sorted, double p) {
        int idx = (int) Math.ceil(p * sorted.length) - 1;
        return sorted[Math.max(0, Math.min(sorted.length - 1, idx))];
    }

    String encode() {
        return String.format(Locale.ROOT, "n=%d mean=%.3f sd=%.3f p50=%.3f p90=%.3f p99=%.3f",
                n, mean, stdDev, p50, p90, p99);
    }
}