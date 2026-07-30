// SPDX-License-Identifier: MIT

package com.daedalus.engine;

import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * {@link MazeGrid#copy()} is ADR-006's copy-on-write primitive: a living-maze tick mutates
 * a copy and atomically swaps it into the cache while readers keep the old snapshot. That
 * only works if the copy is (a) structurally identical and (b) fully independent — and if
 * {@link WeightedMazeGrid#copy()} keeps both the runtime type and the weights, since a
 * weighted maze that silently flattens to uniform cost on its first mutation would erase
 * every hotspot without any test noticing at the API layer.
 */
class MazeGridCopyTest {

    @Test
    void copyPreservesTopologyAndEndpoints() {
        MazeGrid original = new RecursiveBacktrackerGenerator()
                .generate(15, 15, 42L, new MazeStats());
        original.setStart(new Point(3, 4));
        original.setGoal(new Point(11, 9));

        MazeGrid copy = original.copy();

        assertThat(copy.toTileGrid()).isDeepEqualTo(original.toTileGrid());
        assertThat(copy.start()).isEqualTo(original.start());
        assertThat(copy.goal()).isEqualTo(original.goal());
    }

    @Test
    void copyIsIndependent_carvingTheCopyNeverTouchesTheOriginal() {
        MazeGrid original = new RecursiveBacktrackerGenerator()
                .generate(9, 9, 7L, new MazeStats());
        MazeGrid copy = original.copy();

        // A perfect maze always has dead ends — open one extra wall on the copy only.
        List<Point> deadEnds = Braider.deadEnds(copy);
        assertThat(deadEnds).isNotEmpty();
        Braider.braid(copy, 1.0, 99L);

        assertThat(Braider.deadEnds(copy)).isEmpty();
        assertThat(Braider.deadEnds(original))
                .as("braiding the copy must not carve the original")
                .containsExactlyElementsOf(deadEnds);
    }

    @Test
    void weightedCopyKeepsTypeAndWeights() {
        MazeGrid base = new RecursiveBacktrackerGenerator().generate(8, 8, 5L, new MazeStats());
        WeightedMazeGrid weighted = new WeightedMazeGrid(base);
        weighted.setWeight(new Point(2, 3), 25.0);
        weighted.setWeight(new Point(6, 1), 400.0);

        MazeGrid copy = weighted.copy();

        assertThat(copy).isInstanceOf(WeightedMazeGrid.class);
        assertThat(copy.weightOf(2, 3)).isEqualTo(25.0);
        assertThat(copy.weightOf(6, 1)).isEqualTo(400.0);
        assertThat(copy.weightOf(0, 0)).isEqualTo(1.0);

        // And weight independence, same rule as topology.
        ((WeightedMazeGrid) copy).setWeight(new Point(2, 3), 900.0);
        assertThat(weighted.weightOf(2, 3)).isEqualTo(25.0);
    }
}
