// SPDX-License-Identifier: MIT

package com.daedalus.server;

import com.daedalus.engine.MazeGenerator;
import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.model.Direction;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.theory.MazeMetrics;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Property-fuzz every registered generator (ADR-007 idea 9).
 *
 * <p>The project ships 23 generators, most written once and never revisited. Each has unit
 * tests for the shape it was designed to produce; none of them had been checked against the
 * <em>universal</em> invariants — the ones any generator must satisfy whatever its algorithm —
 * across the input space where generators usually break: 1×1, single rows and columns, extreme
 * aspect ratios, non-square grids.
 *
 * <p><b>Driven by the registry, not a hand-written roster.</b> This test injects
 * {@link GeneratorRegistry}, so it fuzzes exactly the generators the application actually
 * registers and a newly added one is covered the moment it is wired up. A hardcoded list would
 * be correct on the day it was written and quietly incomplete afterwards, which is the failure
 * mode of most "test every X" suites — and the reason this is not a duplicate of core's
 * {@code PerfectMazePropertyTest}, which checks the same spanning-tree contract over a
 * hand-listed 8 generators at one size and one seed. That test stays: it runs in pure-JVM core
 * with no Spring, and it is the faster signal. This one is the wider net.
 *
 * <p>Result on first run: <b>zero violations</b> across every registered generator, 11 shapes
 * and 2 seeds. That is worth recording as plainly as a bug would be — the point of the exercise
 * was to find out, and now the answer is measured rather than assumed. It also means the
 * crossbreeding rock defect (a repair that carved away half a dungeon) would have been caught
 * here, because "every habitable cell is mutually reachable" is one of the properties below.
 *
 * <p><b>A green property test proves nothing until it has been seen to fail.</b> Finding no
 * violations is exactly the outcome a vacuous test produces, so {@code mutants/fuzzteeth.py}
 * breaks a real generator (Binary Tree) six ways — one per property — and checks the fuzz
 * notices. All six are caught, each by the property it was aimed at:
 *
 * <pre>
 *   one-sided opening              -> asymmetric wall          (universal invariants)
 *   opening off the grid edge      -> opening leaves the grid  (universal invariants)
 *   seed mixed with the clock      -> not deterministic        (universal invariants)
 *   seed ignored entirely          -> identical for two seeds  (responds to its seed)
 *   carve both N and E (cycles)    -> not a spanning tree      (fills grid ⇒ tree)
 *   walled-off two-cell island     -> stranded habitable cells (universal invariants)
 * </pre>
 *
 * <p>The cycle mutation trips a second property too: carving both directions unconditionally
 * makes the maze the same whatever the seed, so the seed check fires as well. Worth noting
 * because it shows the properties overlap rather than partition the failure space — which is
 * what you want from a safety net.
 */
@SpringBootTest
@ActiveProfiles("test")
class GeneratorInvariantFuzzTest {

    /** Shapes chosen for where generators break: degenerate, thin, and non-square. */
    private static final int[][] SHAPES = {
        {1, 1}, {1, 7}, {7, 1}, {2, 2}, {2, 9}, {9, 2},
        {3, 3}, {5, 8}, {8, 5}, {13, 13}, {16, 24},
    };
    private static final long[] SEEDS = {1L, 12_345L};

    @Autowired
    private GeneratorRegistry registry;

    private record Violation(String generator, String property, String detail) {
        @Override
        public String toString() {
            return generator + " — " + property + " (" + detail + ")";
        }
    }

    @Test
    void everyRegisteredGeneratorHoldsTheUniversalInvariants() {
        List<Violation> violations = new ArrayList<>();
        int runs = 0;

        for (MazeGenerator generator : registry.all()) {
            for (int[] shape : SHAPES) {
                for (long seed : SEEDS) {
                    runs++;
                    check(generator, shape[0], shape[1], seed, violations);
                }
            }
        }

        assertThat(registry.all()).as("no generators registered — the fuzz proved nothing")
                .isNotEmpty();
        assertThat(runs).isEqualTo(registry.all().size() * SHAPES.length * SEEDS.length);
        assertThat(violations)
                .as("%d generator invariant violations over %d runs:%n  %s",
                        violations.size(), runs,
                        violations.stream().map(Object::toString).limit(20).toList())
                .isEmpty();
    }

