// SPDX-License-Identifier: MIT

package com.daedalus.engine.generators;

import com.daedalus.engine.AbstractMazeGenerator;
import com.daedalus.engine.MazeGrid;
import com.daedalus.model.AlgorithmDescriptor;
import com.daedalus.model.MazeStats;

/**
 * Gauss Generator — Quadratic Form Bias (Disquisitiones Arithmeticae style).
 *
 * <p>Carl Friedrich Gauss's favorite playground was quadratic forms and the Gauss circle
 * problem. This generator turns that math into a living spanning tree: at every step we
 * deliberately prefer to expand the active cell with the highest quadratic norm
 * ({@code r² + c²}). The result is an elegant, balanced, almost "crystalline" texture —
 * long corridors that feel mathematically inevitable.
 *
 * <p>The cell-selection rule comes from {@link GrowingTreePolicies#quadraticNorm()}; the
 * loop body it plugs into is the shared {@link GrowingTreeEngine}.
 * {@link LightningGenerator} uses the exact same policy — they're behaviourally
 * identical and the catalog lists both for thematic / id-stability reasons.
 */
public class GaussGenerator extends AbstractMazeGenerator {

    @Override public String id() { return "gauss"; }
    @Override public String displayName() { return "Gauss (Quadratic Form)"; }

    @Override
    public AlgorithmDescriptor descriptor() {
        return new AlgorithmDescriptor(
                id(), displayName(), "generator",
                "O(n log n) worst-case, O(n) space",
                "Quadratic norm bias (r² + c²) creates crystalline, mathematically perfect textures",
                "Directly inspired by Gauss's Disquisitiones Arithmeticae and the Gauss circle problem.");
    }

    @Override
    public MazeGrid generate(int rows, int cols, long seed, MazeStats stats) {
        return GrowingTreeEngine.run(rows, cols, seed, stats, GrowingTreePolicies.quadraticNorm());
    }
}
