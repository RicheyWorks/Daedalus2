// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.engine.MazeGenerator;
import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.theory.ComplexityAnalyzer;
import com.daedalus.theory.ComplexityAnalyzer.Measurement;
import com.daedalus.theory.GrowthEstimator;
import com.github.benmanes.caffeine.cache.Cache;
import com.github.benmanes.caffeine.cache.Caffeine;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.function.ToLongFunction;

/**
 * The Complexity Lab (ADR-007 idea 2) — measure a generator's growth instead of asserting it.
 *
 * <p>Every generator in this project carries a complexity claim in its Javadoc ("O(n) time,
 * O(n) auxiliary"). Those claims were reasoned about, never checked against the code as it
 * actually runs. This runs the generator at a sweep of sizes, records the work it really did,
 * fits the points against candidate growth curves, and reports the winner with an R² — so
 * "recursive-backtracker is O(n)" stops being a comment and becomes a measurement anyone can
 * reproduce by hitting an endpoint.
 *
 * <p><b>It measures counters, not the clock.</b> {@link Measurement#elapsedNanos()} exists but
 * is deliberately not fitted: wall-clock on a shared box measures the box, and a JIT warm-up
 * spike would masquerade as super-linear growth. Cell counters are deterministic for a given
 * {@code (generator, size, seed)}, so a fit computed here reproduces exactly anywhere else.
 *
 * <p><b>Bounded, and it does not touch the maze cache.</b> A sweep generates mazes purely to
 * count their construction work; they are thrown away without ever entering
 * {@link MazeGenerationService}'s bounded cache or firing generation events. That is a lesson
 * with scar tissue — the campaign planner leaked 89% of its candidates into that cache before
 * anyone noticed. Sweeps are capped by size and point count, and results are cached per
 * {@code (generator, metric, seed, sizes)} because the inputs fully determine the output.
 *
 * <p><b>One request is several generations.</b> A sweep runs the generator once per size, so a
 * single uncached call costs roughly {@code max-points} generations against a budget that
 * charges it as one. That is deliberate — the cache makes repeats free and the sizes are capped
 * — but an operator tuning {@code max-size} or {@code max-points} upward is raising the cost of
 * a single token, not just the latency.
 */
@Service
public class ComplexityLabService {

    private static final Logger log = LoggerFactory.getLogger(ComplexityLabService.class);

    /** Metrics worth fitting, all deterministic counters from {@code MazeStats}. */
    private static final java.util.Map<String, ToLongFunction<Measurement>> METRICS =
            java.util.Map.of(
                    "cellsVisited", Measurement::cellsVisited,
                    "cellsExplored", Measurement::cellsExplored,
                    "backtrackCount", Measurement::backtrackCount,
                    "maxFrontierSize", Measurement::maxFrontierSize);

    /** One measured point, wall-clock deliberately omitted (see the class note). */
    public record Point(int size, long cells, long value) {}

    /**
     * A generator's measured growth.
     *
     * @param claimed      the growth class the fit selected, as a big-O label
     * @param exponent     the fitted log-log slope: ~1 is linear in cell count, ~2 quadratic
     * @param rSquared     how well the winning curve explains the points; low means "do not
     *                     trust this label", which is reported rather than hidden
     * @param instrumented false when the generator never increments this counter. Most
     *                     generators track only some of them, and fitting a curve through all
     *                     zeros yields a NaN exponent that rounds to a confident-looking
     *                     {@code 0.0}. Saying "not reported" is the honest answer; inventing a
     *                     growth class for a metric nobody measured is not
     * @param note         a plain-language reading of the result, including the caveat when
     *                     the metric is degenerate for this class of algorithm
     */
    public record Fit(String generatorId, String metric, long seed, String claimed,
                      double exponent, double rSquared, int points, boolean instrumented,
                      String note, List<Point> measured) {}

    private final GeneratorRegistry registry;
    private final int maxSize;
    private final int maxPoints;
    private final Cache<String, Fit> fits;

    public ComplexityLabService(GeneratorRegistry registry,
                                @Value("${daedalus.complexity.max-size:96}") int maxSize,
                                @Value("${daedalus.complexity.max-points:6}") int maxPoints,
                                @Value("${daedalus.complexity.max-cached:200}") long maxCached,
                                @Value("${daedalus.complexity.idle-ttl:6h}") Duration idleTtl) {
        this.registry = registry;
        this.maxSize = Math.max(16, maxSize);
        this.maxPoints = Math.max(3, maxPoints); // a curve fit through two points is a line
        this.fits = Caffeine.newBuilder().maximumSize(maxCached).expireAfterAccess(idleTtl).build();
    }

    /** Metric names this lab can fit. */
    public List<String> metrics() {
        return METRICS.keySet().stream().sorted().toList();
    }