    private void check(MazeGenerator generator, int rows, int cols, long seed,
                       List<Violation> out) {
        String id = generator.id();
        String where = rows + "x" + cols + " seed=" + seed;

        MazeGrid grid;
        try {
            grid = generator.generate(rows, cols, seed, new MazeStats());
        } catch (RuntimeException e) {
            out.add(new Violation(id, "threw", where + " -> " + e));
            return;
        }
        if (grid == null) {
            out.add(new Violation(id, "returned null", where));
            return;
        }
        if (grid.rows() != rows || grid.cols() != cols) {
            out.add(new Violation(id, "wrong dimensions",
                    where + " -> " + grid.rows() + "x" + grid.cols()));
            return;
        }

        // A passage is a two-way agreement; a one-sided opening is a corrupt grid that would
        // let a solver walk through a wall in one direction only.
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                for (Direction d : Direction.values()) {
                    if (!grid.cell(r, c).isOpen(d)) {
                        continue;
                    }
                    int nr = r + d.dr();
                    int nc = c + d.dc();
                    if (!grid.inBounds(nr, nc)) {
                        out.add(new Violation(id, "opening leaves the grid",
                                where + " at (" + r + "," + c + ") " + d));
                    } else if (!grid.cell(nr, nc).isOpen(d.opposite())) {
                        out.add(new Violation(id, "asymmetric wall",
                                where + " between (" + r + "," + c + ") and (" + nr + "," + nc + ")"));
                    }
                }
            }
        }

        // Every carved cell must be mutually reachable. Rock is allowed (Dungeon is half rock);
        // a room nobody can walk to is not.
        Point anchor = firstHabitable(grid);
        if (anchor == null) {
            if (rows * cols > 1) {
                out.add(new Violation(id, "carved nothing at all", where));
            }
            return;
        }
        int[][] distance = MazeMetrics.distancesFrom(grid, anchor);
        int stranded = 0;
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                if (!grid.openNeighbors(new Point(r, c)).isEmpty() && distance[r][c] < 0) {
                    stranded++;
                }
            }
        }
        if (stranded > 0) {
            out.add(new Violation(id, "stranded habitable cells", where + " count=" + stranded));
        }

        // Determinism is a contract the whole project leans on — daily mazes, campaigns and
        // shared seeds are all the same promise.
        MazeGrid again = generator.generate(rows, cols, seed, new MazeStats());
        if (!Arrays.deepEquals(grid.toTileGrid(), again.toTileGrid())) {
            out.add(new Violation(id, "not deterministic", where));
        }
    }

    /**
     * A generator that fills every cell must produce a spanning tree — exactly
     * {@code cells - 1} passages, so no cycles.
     *
     * <p>Stated as a conditional rather than a roster of "the perfect ones": a maze covering
     * every cell with more than {@code cells - 1} edges has loops, which for these algorithms
     * means a bug. Written this way the property extends itself — a new generator is held to it
     * automatically if it fills the grid, and Dungeon opts out by construction rather than by
     * being named in an exclusion list.
     */
    @Test
    void aGeneratorThatFillsTheGridProducesASpanningTree() {
        List<Violation> violations = new ArrayList<>();
        List<String> perfect = new ArrayList<>();
        List<String> sparse = new ArrayList<>();

        for (MazeGenerator generator : registry.all()) {
            for (int size : new int[] {9, 21}) {
                MazeGrid grid = generator.generate(size, size, 7L, new MazeStats());
                int cells = size * size;
                int habitable = countHabitable(grid);
                int passages = countPassages(grid);

                if (habitable < cells) {
                    if (size == 21) {
                        sparse.add(generator.id() + " (" + habitable + "/" + cells + " carved)");
                    }
                    continue; // sparse by design; connectivity is covered by the fuzz above
                }
                if (size == 21) {
                    perfect.add(generator.id());
                }
                if (passages != cells - 1) {
                    violations.add(new Violation(generator.id(), "fills the grid but is not a tree",
                            size + "x" + size + ": " + passages + " passages for " + cells
                                    + " cells (a tree needs " + (cells - 1) + ")"));
                }
            }
        }

        assertThat(violations)
                .as("generators claiming every cell must be acyclic: %s", violations)
                .isEmpty();
        assertThat(perfect)
                .as("measured: %d of %d registered generators produce a perfect maze; sparse: %s",
                        perfect.size(), registry.all().size(), sparse)
                .hasSizeGreaterThan(15);
    }

    /** A generator that ignores its seed makes every shared-seed feature a lie. */
    @Test
    void everyGeneratorRespondsToItsSeed() {
        List<String> ignored = new ArrayList<>();
        for (MazeGenerator generator : registry.all()) {
            MazeGrid a = generator.generate(21, 21, 1L, new MazeStats());
            MazeGrid b = generator.generate(21, 21, 999_983L, new MazeStats());
            if (Arrays.deepEquals(a.toTileGrid(), b.toTileGrid())) {
                ignored.add(generator.id());
            }
        }
        assertThat(ignored)
                .as("these generators produced an identical maze for two different seeds, which "
                        + "would silently break the daily challenge, campaigns and crossbreeding")
                .isEmpty();
    }

    private static Point firstHabitable(MazeGrid grid) {
        for (int r = 0; r < grid.rows(); r++) {
            for (int c = 0; c < grid.cols(); c++) {
                if (!grid.openNeighbors(new Point(r, c)).isEmpty()) {
                    return new Point(r, c);
                }
            }
        }
        return null;
    }

    private static int countHabitable(MazeGrid grid) {
        int habitable = 0;
        for (int r = 0; r < grid.rows(); r++) {
            for (int c = 0; c < grid.cols(); c++) {
                if (!grid.openNeighbors(new Point(r, c)).isEmpty()) {
                    habitable++;
                }
            }
        }
        return habitable;
    }

    private static int countPassages(MazeGrid grid) {
        int passages = 0;
        for (int r = 0; r < grid.rows(); r++) {
            for (int c = 0; c < grid.cols(); c++) {
                if (c + 1 < grid.cols() && grid.cell(r, c).isOpen(Direction.EAST)) {
                    passages++;
                }
                if (r + 1 < grid.rows() && grid.cell(r, c).isOpen(Direction.SOUTH)) {
                    passages++;
                }
            }
        }
        return passages;
    }
}
