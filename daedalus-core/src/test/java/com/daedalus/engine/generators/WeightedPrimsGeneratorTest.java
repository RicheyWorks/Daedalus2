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
 * {@link WeightedPrimsGenerator} must produce a perfect maze (spanning tree), differ from the
 * random-frontier {@link PrimsGenerator}, and honour its one genuine texture knob — the
 * directional bias.
 */
class WeightedPrimsGeneratorTest {

    private static final int SIZE = 20;
    private static final long SEED = 42L;

    @Test
    void producesAPerfectMaze() {
        MazeGrid grid = new WeightedPrimsGenerator().generate(SIZE, SIZE, SEED, new MazeStats());

        // Spanning tree: every cell reachable, and exactly V-1 carved edges (so no cycles).
        assertThat(reachableCount(grid)).isEqualTo(SIZE * SIZE);
        assertThat(edgeCount(grid)).isEqualTo(SIZE * SIZE - 1);
    }

    @Test
    void isDeterministicForASeed_andVariesAcrossSeeds() {
        MazeGrid a = new WeightedPrimsGenerator().generate(SIZE, SIZE, SEED, new MazeStats());
        MazeGrid b = new WeightedPrimsGenerator().generate(SIZE, SIZE, SEED, new MazeStats());
        MazeGrid other = new WeightedPrimsGenerator().generate(SIZE, SIZE, SEED + 1, new MazeStats());

        assertThat(signature(a)).isEqualTo(signature(b));
        assertThat(signature(a)).isNotEqualTo(signature(other));
    }

    @Test
    void differsFromTheRandomFrontierPrims_onTheSameSeed() {
        MazeGrid weighted = new WeightedPrimsGenerator().generate(SIZE, SIZE, SEED, new MazeStats());
        MazeGrid classic = new PrimsGenerator().generate(SIZE, SIZE, SEED, new MazeStats());

        assertThat(signature(weighted)).isNotEqualTo(signature(classic));
    }

    @Test
    void horizontalBias_stretchesTheMazeEastWest() {
        MazeGrid isotropic = new WeightedPrimsGenerator(0.0)
                .generate(SIZE, SIZE, SEED, new MazeStats());
        MazeGrid biased = new WeightedPrimsGenerator(1.0)
                .generate(SIZE, SIZE, SEED, new MazeStats());

        assertThat(horizontalEdges(biased))
                .as("a strong horizontal bias must carve more east-west passages")
                .isGreaterThan(horizontalEdges(isotropic));
    }

    @Test
    void populatesStats() {
        MazeStats stats = new MazeStats();
        new WeightedPrimsGenerator().generate(SIZE, SIZE, SEED, stats);

        assertThat(stats.cellsVisited()).isEqualTo(SIZE * SIZE);
        assertThat(stats.maxFrontierSize()).isPositive();
        assertThat(stats.success()).isTrue();
    }

    // ---------- helpers ----------

    private static int reachableCount(MazeGrid grid) {
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

    /** Count of east-west passages (same row). */
    private static int horizontalEdges(MazeGrid grid) {
        int count = 0;
        for (int r = 0; r < grid.rows(); r++) {
            for (int c = 0; c < grid.cols(); c++) {
                Point p = new Point(r, c);
                for (Point n : grid.openNeighbors(p)) {
                    if (n.row() == r && n.col() == c + 1) {
                        count++;
                    }
                }
            }
        }
        return count;
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
