// SPDX-License-Identifier: MIT

package com.daedalus.theory;

import com.daedalus.theory.ComplexityAnalyzer.Measurement;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.function.DoubleUnaryOperator;
import java.util.function.ToLongFunction;

/**
 * Turns the raw counts a {@link ComplexityAnalyzer} sweep produces into an <em>empirical</em>
 * growth label per generator — CLRS Ch. 3 (growth of functions), applied to real measurements.
 *
 * <p>For each generator it takes the chosen metric (default: cells visited) sampled at several
 * grid sizes {@code n = cellCount} and does two independent things:
 * <ol>
 *   <li><b>Model selection.</b> Fit the points against each candidate {@link GrowthClass} —
 *       {@code O(1)}, {@code O(log n)}, {@code O(sqrt n)}, {@code O(n)}, {@code O(n log n)},
 *       {@code O(n^2)} — by least squares through the origin ({@code w ≈ c·f(n)}), and pick the
 *       class with the highest coefficient of determination (R²). A single scale constant is fit
 *       per class, so the comparison is purely about <em>shape</em>.</li>
 *   <li><b>Empirical exponent.</b> The slope of {@code ln(w)} against {@code ln(n)} — the
 *       power-law exponent — reported alongside as corroborating evidence (≈1 linear, ≈2
 *       quadratic, …).</li>
 * </ol>
 *
 * <p><b>Caveat — high-variance randomized algorithms.</b> A class label fitted to a
 * <em>single-seed</em> series can be unreliable when the algorithm itself is highly variable. Fitting
 * the random-walk generators this way produced labels that swung between {@code O(n)} and
 * {@code O(n^2)} from one seed to the next (and occasionally {@code UNKNOWN}), even though their
 * true behaviour is stable and clearly separated once averaged. The exponent is steadier than the
 * label, but neither is trustworthy from one sample. Average the metric over several seeds before
 * fitting when the algorithm is randomized — see {@code RandomWalkCoverTimeTest}.
 *
 * <p>Deterministic: the inputs are the seed-stable counters from {@link ComplexityAnalyzer}, and
 * the arithmetic is ordinary floating point, so a given sweep always yields the same labels.
 * Metrics that stay at zero (generators that never touch {@code MazeStats}) or fewer than two
 * distinct sizes yield {@link GrowthClass#UNKNOWN} rather than a fabricated class.
 */
public final class GrowthEstimator {

    /** Below this best-fit R², the data isn't cleanly any single class — report UNKNOWN. */
    private static final double MIN_R2 = 0.90;

    private GrowthEstimator() {
    }

    /** Candidate empirical growth classes and the shape each fits against. */
    public enum GrowthClass {
        CONSTANT("O(1)", n -> 1.0),
        LOG_N("O(log n)", Math::log),
        SQRT_N("O(sqrt n)", Math::sqrt),
        LINEAR("O(n)", n -> n),
        N_LOG_N("O(n log n)", n -> n * Math.log(n)),
        QUADRATIC("O(n^2)", n -> n * n),
        UNKNOWN("?", n -> Double.NaN);

        private final String label;
        private final DoubleUnaryOperator model;

        GrowthClass(String label, DoubleUnaryOperator model) {
            this.label = label;
            this.model = model;
        }

        /** Big-O style label, e.g. {@code "O(n log n)"}. */
        public String label() {
            return label;
        }

        double shape(double n) {
            return model.applyAsDouble(n);
        }

        /** The classes we actually fit against (everything except the UNKNOWN sentinel). */
        static GrowthClass[] fittable() {
            return new GrowthClass[] {CONSTANT, LOG_N, SQRT_N, LINEAR, N_LOG_N, QUADRATIC};
        }
    }

    /** One generator's empirical growth verdict for a given metric. */
    public record GrowthFit(String generatorId, String metric, GrowthClass growthClass,
                            double exponent, double rSquared, int points) {

        @Override
        public String toString() {
            if (growthClass == GrowthClass.UNKNOWN) {
                return String.format(Locale.ROOT, "%s [%s]: ? (insufficient data, %d pts)",
                        generatorId, metric, points);
            }
            return String.format(Locale.ROOT, "%s [%s]: %s (exponent=%.2f, R^2=%.3f, %d pts)",
                    generatorId, metric, growthClass.label(), exponent, rSquared, points);
        }
    }

    /**
     * Classify every generator in {@code measurements} by {@code cellsVisited} — the usual
     * "work done" proxy.
     */
    public static List<GrowthFit> classifyVisited(List<Measurement> measurements) {
        return classify(measurements, "cellsVisited", Measurement::cellsVisited);
    }

