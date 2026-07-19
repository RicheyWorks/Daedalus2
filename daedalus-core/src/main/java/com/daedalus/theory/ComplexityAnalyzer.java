// SPDX-License-Identifier: MIT

package com.daedalus.theory;

import com.daedalus.engine.MazeGenerator;
import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.model.MazeStats;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

/**
 * Empirical complexity harness for maze generators.
 *
 * <p>Runs each generator at a fixed seed and one or more square sizes, capturing the work it
 * reported through {@link MazeStats} (cells visited, peak frontier, backtracks, …) plus a
 * wall-clock timing. The intent is <em>regression detection</em>, not micro-benchmarking: the
 * serialized report ({@link Report#toCsv()} / {@link Report#toJson()}) carries only the
 * deterministic, seed-stable counters, so it can be committed as a golden file and diffed on
 * every change. Wall-clock time is measured and kept on each {@link Measurement}
 * ({@link Measurement#elapsed()}) for live inspection, but is deliberately left <em>out</em> of
 * the serialized output — timings vary run to run and would make the golden file churn.
 *
 * <p>Not every generator populates every counter (some never touch {@link MazeStats}); those
 * simply report {@code 0}, which is itself stable and therefore fine to lock in. A generator
 * that throws is recorded as {@code success=false} rather than sinking the whole sweep.
 *
 * <p>Determinism rests on the {@link MazeGenerator} contract ("same seed ⇒ same maze") and
 * {@link java.util.Random}'s platform-independent stream, so golden values match across
 * machines and CI.
 */
public final class ComplexityAnalyzer {

    /** Seed used by the zero-arg {@link #analyzeAll()} — matches the codebase's test convention. */
    public static final long DEFAULT_SEED = 42L;

    /** Square edge lengths swept by the zero-arg {@link #analyzeAll()} (all powers of two). */
    private static final int[] DEFAULT_SIZES = {32, 64, 128};

    private final GeneratorRegistry registry;

    public ComplexityAnalyzer(GeneratorRegistry registry) {
        this.registry = registry;
    }

    /** The default sizes swept by {@link #analyzeAll()}, as a fresh copy. */
    public static int[] defaultSizes() {
        return DEFAULT_SIZES.clone();
    }

    /**
     * Measure a single generator once at {@code rows × cols} under {@code seed}. Deterministic
     * in every field except {@link Measurement#elapsedNanos()}.
     */
    public static Measurement measure(MazeGenerator generator, int rows, int cols, long seed) {
        String id = generator.id();
        long cellCount = (long) rows * cols;
        MazeStats stats = new MazeStats();
        long startNanos = System.nanoTime();
        try {
            MazeGrid grid = generator.generate(rows, cols, seed, stats);
            long elapsedNanos = System.nanoTime() - startNanos;
            boolean ok = grid != null && grid.rows() == rows && grid.cols() == cols;
            return toMeasurement(id, rows, cols, cellCount, stats, ok, elapsedNanos);
        } catch (RuntimeException failure) {
            // A misbehaving generator is a data point, not a reason to abort the whole report.
            long elapsedNanos = System.nanoTime() - startNanos;
            return toMeasurement(id, rows, cols, cellCount, stats, false, elapsedNanos);
        }
    }

    /**
     * Sweep every registered generator across {@code sizes} (square) at {@code seed}. Results are
     * sorted by {@code (generatorId, cellCount)} so the report is stable regardless of registry
     * iteration order. Passing no sizes falls back to {@link #defaultSizes()}.
     */
    public Report analyzeAll(long seed, int... sizes) {
        int[] useSizes = (sizes == null || sizes.length == 0) ? DEFAULT_SIZES : sizes;
        List<Measurement> out = new ArrayList<>();
        for (MazeGenerator generator : registry.all()) {
            for (int size : useSizes) {
                out.add(measure(generator, size, size, seed));
            }
        }
        out.sort(Comparator.comparing(Measurement::generatorId).thenComparingLong(Measurement::cellCount));
        return new Report(seed, out);
    }

    /** Sweep every registered generator at {@code seed} across {@link #defaultSizes()}. */
    public Report analyzeAll(long seed) {
        return analyzeAll(seed, DEFAULT_SIZES);
    }

    /** Sweep every registered generator at {@link #DEFAULT_SEED} across {@link #defaultSizes()}. */
    public Report analyzeAll() {
        return analyzeAll(DEFAULT_SEED, DEFAULT_SIZES);
    }

    private static Measurement toMeasurement(String id, int rows, int cols, long cellCount,
                                             MazeStats stats, boolean success, long elapsedNanos) {
        return new Measurement(id, rows, cols, cellCount,
                stats.cellsVisited(), stats.cellsExplored(), stats.backtrackCount(),
                stats.maxFrontierSize(), stats.pathLength(), success, elapsedNanos);
    }

