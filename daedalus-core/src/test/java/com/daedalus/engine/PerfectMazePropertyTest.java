// SPDX-License-Identifier: MIT

package com.daedalus.engine;

import com.daedalus.engine.generators.BoruvkasGenerator;
import com.daedalus.engine.generators.GaussGenerator;
import com.daedalus.engine.generators.GrowingTreeGenerator;
import com.daedalus.engine.generators.KruskalsGenerator;
import com.daedalus.engine.generators.LightningGenerator;
import com.daedalus.engine.generators.OldestPickGenerator;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.engine.generators.TuringGenerator;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;

import java.util.ArrayDeque;
import java.util.Deque;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.function.Supplier;
import java.util.stream.Stream;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Property test for the maze engine: a "perfect maze" generator's output must be a
 * spanning tree of the grid — every cell reachable from the start, no cycles, exactly
 * W*H − 1 carved edges. Any failure here means a generator violated the spanning-tree
 * contract advertised in {@link MazeGenerator}'s Javadoc.
 *
 * <p>Parameterized over every generator that promises to produce a perfect maze. The
 * Kruskal / Borůvka entries guard the {@link com.daedalus.util.DSU} migration; the four
 * Growing-Tree entries guard the {@link com.daedalus.engine.generators.GrowingTreeEngine}
 * unification. If any of these regress to a disconnected, cyclic, or wrong-edge-count
 * output, a single test row fails with a clear "which generator" label.
 *
 * <p>This test is deterministic (fixed seed), small (12×17 cells), and uses only the
 * daedalus-core public API plus JUnit 5 + AssertJ. It must run in pure JVM mode under
 * {@code mvn -pl daedalus-core test} — no Spring, no server, no plugin runtime,
 * no JavaFX on the classpath.
 */
class PerfectMazePropertyTest {

    private static final int ROWS = 12;
    private static final int COLS = 17;
    private static final long SEED = 42L;

    /**
     * Every generator that contractually produces a perfect (spanning-tree) maze.
     * Entries are {@code (humanLabel, supplier)} pairs — the label is what JUnit prints
     * on failure, the supplier gives a fresh generator per test row so we never share
     * mutable state between rows.
     */
    private static Stream<Arguments> perfectMazeGenerators() {
        return Stream.of(
                Arguments.of("recursive-backtracker",
                        (Supplier<MazeGenerator>) RecursiveBacktrackerGenerator::new),
                Arguments.of("kruskals",
                        (Supplier<MazeGenerator>) KruskalsGenerator::new),
                Arguments.of("boruvkas",
                        (Supplier<MazeGenerator>) BoruvkasGenerator::new),
                Arguments.of("growing-tree",
                        (Supplier<MazeGenerator>) GrowingTreeGenerator::new),
                Arguments.of("oldest-pick",
                        (Supplier<MazeGenerator>) OldestPickGenerator::new),
                Arguments.of("lightning",
                        (Supplier<MazeGenerator>) LightningGenerator::new),
                Arguments.of("gauss",
                        (Supplier<MazeGenerator>) GaussGenerator::new),
                Arguments.of("turing",
                        (Supplier<MazeGenerator>) TuringGenerator::new)
        );
    }

    @ParameterizedTest(name = "{0} produces a perfect maze")
    @MethodSource("perfectMazeGenerators")
    void producesPerfectMaze(String label, Supplier<MazeGenerator> factory) {
        MazeGenerator generator = factory.get();
        MazeStats stats = new MazeStats();

        MazeGrid grid = generator.generate(ROWS, COLS, SEED, stats);

        int totalCells = grid.rows() * grid.cols();
        Point start = new Point(0, 0);

        // (1) Connectivity: every cell must be reachable via carved openings only.
        Set<Point> reachable = floodFill(grid, start);
        assertThat(reachable)
                .as("[%s] every cell must be reachable from the start (no isolated regions)", label)
                .hasSize(totalCells);

        // (2) Acyclicity: BFS with parent tracking finds no back-edges.
        assertThat(hasNoCycles(grid, start))
                .as("[%s] the carved graph must be a tree (no back-edges during BFS)", label)
                .isTrue();

        // (3) Edge count: a tree on N nodes has exactly N−1 edges.
        int carvedEdges = countCarvedEdges(grid);
        assertThat(carvedEdges)
                .as("[%s] a perfect maze on %d×%d cells must have exactly %d carved edges",
                        label, ROWS, COLS, totalCells - 1)
                .isEqualTo(totalCells - 1);
    }

    /** BFS over the grid following only carved (open) edges. */
    private Set<Point> floodFill(MazeGrid grid, Point start) {
        Set<Point> seen = new HashSet<>();
        Deque<Point> queue = new ArrayDeque<>();
        queue.add(start);
        seen.add(start);
        while (!queue.isEmpty()) {
            Point p = queue.removeFirst();
            for (Point n : grid.openNeighbors(p)) {
                if (seen.add(n)) queue.add(n);
            }
        }
        return seen;
    }

    /**
     * BFS with parent tracking. Returns false the moment we encounter an open neighbor
     * that's already been visited and is <em>not</em> our immediate parent — that's the
     * textbook back-edge definition of a cycle in an undirected graph.
     */
    private boolean hasNoCycles(MazeGrid grid, Point start) {
        Map<Point, Point> parent = new HashMap<>();
        parent.put(start, start); // root is its own parent — sentinel that never matches a real edge
        Deque<Point> queue = new ArrayDeque<>();
        queue.add(start);
        while (!queue.isEmpty()) {
            Point u = queue.removeFirst();
            Point parentOfU = parent.get(u);
            for (Point v : grid.openNeighbors(u)) {
                if (parent.containsKey(v)) {
                    // Already visited. The only legitimate revisit is the edge back to
                    // our own parent (the edge we came in on). Anything else = back-edge = cycle.
                    if (!v.equals(parentOfU)) return false;
                } else {
                    parent.put(v, u);
                    queue.add(v);
                }
            }
        }
        return true;
    }

    /** Count carved openings. Each open edge is shared by two cells, so we halve. */
    private int countCarvedEdges(MazeGrid grid) {
        int totalOpenings = 0;
        for (int r = 0; r < grid.rows(); r++) {
            for (int c = 0; c < grid.cols(); c++) {
                totalOpenings += grid.openNeighbors(new Point(r, c)).size();
            }
        }
        return totalOpenings / 2;
    }
}
