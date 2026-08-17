// SPDX-License-Identifier: MIT

package com.daedalus.engine.generators;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.AlgorithmDescriptor;
import com.daedalus.model.MazeStats;
import com.daedalus.theory.MazeMetrics;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * The vision documents and the live {@link AlgorithmDescriptor} used to claim Hilbert has
 * the best locality of any curve generator. Measured stretch (20,000 pairs at 32²) put it
 * worse than Morton and more than double Prim's diameter. The descriptor is what
 * {@code GET /algorithms} shows; a javadoc correction that leaves the API lying is the
 * same defect the vision table had.
 */
class HilbertCurveGeneratorTest {

    @Test
    void descriptorDoesNotClaimBestLocality() {
        AlgorithmDescriptor d = new HilbertCurveGenerator().descriptor();

        assertThat(d.biasNote() + " " + d.description())
                .doesNotContainIgnoringCase("best locality");
    }

    @Test
    void diameterIsWorseThanPrims_andBetterThanAHamiltonianSnake() {
        // Both generators emit trees, so the two-sweep diameter is exact. Pin the order
        // the published table measured, not the exact hop counts (those move with the seed).
        // Carving strictly along the curve produces diameter 1023 on 32² — if someone
        // "fixes" attach to follow the curve, the upper bound fails.
        MazeGrid hilbert = new HilbertCurveGenerator().generate(32, 32, 42L, new MazeStats());
        MazeGrid prims = new PrimsGenerator().generate(32, 32, 42L, new MazeStats());

        int h = MazeMetrics.diameter(hilbert).distance();
        int p = MazeMetrics.diameter(prims).distance();

        assertThat(h)
                .as("Hilbert tree diameter %d vs Prim %d — the curve's locality is not the tree's", h, p)
                .isGreaterThan(p);
        assertThat(h)
                .as("a Hilbert snake is a path of length 1023; random-attach must stay below that")
                .isLessThan(32 * 32 - 1);
    }
}
