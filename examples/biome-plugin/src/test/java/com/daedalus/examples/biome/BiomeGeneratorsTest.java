// SPDX-License-Identifier: MIT

package com.daedalus.examples.biome;

import com.daedalus.engine.MazeGenerator;
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
 * Smoke + invariant tests for the two example biome generators. The full
 * perfect-maze property test in {@code daedalus-core} covers built-ins; here
 * we just confirm that the plugin's generators produce valid mazes and that
 * seeds are deterministic.
 */
class BiomeGeneratorsTest {

    @Test
    void forestBiomeProducesAPerfectMaze() {
        assertPerfect(new ForestBiomeGenerator(), 16, 16, 42L);
    }

    @Test
    void desertBiomeProducesAPerfectMaze() {
        assertPerfect(new DesertBiomeGenerator(), 16, 16, 42L);
    }

    @Test
    void forestBiomeIsSeedDeterministic() {
        assertSameOutputForSameSeed(new ForestBiomeGenerator(), 12, 12, 7L);
    }

    @Test
    void desertBiomeIsSeedDeterministic() {
        assertSameOutputForSameSeed(new DesertBiomeGenerator(), 12, 12, 7L);
    }

    @Test
    void descriptorsAreNonNullAndIdMatchesGenerator() {
        ForestBiomeGenerator f = new ForestBiomeGenerator();
        DesertBiomeGenerator d = new DesertBiomeGenerator();

        assertThat(f.descriptor()).isNotNull();
        assertThat(f.descriptor().id()).isEqualTo(f.id());
        assertThat(d.descriptor()).isNotNull();
        assertThat(d.descriptor().id()).isEqualTo(d.id());
    }

    // ----- helpers -----

    /**
     * Asserts the generator produces a perfect maze: correct dimensions, single
     * connected component, exactly {@code rows*cols - 1} carved edges
     * (i.e. a spanning tree).
     */
    private static void assertPerfect(MazeGenerator gen, int rows, int cols, long seed) {
        MazeGrid grid = gen.generate(rows, cols, seed, new MazeStats());

        assertThat(grid.rows()).isEqualTo(rows);
        assertThat(grid.cols()).isEqualTo(cols);

        // BFS over open neighbours from (0,0) and count cells + edges.
        Set<Point> visited = new HashSet<>();
        Deque<Point> queue = new ArrayDeque<>();
        Point root = new Point(0, 0);
        queue.add(root);
        visited.add(root);

        int edgeCountDoubled = 0;
        while (!queue.isEmpty()) {
            Point p = queue.poll();
            for (Point n : grid.openNeighbors(p)) {
                edgeCountDoubled++;
                if (visited.add(n)) queue.add(n);
            }
        }

        assertThat(visited).hasSize(rows * cols);          // every cell reachable
        assertThat(edgeCountDoubled / 2).isEqualTo(rows * cols - 1); // spanning tree
    }

    private static void assertSameOutputForSameSeed(MazeGenerator gen, int rows, int cols, long seed) {
        MazeGrid a = gen.generate(rows, cols, seed, new MazeStats());
        MazeGrid b = gen.generate(rows, cols, seed, new MazeStats());

        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                Point p = new Point(r, c);
                assertThat(a.openNeighbors(p))
                        .as("openNeighbors at (%d,%d)", r, c)
                        .containsExactlyInAnyOrderElementsOf(b.openNeighbors(p));
            }
        }
    }
}
