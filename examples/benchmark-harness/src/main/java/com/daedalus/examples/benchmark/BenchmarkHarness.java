// SPDX-License-Identifier: MIT

package com.daedalus.examples.benchmark;

import com.daedalus.engine.MazeGenerator;
import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.*;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.solver.MazeSolver;
import com.daedalus.solver.solvers.*;
import com.daedalus.theory.MazeMetrics;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;

/**
 * Times every generator and solver across grid sizes and seeds, and writes a CSV.
 *
 * <h3>Read the numbers with the environment attached</h3>
 *
 * <p>This harness deliberately records the JVM, OS, CPU count and date alongside every run,
 * because a timing without its machine is not a measurement — it is an anecdote. Absolute
 * milliseconds from one laptop say nothing about another, and on a shared or virtualised host
 * they barely say anything about themselves: repeated runs of identical code during this
 * project's own optimisation work varied by more than 2× on a loaded sandbox.
 *
 * <p>So the column worth acting on is <b>relative</b> cost between algorithms measured in the
 * same run, not the absolute figure. A committed CSV is a record of one machine on one day,
 * not a specification, and it should never become an assertion in CI — a timing test on a
 * shared runner fails for reasons that have nothing to do with the code.
 *
 * <h3>Methodology</h3>
 *
 * <ul>
 *   <li>Each algorithm gets untimed warm-up iterations before any measurement, so the figures
 *       are JIT-compiled steady state rather than interpreter time.</li>
 *   <li>Every timing is the <b>median</b> of its repetitions, not the mean — a single GC pause
 *       or scheduler preemption skews a mean and leaves the median alone.</li>
 *   <li>Solvers run against a maze with start and goal placed at the diameter extremes, so
 *       every solver faces the same, maximally hard query rather than a lucky short one.</li>
 *   <li>Seeds are fixed, so the *work* is identical run to run and only the clock varies.</li>
 * </ul>
 */
public final class BenchmarkHarness {

    private static final int WARMUP = 3;
    private static final int REPETITIONS = 5;

    /**
     * Per-algorithm wall-clock ceiling. Not a tuning knob — a correctness property of the
     * harness. The spread between the fastest and slowest algorithms here is enormous: IDA*
     * costs roughly <b>300× BFS</b> on the same maze, because iterative deepening re-searches
     * from scratch under each larger f-bound. Warming up and repeating that five times at 200²
     * does not produce a better number, it produces a run nobody waits for. An algorithm that
     * blows the budget is measured once and flagged, so a slow entry degrades the precision of
     * its own row instead of the usability of the whole sweep.
     */
    private static final long BUDGET_MILLIS = 2_000;

    private BenchmarkHarness() {
    }

    /**
     * One measured cell of the result table.
     *
     * @param budgeted {@code true} when the algorithm exceeded {@link #BUDGET_MILLIS} on its
     *        first sweep and was therefore measured once rather than repeated — the figure is
     *        a single sample, so treat it as an order of magnitude, not a measurement
     */
    public record Row(String kind, String id, int size, double medianMillis, long work,
                      boolean budgeted) {
        String toCsv() {
            return "%s,%s,%d,%.3f,%d,%s"
                    .formatted(kind, id, size, medianMillis, work, budgeted ? "single-sample" : "median");
        }
    }

    /** Runs one sweep, repeating it only if the first is cheap enough to be worth repeating. */
    private static Row measure(String kind, String id, int size, java.util.function.LongSupplier sweep) {
        sweep.getAsLong(); // one untimed pass, so nothing is measured in the interpreter

        long start = System.nanoTime();
        long work = sweep.getAsLong();
        double firstMillis = (System.nanoTime() - start) / 1e6;

        if (firstMillis > BUDGET_MILLIS) {
            return new Row(kind, id, size, firstMillis, work, true);
        }

        for (int i = 1; i < WARMUP; i++) {
            sweep.getAsLong();
        }
        double[] samples = new double[REPETITIONS];
        for (int r = 0; r < REPETITIONS; r++) {
            long begin = System.nanoTime();
            work = sweep.getAsLong();
            samples[r] = (System.nanoTime() - begin) / 1e6;
        }
        return new Row(kind, id, size, median(samples), work, false);
    }

