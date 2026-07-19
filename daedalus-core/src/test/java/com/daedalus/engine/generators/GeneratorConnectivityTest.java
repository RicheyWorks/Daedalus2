// SPDX-License-Identifier: MIT

package com.daedalus.engine.generators;

import com.daedalus.engine.MazeGenerator;
import com.daedalus.engine.MazeGrid;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import org.junit.jupiter.api.Test;

import java.util.ArrayDeque;
import java.util.Deque;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

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
