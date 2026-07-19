// SPDX-License-Identifier: MIT

package com.daedalus.engine.generators;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import org.junit.jupiter.api.Test;

import java.util.ArrayDeque;
import java.util.Deque;
import java.util.HashSet;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * {@link DungeonGenerator} is the one generator here that deliberately breaks the perfect-maze
 * mould, so the tests assert the opposite properties: open rooms, loops, unreachable rock — while
 * still keeping every carved cell in one connected component.
 */
class DungeonGeneratorTest {

    private static final int SIZE = 40;
    private static final long SEED = 42L;

    private static MazeGrid dungeon(long seed) {
        return new DungeonGenerator().generate(SIZE, SIZE, seed, new MazeStats());
    }

    @Test
    void everyCarvedCellIsReachableFromTheStart() {
        MazeGrid grid = dungeon(SEED);

        int carved = countCarved(grid);
        assertThat(carved).isPositive();
        assertThat(reachableFrom(grid, grid.start())).isEqualTo(carved);
    }

    @Test
    void startAndGoalSitOnCarvedGround() {
        MazeGrid grid = dungeon(SEED);

        assertThat(grid.openNeighbors(grid.start())).isNotEmpty();
        assertThat(grid.openNeighbors(grid.goal())).isNotEmpty();
    }

    @Test
    void hasOpenRooms_unlikeAPerfectMaze() {
        MazeGrid dungeonGrid = dungeon(SEED);
        MazeGrid mazeGrid = new RecursiveBacktrackerGenerator().generate(SIZE, SIZE, SEED);

        // Interior room cells are open on all four sides; corridors in a maze rarely are.
        assertThat(fullyOpenCells(dungeonGrid))
                .as("a dungeon should contain open rooms")
                .isGreaterThan(fullyOpenCells(mazeGrid));
    }

    @Test
    void containsLoops_soRoutesAreNotUnique() {
        MazeGrid grid = dungeon(SEED);

        // A tree over the carved component would have exactly (cells - 1) edges; rooms add more.
        assertThat(edgeCount(grid)).isGreaterThan(countCarved(grid) - 1);
    }

    @Test
    void leavesSolidRockBetweenRooms() {
        MazeGrid grid = dungeon(SEED);

        assertThat(countCarved(grid))
                .as("a dungeon should not fill the whole grid")
                .isLessThan(SIZE * SIZE);
    }

    @Test
    void isDeterministicPerSeed_andVariesAcrossSeeds() {
        assertThat(signature(dungeon(SEED))).isEqualTo(signature(dungeon(SEED)));
        assertThat(signature(dungeon(SEED))).isNotEqualTo(signature(dungeon(SEED + 1)));
    }

    @Test
    void isStatelessAcrossRuns() {
        // The generator is registered as a shared singleton, so reusing one instance must be safe.
        DungeonGenerator shared = new DungeonGenerator();
        MazeGrid first = shared.generate(SIZE, SIZE, SEED, new MazeStats());
        shared.generate(SIZE, SIZE, SEED + 5, new MazeStats());
        MazeGrid again = shared.generate(SIZE, SIZE, SEED, new MazeStats());

        assertThat(signature(again)).isEqualTo(signature(first));
    }

    @Test
    void populatesStats() {
        MazeStats stats = new MazeStats();
        new DungeonGenerator().generate(SIZE, SIZE, SEED, stats);

        assertThat(stats.cellsVisited()).isPositive();
        assertThat(stats.success()).isTrue();
    }

    // ---------- helpers ----------

    private static int countCarved(MazeGrid grid) {
        int carved = 0;
        for (int r = 0; r < grid.rows(); r++) {
            for (int c = 0; c < grid.cols(); c++) {
                if (!grid.openNeighbors(new Point(r, c)).isEmpty()) {
                    carved++;
                }
            }
        }
        return carved;
    }

    private static int reachableFrom(MazeGrid grid, Point origin) {
        Set<Point> seen = new HashSet<>();
        Deque<Point> queue = new ArrayDeque<>();
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

    private static int fullyOpenCells(MazeGrid grid) {
        int count = 0;
        for (int r = 0; r < grid.rows(); r++) {
            for (int c = 0; c < grid.cols(); c++) {
                if (grid.openNeighbors(new Point(r, c)).size() == 4) {
                    count++;
                }
            }
        }
        return count;
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

    private static String signature(MazeGrid grid) {
        StringBuilder sb = new StringBuilder();
        for (int r = 0; r < grid.rows(); r++) {
            for (int c = 0; c < grid.cols(); c++) {
                sb.append(grid.openNeighbors(new Point(r, c)).size());
            }
        }
        return sb.toString();
    }
}
