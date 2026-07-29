// SPDX-License-Identifier: MIT

package com.daedalus.engine.generators;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.MazeStats;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Chaos-specific properties only. Connectivity, the V-1 edge count, and the awkward-shape
 * sweep all come from {@code GeneratorConnectivityTest} automatically — the structural roster
 * guard forces Chaos Mode onto that roster like any other concrete generator in the package,
 * which is exactly the point of the guard.
 */
class ChaosGeneratorTest {

    @Test
    void sameSeedSameMaze() {
        MazeGrid a = new ChaosGenerator().generate(20, 30, 42L, new MazeStats());
        MazeGrid b = new ChaosGenerator().generate(20, 30, 42L, new MazeStats());
        assertThat(a.toString()).isEqualTo(b.toString());
    }

    @Test
    void differentSeedsProduceDifferentMazes() {
        MazeGrid a = new ChaosGenerator().generate(20, 30, 1L, new MazeStats());
        MazeGrid b = new ChaosGenerator().generate(20, 30, 2L, new MazeStats());
        // Overwhelmingly likely for any real generator; deterministic here because both
        // sides are fixed seeds, so this can never flake — it either holds or the
        // generator broke.
        assertThat(a.toString()).isNotEqualTo(b.toString());
    }

    @Test
    void seedsVaryTheDelegatePoolChoices() {
        // Different seeds must be able to produce structurally different band textures —
        // if every seed picked the same delegates, chaos mode would be a rename. Compare a
        // spread of seeds pairwise; at least one pair must differ in the first band's
        // texture (top-left corner region).
        String[] corners = new String[8];
        for (int seed = 0; seed < corners.length; seed++) {
            MazeGrid g = new ChaosGenerator().generate(24, 24, seed, new MazeStats());
            corners[seed] = g.toString().substring(0, 200);
        }
        assertThat(java.util.Set.of(corners).size())
                .as("8 seeds should not all render an identical top-left region")
                .isGreaterThan(1);
    }

    @Test
    void statsAccumulateAcrossDelegates() {
        MazeStats stats = new MazeStats();
        new ChaosGenerator().generate(20, 20, 7L, stats);
        assertThat(stats.success()).isTrue();
        assertThat(stats.cellsVisited()).isGreaterThan(0);
    }
}
