// SPDX-License-Identifier: MIT

package com.daedalus.engine.generators;

import com.daedalus.engine.MazeGenerator;
import com.daedalus.engine.MazeGrid;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.theory.MazeMetrics;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;

import java.util.ArrayDeque;
import java.util.Deque;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.stream.Stream;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Every generator that claims to build a perfect maze must actually produce a spanning tree —
 * connected, with exactly {@code V-1} edges.
 *
 * <p>{@code PerfectMazePropertyTest} checks this for eight hand-picked generators. That gap
 * mattered: an audit across all of them found {@link HilbertCurveGenerator} emitting a
 * <b>forest</b> — 953 edges for 1024 cells at 32², with only 66 cells reachable from the origin —
 * because a cell arriving with no visited neighbour was silently skipped rather than connected.
 * Since both vision documents recommend Hilbert as the topology generator for LoadBalancer work,
 * that defect would have produced empty routes with no error. This test covers the whole roster so
 * the same class of bug cannot hide in an unwatched generator again.
 *
 * <p>{@link DungeonGenerator} is deliberately excluded: it is contractually <em>not</em> a perfect
 * maze (open rooms, loops, and unreachable rock), and {@code DungeonGeneratorTest} asserts its own
 * connectivity property instead.
 */
class GeneratorConnectivityTest {

    private static final int SIZE = 24;

    private static List<MazeGenerator> spanningTreeGenerators() {
        return List.of(
                new RecursiveBacktrackerGenerator(), new PrimsGenerator(), new WeightedPrimsGenerator(),
                new KruskalsGenerator(), new BoruvkasGenerator(), new WilsonsGenerator(),
                new HuntAndKillGenerator(), new RecursiveDivisionGenerator(), new BinaryTreeGenerator(),
                new SidewinderGenerator(), new GrowingTreeGenerator(), new OldestPickGenerator(),
                new AldousBroderGenerator(), new EllersGenerator(), new KrakenGenerator(),
                new MortonCurveGenerator(), new HilbertCurveGenerator(), new LightningGenerator(),
                new TuringGenerator(), new GaussGenerator(), new ArchimedesGenerator());
    }

    @Test
    void everyGeneratorProducesAConnectedSpanningTree() {
        for (MazeGenerator generator : spanningTreeGenerators()) {
            for (long seed = 1; seed <= 3; seed++) {
                MazeGrid grid = generator.generate(SIZE, SIZE, seed, new MazeStats());

                assertThat(reachableFromOrigin(grid))
                        .as("%s seed %d: every cell must be reachable", generator.id(), seed)
                        .isEqualTo(SIZE * SIZE);
                assertThat(edgeCount(grid))
                        .as("%s seed %d: a spanning tree has exactly V-1 edges", generator.id(), seed)
                        .isEqualTo(SIZE * SIZE - 1);
            }
        }
    }

    /**
     * Grid shapes that are not a comfortable square. Several generators carry an implicit shape
     * assumption — the space-filling curves want a power of two, {@code DungeonGenerator} wants
     * room to split BSP leaves, {@code EllersGenerator} works a row at a time — and a degenerate
     * or lopsided grid is where such an assumption surfaces.
     */
    static Stream<Arguments> awkwardShapes() {
        return Stream.of(
                Arguments.of(1, 1, "single cell"),
                Arguments.of(1, 10, "single row"),
                Arguments.of(10, 1, "single column"),
                Arguments.of(2, 3, "smallest non-square"),
                Arguments.of(7, 13, "both prime"),
                Arguments.of(33, 17, "odd and lopsided"),
                Arguments.of(5, 64, "extreme aspect ratio"),
                Arguments.of(20, 20, "square, not a power of two"));
    }

    @ParameterizedTest(name = "{2} ({0}x{1})")
    @MethodSource("awkwardShapes")
    void everyGeneratorSpansAnyGridShape(int rows, int cols, String description) {
        // The square-grid test above would not catch a generator that quietly drops the last
        // column of a lopsided grid, or that divides by zero on a single row.
        for (MazeGenerator generator : spanningTreeGenerators()) {
            MazeGrid grid = generator.generate(rows, cols, 7L, new MazeStats());

            assertThat(reachableFromOrigin(grid))
                    .as("%s at %dx%d (%s): every cell must be reachable",
                            generator.id(), rows, cols, description)
                    .isEqualTo(rows * cols);
            assertThat(edgeCount(grid))
                    .as("%s at %dx%d (%s): a spanning tree has exactly V-1 edges",
                            generator.id(), rows, cols, description)
                    .isEqualTo(rows * cols - 1);
        }
    }

    @ParameterizedTest(name = "{2} ({0}x{1})")
    @MethodSource("awkwardShapes")
    void dungeonKeepsItsCarvedSpaceConnectedAtAnyShape(int rows, int cols, String description) {
        // DungeonGenerator is excluded from the spanning-tree roster because rock is meant to be
        // unreachable — but the *carved* space must still be one connected level, or the layout
        // has rooms the player can never enter. That is the property that survives its contract.
        MazeGrid grid = new DungeonGenerator().generate(rows, cols, 7L, new MazeStats());

        int carved = 0;
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                if (!grid.openNeighbors(new Point(r, c)).isEmpty()) {
                    carved++;
                }
            }
        }
        if (carved == 0) {
            return; // too small to hold a room; nothing carved is a legitimate outcome
        }

        int reachable = 0;
        for (int[] row : MazeMetrics.distancesFrom(grid, MazeMetrics.largestComponentCell(grid))) {
            for (int distance : row) {
                if (distance >= 0) {
                    reachable++;
                }
            }
        }
        assertThat(reachable)
                .as("dungeon at %dx%d (%s): floor area must be a single connected level",
                        rows, cols, description)
                .isEqualTo(carved);
    }

    @Test
    void hilbertIsConnectedOnNonPowerOfTwoSizes_wherePreviousOrderingBroke() {
        // The curve of the enclosing power-of-two square gets filtered here, so adjacency between
        // consecutive cells is not guaranteed and the repair pass is what carries connectivity.
        for (int size : new int[] {13, 20, 31}) {
            MazeGrid grid = new HilbertCurveGenerator().generate(size, size, 42L, new MazeStats());

            assertThat(reachableFromOrigin(grid)).as("hilbert %dx%d", size, size).isEqualTo(size * size);
            assertThat(edgeCount(grid)).isEqualTo(size * size - 1);
        }
    }

    @Test
    void hilbertIsConnectedOnRectangularGrids() {
        MazeGrid grid = new HilbertCurveGenerator().generate(17, 40, 7L, new MazeStats());

        assertThat(reachableFromOrigin(grid)).isEqualTo(17 * 40);
        assertThat(edgeCount(grid)).isEqualTo(17 * 40 - 1);
    }

    private static int reachableFromOrigin(MazeGrid grid) {
        Set<Point> seen = new HashSet<>();
        Deque<Point> queue = new ArrayDeque<>();
        Point origin = new Point(0, 0);
        seen.add(origin);
        queue.add(origin);
        while (!queue.isEmpty()) {
            for (Point n : grid.openNeighbors(queue.poll())) {
                if (seen.add(n)) {
                    queue.add(n);
                }
            }
        }
        return seen.size();
    }

    private static int edgeCount(MazeGrid grid) {
        int halfEdges = 0;
        for (int r = 0; r < grid.rows(); r++) {
            for (int c = 0; c < grid.cols(); c++) {
                halfEdges += grid.openNeighbors(new Point(r, c)).size();
            }
        }
        return halfEdges / 2;
    }
}