    /** The default size sweep, capped so one request cannot run an unbounded benchmark. */
    public int[] defaultSizes() {
        int[] candidates = {16, 24, 32, 48, 64, 96, 128, 192};
        return Arrays.stream(candidates)
                .filter(s -> s <= maxSize)
                .limit(maxPoints)
                .toArray();
    }

    /**
     * Measure and fit one generator.
     *
     * @return {@code null} when the generator or metric is unknown (controller answers 404)
     */
    public Fit fit(String generatorId, String metricName, Long seed) {
        String metric = (metricName == null || metricName.isBlank()) ? "cellsVisited" : metricName;
        ToLongFunction<Measurement> extractor = METRICS.get(metric);
        if (extractor == null) {
            return null;
        }
        // Deliberately NOT caught. This used to be a `catch (RuntimeException)` that returned
        // null, which collapsed "no such generator" into the same empty 404 as "no such metric"
        // — and, being a catch-all, would have swallowed any other runtime failure in the
        // lookup as a 404 too. `require` now throws UnknownAlgorithmException, which the web
        // layer turns into a 404 listing every generator that *is* registered.
        MazeGenerator generator = registry.require(generatorId);
        long useSeed = seed == null ? ComplexityAnalyzer.DEFAULT_SEED : seed;
        int[] sizes = defaultSizes();
        String key = generatorId + "|" + metric + "|" + useSeed + "|" + Arrays.toString(sizes);
        return fits.get(key, k -> measure(generator, metric, extractor, useSeed, sizes));
    }

    private Fit measure(MazeGenerator generator, String metric,
                        ToLongFunction<Measurement> extractor, long seed, int[] sizes) {
        List<Measurement> measurements = new ArrayList<>(sizes.length);
        for (int size : sizes) {
            // ComplexityAnalyzer.measure runs the generator directly and keeps only counters —
            // no cache entry, no MazeGeneratedEvent, nothing observable outside this method.
            measurements.add(ComplexityAnalyzer.measure(generator, size, size, seed));
        }
        var fit = GrowthEstimator.classify(measurements, metric, extractor).get(0);

        List<Point> points = measurements.stream()
                .map(m -> new Point(m.rows(), m.cellCount(), extractor.applyAsLong(m)))
                .toList();
        boolean instrumented = points.stream().anyMatch(pt -> pt.value() > 0);
        String label = instrumented ? fit.growthClass().label() : "not reported";
        log.debug("complexity {} [{}] -> {} (R^2={})", generator.id(), metric, label,
                fit.rSquared());
        return new Fit(generator.id(), metric, seed, label,
                round(fit.exponent()), round(fit.rSquared()), fit.points(), instrumented,
                noteFor(generator.id(), metric, instrumented, points), points);
    }

    /**
     * Say what the numbers mean, including when they mean little.
     *
     * <p>{@code cellsVisited} is the tempting default and the least informative measurement
     * here: a spanning-tree generator carves every cell exactly once, so the metric is
     * identically the cell count and every generator fits O(n) at R²=1.000. That is a real
     * invariant worth checking — it catches a generator that skips or double-counts cells — but
     * it is not a complexity comparison, and presenting it as one would be a chart that always
     * says the same thing. The discriminating metrics are {@code cellsExplored} (work done and
     * thrown away) and {@code maxFrontierSize} (peak memory).
     */
    private static String noteFor(String id, String metric, boolean instrumented,
                                  List<Point> points) {
        if (!instrumented) {
            return id + " does not report " + metric + "; nothing to fit. Try cellsVisited, or "
                    + "cellsExplored and maxFrontierSize on the search-based generators.";
        }
        long cells = points.get(points.size() - 1).cells();
        long value = points.get(points.size() - 1).value();
        if ("cellsVisited".equals(metric)) {
            return "cellsVisited is the cell count by construction for a spanning-tree "
                    + "generator, so O(n) at R^2=1 confirms every cell was carved exactly once "
                    + "rather than revealing anything about cost. cellsExplored and "
                    + "maxFrontierSize are where generators actually differ.";
        }
        if ("cellsExplored".equals(metric) && value > cells * 2) {
            return String.format(java.util.Locale.ROOT,
                    "explored %d cells to carve %d — %.1fx overdraw, the signature of a "
                    + "random-walk generator paying cover-time for a uniform spanning tree.",
                    value, cells, value / (double) cells);
        }
        if ("maxFrontierSize".equals(metric)) {
            return String.format(java.util.Locale.ROOT,
                    "peak frontier %d against %d cells — this is the generator's memory high "
                    + "water mark, and a sub-linear fit means the frontier is a perimeter "
                    + "rather than a wavefront over the whole grid.", value, cells);
        }
        return "fitted over " + points.size() + " sizes; check R^2 before trusting the label.";
    }

    private static double round(double v) {
        return Double.isFinite(v) ? Math.round(v * 1000.0) / 1000.0 : 0.0;
    }
}
