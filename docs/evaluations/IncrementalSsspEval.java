// SPDX-License-Identifier: MIT
//
// Harness for ADR-011 — "incremental SSSP vs full Dijkstra after a living-maze tick".
//
// Core-only. Not in the reactor: a timing assertion on a shared runner is the failure
// TESTING.md already named. Compile against an installed daedalus-core and run by hand.
//
//   javac -cp daedalus-core/target/classes IncrementalSsspEval.java
//   java  -cp daedalus-core/target/classes;. IncrementalSsspEval
//
// What it measures: median wall-clock of a full Dijkstra recompute after the three
// mutations a living tick actually does (erode, harden, drift hotspot weights), at the
// sizes the API serves. The living ticker fires every 2 s. If a recompute is a small
// fraction of that, D* Lite is ceremony around a non-problem.

import com.daedalus.engine.Braider;
import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.Sealer;
import com.daedalus.engine.WeightedMazeGrid;
import com.daedalus.engine.generators.PrimsGenerator;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.solver.solvers.DijkstraSolver;
import com.daedalus.theory.MazeMetrics;

import java.util.Arrays;
import java.util.List;
import java.util.Locale;
import java.util.Random;

/** ADR-001 appendix 5: is incremental SSSP necessary, or is a full recompute already cheap? */
public final class IncrementalSsspEval {

    private static final int WARM = 8;
    private static final int REPS = 21;
    private static final long SEED = 42L;

    public static void main(String[] args) {
        System.out.println("jvm=" + System.getProperty("java.version")
                + "  os=" + System.getProperty("os.name")
                + "  cpus=" + Runtime.getRuntime().availableProcessors());
        System.out.println("warm=" + WARM + "  reps=" + REPS + "  figure=median ns");
        System.out.println();
        System.out.printf(Locale.ROOT, "%-22s %6s %12s %12s %10s%n",
                "mutation", "size", "median_us", "p95_us", "vs_2s_tick");
        for (int size : new int[] {16, 32, 64, 128}) {
            time("erode prims", size, IncrementalSsspEval::erodePrims);
            time("erode backtracker", size, IncrementalSsspEval::erodeBacktracker);
            time("harden braided", size, IncrementalSsspEval::hardenBraided);
            time("drift weights", size, IncrementalSsspEval::driftWeights);
        }
    }

    @FunctionalInterface
    private interface Setup {
        MazeGrid apply(int size);
    }

    private static MazeGrid erodePrims(int size) {
        MazeGrid grid = new PrimsGenerator().generate(size, size, SEED, new MazeStats());
        MazeMetrics.placeStartAndGoalAtExtremes(grid);
        Braider.braid(grid, 0.08, SEED);
        return grid;
    }

    private static MazeGrid erodeBacktracker(int size) {
        MazeGrid grid = new RecursiveBacktrackerGenerator().generate(size, size, SEED, new MazeStats());
        MazeMetrics.placeStartAndGoalAtExtremes(grid);
        Braider.braid(grid, 0.08, SEED);
        return grid;
    }

    private static MazeGrid hardenBraided(int size) {
        MazeGrid grid = new PrimsGenerator().generate(size, size, SEED, new MazeStats());
        MazeMetrics.placeStartAndGoalAtExtremes(grid);
        Braider.braid(grid, 1.0, SEED);
        Sealer.seal(grid, 0.08, SEED);
        return grid;
    }

    private static MazeGrid driftWeights(int size) {
        MazeGrid base = new PrimsGenerator().generate(size, size, SEED, new MazeStats());
        MazeMetrics.placeStartAndGoalAtExtremes(base);
        Braider.braid(base, 0.25, SEED);
        WeightedMazeGrid weighted = new WeightedMazeGrid(base);
        Random rng = new Random(SEED);
        for (int i = 0; i < 8; i++) {
            weighted.setWeight(new Point(rng.nextInt(size), rng.nextInt(size)),
                    1.0 + rng.nextDouble() * 20.0);
        }
        return weighted;
    }

    private static void time(String label, int size, Setup setup) {
        MazeGrid grid = setup.apply(size);
        DijkstraSolver solver = new DijkstraSolver();
        Point start = grid.start();
        Point goal = grid.goal();
        for (int i = 0; i < WARM; i++) {
            solver.solve(grid, start, goal, new MazeStats());
        }
        long[] samples = new long[REPS];
        for (int i = 0; i < REPS; i++) {
            long t0 = System.nanoTime();
            List<Point> path = solver.solve(grid, start, goal, new MazeStats());
            samples[i] = System.nanoTime() - t0;
            if (path.isEmpty()) {
                throw new IllegalStateException(label + " " + size + " returned no route");
            }
        }
        Arrays.sort(samples);
        double medianUs = samples[REPS / 2] / 1_000.0;
        double p95Us = samples[(int) Math.floor(0.95 * (REPS - 1))] / 1_000.0;
        double vsTick = (2_000_000.0) / (samples[REPS / 2] / 1_000.0); // 2s / median_us
        System.out.printf(Locale.ROOT, "%-22s %6d %12.1f %12.1f %9.0fx%n",
                label, size, medianUs, p95Us, vsTick);
    }
}