    /**
     * One generator run's outcome. Every field is deterministic for a given
     * {@code (generator, rows, cols, seed)} except {@link #elapsedNanos()}, which is wall-clock
     * and therefore excluded from the serialized report.
     */
    public record Measurement(
            String generatorId,
            int rows,
            int cols,
            long cellCount,
            long cellsVisited,
            long cellsExplored,
            long backtrackCount,
            long maxFrontierSize,
            long pathLength,
            boolean success,
            long elapsedNanos) {

        /** Wall-clock duration of the run (informational — not part of the golden report). */
        public Duration elapsed() {
            return Duration.ofNanos(elapsedNanos);
        }
    }

    /**
     * A full sweep's results. {@link #toCsv()} and {@link #toJson()} emit only the deterministic
     * columns, so either form is safe to commit as a regression fixture.
     */
    public record Report(long seed, List<Measurement> measurements) {

        private static final String CSV_HEADER =
                "generatorId,rows,cols,cellCount,cellsVisited,cellsExplored,"
                        + "backtrackCount,maxFrontierSize,pathLength,success";

        public Report {
            measurements = List.copyOf(measurements);
        }

        /** Deterministic CSV: a header row plus one row per measurement, LF-terminated. */
        public String toCsv() {
            StringBuilder sb = new StringBuilder(CSV_HEADER).append('\n');
            for (Measurement m : measurements) {
                sb.append(m.generatorId()).append(',')
                        .append(m.rows()).append(',')
                        .append(m.cols()).append(',')
                        .append(m.cellCount()).append(',')
                        .append(m.cellsVisited()).append(',')
                        .append(m.cellsExplored()).append(',')
                        .append(m.backtrackCount()).append(',')
                        .append(m.maxFrontierSize()).append(',')
                        .append(m.pathLength()).append(',')
                        .append(m.success()).append('\n');
            }
            return sb.toString();
        }

        /** Deterministic JSON: {@code {seed, measurements:[…]}} over the same columns as the CSV. */
        public String toJson() {
            StringBuilder sb = new StringBuilder();
            sb.append("{\n  \"seed\": ").append(seed).append(",\n  \"measurements\": [");
            for (int i = 0; i < measurements.size(); i++) {
                Measurement m = measurements.get(i);
                sb.append(i == 0 ? "\n" : ",\n");
                sb.append("    {\"generatorId\": \"").append(escapeJson(m.generatorId())).append("\", ")
                        .append("\"rows\": ").append(m.rows()).append(", ")
                        .append("\"cols\": ").append(m.cols()).append(", ")
                        .append("\"cellCount\": ").append(m.cellCount()).append(", ")
                        .append("\"cellsVisited\": ").append(m.cellsVisited()).append(", ")
                        .append("\"cellsExplored\": ").append(m.cellsExplored()).append(", ")
                        .append("\"backtrackCount\": ").append(m.backtrackCount()).append(", ")
                        .append("\"maxFrontierSize\": ").append(m.maxFrontierSize()).append(", ")
                        .append("\"pathLength\": ").append(m.pathLength()).append(", ")
                        .append("\"success\": ").append(m.success()).append('}');
            }
            sb.append(measurements.isEmpty() ? "" : "\n  ").append("]\n}\n");
            return sb.toString();
        }

        /** Write {@link #toCsv()} to {@code path} as UTF-8. */
        public void writeCsv(Path path) throws IOException {
            Files.writeString(path, toCsv(), StandardCharsets.UTF_8);
        }

        /** Write {@link #toJson()} to {@code path} as UTF-8. */
        public void writeJson(Path path) throws IOException {
            Files.writeString(path, toJson(), StandardCharsets.UTF_8);
        }

        /** Write both {@code complexity.csv} and {@code complexity.json} into {@code dir}. */
        public void writeTo(Path dir) throws IOException {
            Files.createDirectories(dir);
            writeCsv(dir.resolve("complexity.csv"));
            writeJson(dir.resolve("complexity.json"));
        }

        private static String escapeJson(String s) {
            StringBuilder b = new StringBuilder(s.length());
            for (int i = 0; i < s.length(); i++) {
                char c = s.charAt(i);
                switch (c) {
                    case '"', '\\' -> b.append('\\').append(c);
                    case '\n' -> b.append("\\n");
                    case '\r' -> b.append("\\r");
                    case '\t' -> b.append("\\t");
                    default -> b.append(c);
                }
            }
            return b.toString();
        }
    }
}