    static List<MazeGenerator> generators() {
        return List.of(new RecursiveBacktrackerGenerator(), new PrimsGenerator(),
                new WeightedPrimsGenerator(), new KruskalsGenerator(), new BoruvkasGenerator(),
                new WilsonsGenerator(), new HuntAndKillGenerator(), new RecursiveDivisionGenerator(),
                new BinaryTreeGenerator(), new SidewinderGenerator(), new GrowingTreeGenerator(),
                new OldestPickGenerator(), new AldousBroderGenerator(), new EllersGenerator(),
                new KrakenGenerator(), new MortonCurveGenerator(), new HilbertCurveGenerator(),
                new LightningGenerator(), new TuringGenerator(), new GaussGenerator(),
                new ArchimedesGenerator(), new DungeonGenerator());
    }

    static List<MazeSolver> solvers() {
        return List.of(new BfsSolver(), new DfsSolver(), new DijkstraSolver(), new AStarSolver(),
                new DialSolver(), new BidirectionalSolver(), new TremauxSolver(),
                new WallFollowerSolver(), new DeadEndFillingSolver(), new IDAStarSolver());
    }

    public static void main(String[] args) throws IOException {
        int[] sizes = parseSizes(args);
        int seeds = parseSeeds(args);

        List<Row> rows = new ArrayList<>();
        for (int size : sizes) {
            rows.addAll(timeGenerators(size, seeds));
            rows.addAll(timeSolvers(size, seeds));
        }

        printSummary(rows, sizes);
        Path out = writeCsv(rows, sizes, seeds);
        System.out.println("\nCSV written to " + out.toAbsolutePath());
    }

    static List<Row> timeGenerators(int size, int seeds) {
        List<Row> rows = new ArrayList<>();
        for (MazeGenerator generator : generators()) {
            rows.add(measure("generator", generator.id(), size,
                    () -> sweepGenerate(generator, size, seeds)));
        }
        return rows;
    }

    static List<Row> timeSolvers(int size, int seeds) {
        // Build the mazes once, outside the clock: we are timing solvers here, not generation.
        List<MazeGrid> mazes = new ArrayList<>();
        for (int seed = 1; seed <= seeds; seed++) {
            MazeGrid grid = new RecursiveBacktrackerGenerator()
                    .generate(size, size, seed, new MazeStats());
            MazeMetrics.placeStartAndGoalAtExtremes(grid);
            mazes.add(grid);
        }

        List<Row> rows = new ArrayList<>();
        for (MazeSolver solver : solvers()) {
            rows.add(measure("solver", solver.id(), size, () -> sweepSolve(solver, mazes)));
        }
        return rows;
    }

    private static long sweepGenerate(MazeGenerator generator, int size, int seeds) {
        long cells = 0;
        for (int seed = 1; seed <= seeds; seed++) {
            MazeStats stats = new MazeStats();
            generator.generate(size, size, seed, stats);
            cells += stats.cellsVisited();
        }
        return cells;
    }

    private static long sweepSolve(MazeSolver solver, List<MazeGrid> mazes) {
        long explored = 0;
        for (MazeGrid grid : mazes) {
            MazeStats stats = new MazeStats();
            solver.solve(grid, grid.start(), grid.goal(), stats);
            explored += stats.cellsExplored();
        }
        return explored;
    }

    /** Median, not mean — one GC pause should not move the reported number. */
    static double median(double[] samples) {
        double[] sorted = samples.clone();
        java.util.Arrays.sort(sorted);
        int mid = sorted.length / 2;
        return sorted.length % 2 == 1
                ? sorted[mid]
                : (sorted[mid - 1] + sorted[mid]) / 2.0;
    }

