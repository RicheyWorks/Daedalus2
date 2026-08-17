// SPDX-License-Identifier: MIT
//
// Harness for ADR-016 — "should MazeGrid pack wall bits into a long[], or did the
// remaining D2 win already land as Cell's nibble + allocation-free MazeGraph?"
//
// Core-only. Not in the reactor. Compile against an installed daedalus-core:
//
//   javac -cp daedalus-core/target/classes BitsetGridEval.java
//   java  -cp daedalus-core/target/classes;. BitsetGridEval
//
// Three neighbor walks of the same maze:
//   mazegraph  — production MazeGraph.neighbors (coordinate isOpen, no Point)
//   packed     — the same walk over an int[] of 4-bit masks (no Cell objects)
//   copy       — MazeGrid.copy() vs System.arraycopy of that int[]
//
// Generation time is the denominator: if a packed sweep is 2× and still a
// rounding error on a generate+solve, the long[] rewrite cannot pay.

import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.PrimsGenerator;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.graph.MazeGraph;
import com.daedalus.model.Direction;
import com.daedalus.model.MazeStats;
import com.daedalus.solver.solvers.DijkstraSolver;
import com.daedalus.theory.MazeMetrics;

import java.util.Arrays;
import java.util.Locale;

/** ADR-001 leftover D2: is a packed MazeGrid still worth it? */
public final class BitsetGridEval {

    private static final int WARM = 8;
    private static final int REPS = 21;
    private static final long SEED = 42L;
    private static final Direction[] DIRS = Direction.values();

    public static void main(String[] args) {
        System.out.println("jvm=" + System.getProperty("java.version")
                + "  os=" + System.getProperty("os.name")
                + "  cpus=" + Runtime.getRuntime().availableProcessors());
        System.out.println("warm=" + WARM + "  reps=" + REPS + "  figure=median ns");
        System.out.println();
        System.out.printf(Locale.ROOT, "%-18s %6s %12s %12s %12s%n",
                "work", "size", "mazegraph_us", "packed_us", "copy_vs_pack");
        for (int size : new int[] {32, 64, 128, 256}) {
            time(size);
        }
        System.out.println();
        System.out.printf(Locale.ROOT, "%-18s %6s %12s%n", "work", "size", "median_us");
        for (int size : new int[] {32, 64, 128}) {
            timeGenerate("generate backtracker", size, new RecursiveBacktrackerGenerator());
            timeGenerate("generate prims", size, new PrimsGenerator());
            timeSolve("dijkstra", size);
        }
    }

    private static void time(int size) {
        MazeGrid grid = new RecursiveBacktrackerGenerator()
                .generate(size, size, SEED, new MazeStats());
        MazeMetrics.placeStartAndGoalAtExtremes(grid);
        MazeGraph graph = new MazeGraph(grid);
        int[] packed = pack(grid);
        int[] buf = new int[4];

        long graphNs = median(REPS, () -> sweepGraph(graph, buf));
        long packNs = median(REPS, () -> sweepPacked(packed, size));
        long copyNs = median(REPS, grid::copy);
        long packCopyNs = median(REPS, () -> Arrays.copyOf(packed, packed.length));

        System.out.printf(Locale.ROOT, "%-18s %6d %12.1f %12.1f %12.1fx%n",
                "neighbor sweep", size,
                graphNs / 1_000.0, packNs / 1_000.0,
                copyNs / (double) packCopyNs);
    }

    private static void timeGenerate(String label, int size,
                                     com.daedalus.engine.MazeGenerator gen) {
        for (int i = 0; i < WARM; i++) {
            gen.generate(size, size, SEED, new MazeStats());
        }
        long ns = median(REPS, () -> gen.generate(size, size, SEED, new MazeStats()));
        System.out.printf(Locale.ROOT, "%-18s %6d %12.1f%n", label, size, ns / 1_000.0);
    }

    private static void timeSolve(String label, int size) {
        MazeGrid grid = new RecursiveBacktrackerGenerator()
                .generate(size, size, SEED, new MazeStats());
        MazeMetrics.placeStartAndGoalAtExtremes(grid);
        DijkstraSolver solver = new DijkstraSolver();
        for (int i = 0; i < WARM; i++) {
            solver.solve(grid, grid.start(), grid.goal(), new MazeStats());
        }
        long ns = median(REPS, () -> solver.solve(grid, grid.start(), grid.goal(), new MazeStats()));
        System.out.printf(Locale.ROOT, "%-18s %6d %12.1f%n", label, size, ns / 1_000.0);
    }

    private static int[] pack(MazeGrid grid) {
        int n = grid.rows() * grid.cols();
        int[] masks = new int[n];
        int cols = grid.cols();
        for (int r = 0; r < grid.rows(); r++) {
            for (int c = 0; c < cols; c++) {
                int m = 0;
                for (Direction d : DIRS) {
                    if (grid.isOpen(r, c, d)) {
                        m |= 1 << d.ordinal();
                    }
                }
                masks[r * cols + c] = m;
            }
        }
        return masks;
    }

    private static int sweepGraph(MazeGraph graph, int[] buf) {
        int sum = 0;
        for (int n = 0; n < graph.nodeCount(); n++) {
            sum += graph.neighbors(n, buf);
        }
        return sum;
    }

    private static int sweepPacked(int[] masks, int size) {
        int sum = 0;
        for (int id = 0; id < masks.length; id++) {
            int row = id / size;
            int col = id % size;
            int m = masks[id];
            for (Direction d : DIRS) {
                if ((m & (1 << d.ordinal())) == 0) {
                    continue;
                }
                int nr = row + d.dr();
                int nc = col + d.dc();
                if (nr >= 0 && nr < size && nc >= 0 && nc < size) {
                    sum++;
                }
            }
        }
        return sum;
    }

    private static long median(int reps, Runnable work) {
        for (int i = 0; i < WARM; i++) {
            work.run();
        }
        long[] samples = new long[reps];
        for (int i = 0; i < reps; i++) {
            long t0 = System.nanoTime();
            work.run();
            samples[i] = System.nanoTime() - t0;
        }
        Arrays.sort(samples);
        return samples[reps / 2];
    }
}