    /**
     * Classify every generator in {@code measurements} by an arbitrary metric. Measurements are
     * grouped by {@code generatorId} (encounter order preserved), and each group is fit
     * independently.
     */
    public static List<GrowthFit> classify(List<Measurement> measurements, String metricName,
                                           ToLongFunction<Measurement> metric) {
        Map<String, List<Measurement>> byGenerator = new LinkedHashMap<>();
        for (Measurement m : measurements) {
            byGenerator.computeIfAbsent(m.generatorId(), key -> new ArrayList<>()).add(m);
        }
        List<GrowthFit> fits = new ArrayList<>(byGenerator.size());
        for (Map.Entry<String, List<Measurement>> entry : byGenerator.entrySet()) {
            fits.add(fit(entry.getKey(), metricName, entry.getValue(), metric));
        }
        return fits;
    }

    /** Fit one generator's points. Package-visible so it can be unit-tested directly. */
    static GrowthFit fit(String generatorId, String metricName, List<Measurement> points,
                         ToLongFunction<Measurement> metric) {
        int k = points.size();
        double[] ns = new double[k];
        double[] ws = new double[k];
        for (int i = 0; i < k; i++) {
            ns[i] = points.get(i).cellCount();
            ws[i] = metric.applyAsLong(points.get(i));
        }

        if (k < 2 || distinctCount(ns) < 2 || allZero(ws)) {
            return new GrowthFit(generatorId, metricName, GrowthClass.UNKNOWN, Double.NaN, Double.NaN, k);
        }

        double meanW = mean(ws);
        double ssTot = 0.0;
        for (double w : ws) {
            ssTot += (w - meanW) * (w - meanW);
        }
        double exponent = logLogSlope(ns, ws);

        // All work values identical (and non-zero, since not allZero) — that is O(1) exactly.
        if (ssTot == 0.0) {
            return new GrowthFit(generatorId, metricName, GrowthClass.CONSTANT, exponent, 1.0, k);
        }

        GrowthClass best = GrowthClass.UNKNOWN;
        double bestR2 = Double.NEGATIVE_INFINITY;
        for (GrowthClass candidate : GrowthClass.fittable()) {
            double r2 = rSquaredThroughOrigin(ns, ws, meanW, ssTot, candidate);
            if (r2 > bestR2) {
                bestR2 = r2;
                best = candidate;
            }
        }

        if (bestR2 < MIN_R2) {
            return new GrowthFit(generatorId, metricName, GrowthClass.UNKNOWN, exponent, bestR2, k);
        }
        return new GrowthFit(generatorId, metricName, best, exponent, bestR2, k);
    }

    /** Render a list of fits as one line each, for logging or a report footer. */
    public static String toTable(List<GrowthFit> fits) {
        StringBuilder sb = new StringBuilder();
        for (GrowthFit fit : fits) {
            sb.append(fit).append('\n');
        }
        return sb.toString();
    }

    /**
     * R² of the best-scale fit {@code w ≈ c·shape(n)}. The constant {@code c} is chosen by least
     * squares through the origin ({@code c = Σ f·w / Σ f²}), then R² is measured against the mean
     * of {@code w} in the usual way.
     */
    private static double rSquaredThroughOrigin(double[] ns, double[] ws, double meanW, double ssTot,
                                                GrowthClass candidate) {
        double sumFw = 0.0;
        double sumFf = 0.0;
        for (int i = 0; i < ns.length; i++) {
            double f = candidate.shape(ns[i]);
            sumFw += f * ws[i];
            sumFf += f * f;
        }
        if (sumFf == 0.0) {
            return Double.NEGATIVE_INFINITY;
        }
        double c = sumFw / sumFf;
        double ssRes = 0.0;
        for (int i = 0; i < ns.length; i++) {
            double predicted = c * candidate.shape(ns[i]);
            double residual = ws[i] - predicted;
            ssRes += residual * residual;
        }
        return 1.0 - ssRes / ssTot;
    }

    /** Slope of ln(w) vs ln(n) over points with positive n and w — the power-law exponent. */
    private static double logLogSlope(double[] ns, double[] ws) {
        double sumX = 0.0;
        double sumY = 0.0;
        int used = 0;
        for (int i = 0; i < ns.length; i++) {
            if (ns[i] > 0.0 && ws[i] > 0.0) {
                sumX += Math.log(ns[i]);
                sumY += Math.log(ws[i]);
                used++;
            }
        }
        if (used < 2) {
            return Double.NaN;
        }
        double meanX = sumX / used;
        double meanY = sumY / used;
        double cov = 0.0;
        double varX = 0.0;
        for (int i = 0; i < ns.length; i++) {
            if (ns[i] > 0.0 && ws[i] > 0.0) {
                double dx = Math.log(ns[i]) - meanX;
                cov += dx * (Math.log(ws[i]) - meanY);
                varX += dx * dx;
            }
        }
        return varX == 0.0 ? Double.NaN : cov / varX;
    }

    private static double mean(double[] xs) {
        double sum = 0.0;
        for (double x : xs) {
            sum += x;
        }
        return sum / xs.length;
    }

    private static boolean allZero(double[] xs) {
        for (double x : xs) {
            if (x != 0.0) {
                return false;
            }
        }
        return true;
    }

    private static long distinctCount(double[] xs) {
        return java.util.Arrays.stream(xs).distinct().count();
    }
}