    private static void printSummary(List<Row> rows, int[] sizes) {
        for (String kind : new String[] {"generator", "solver"}) {
            System.out.printf("%n=== %ss (median ms per sweep) ===%n", kind);
            System.out.printf("%-24s", kind);
            for (int size : sizes) {
                System.out.printf("%12s", size + "x" + size);
            }
            System.out.printf("%12s%n", "vs fastest");

            List<Row> forKind = rows.stream().filter(r -> r.kind().equals(kind)).toList();
            int largest = sizes[sizes.length - 1];
            double fastest = forKind.stream().filter(r -> r.size() == largest)
                    .mapToDouble(Row::medianMillis).min().orElse(1.0);

            forKind.stream().map(Row::id).distinct().sorted().forEach(id -> {
                System.out.printf("%-24s", id);
                double atLargest = 0;
                for (int size : sizes) {
                    double ms = forKind.stream()
                            .filter(r -> r.id().equals(id) && r.size() == size)
                            .mapToDouble(Row::medianMillis).findFirst().orElse(Double.NaN);
                    if (size == largest) {
                        atLargest = ms;
                    }
                    System.out.printf("%12.2f", ms);
                }
                System.out.printf("%11.1fx%n", atLargest / fastest);
            });
        }
    }

    private static Path writeCsv(List<Row> rows, int[] sizes, int seeds) throws IOException {
        Runtime runtime = Runtime.getRuntime();
        List<String> lines = new ArrayList<>();
        lines.add("# Daedalus benchmark — " + LocalDate.now());
        lines.add("# NOT a specification: absolute times are specific to this machine and this");
        lines.add("# run. Compare algorithms within a run; do not compare across machines, and");
        lines.add("# never assert on these numbers in CI.");
        lines.add("# jvm=" + System.getProperty("java.version")
                + " vendor=" + System.getProperty("java.vendor")
                + " os=" + System.getProperty("os.name") + "/" + System.getProperty("os.arch")
                + " cpus=" + runtime.availableProcessors()
                + " maxHeapMB=" + runtime.maxMemory() / (1024 * 1024));
        lines.add("# sizes=" + java.util.Arrays.toString(sizes) + " seedsPerSweep=" + seeds
                + " warmup=" + WARMUP + " repetitions=" + REPETITIONS
                + " budgetMs=" + BUDGET_MILLIS);
        lines.add("kind,id,size,median_ms,work_units,statistic");
        rows.forEach(r -> lines.add(r.toCsv()));

        Path dir = repositoryRoot().resolve("docs").resolve("benchmarks");
        Files.createDirectories(dir);
        Path out = dir.resolve("benchmark-" + LocalDate.now() + ".csv");
        Files.write(out, lines);
        return out;
    }

    /**
     * The repository root, so results land in one {@code docs/benchmarks/} regardless of where
     * the harness was launched from.
     *
     * <p>{@code exec:java} runs with the <em>module</em> directory as the working directory, so
     * a plain relative path quietly created
     * {@code examples/benchmark-harness/docs/benchmarks/} — a second, invisible results
     * directory. Walking up to the marker keeps every run writing to the same place. Falls back
     * to the working directory when no marker is found, so the harness still works if the
     * module is copied elsewhere.
     */
    static Path repositoryRoot() {
        Path candidate = Path.of("").toAbsolutePath();
        while (candidate != null) {
            if (Files.isDirectory(candidate.resolve("daedalus-core"))
                    && Files.isRegularFile(candidate.resolve("pom.xml"))) {
                return candidate;
            }
            candidate = candidate.getParent();
        }
        return Path.of("").toAbsolutePath();
    }

    private static int[] parseSizes(String[] args) {
        for (String arg : args) {
            if (arg.startsWith("--sizes=")) {
                String[] parts = arg.substring("--sizes=".length()).split(",");
                int[] sizes = new int[parts.length];
                for (int i = 0; i < parts.length; i++) {
                    sizes[i] = Integer.parseInt(parts[i].trim());
                }
                return sizes;
            }
        }
        return new int[] {50, 100, 200};
    }

    private static int parseSeeds(String[] args) {
        for (String arg : args) {
            if (arg.startsWith("--seeds=")) {
                return Integer.parseInt(arg.substring("--seeds=".length()).trim());
            }
        }
        return 5;
    }
}
