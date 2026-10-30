// SPDX-License-Identifier: MIT

package com.daedalus.engine.generators;

import com.daedalus.engine.AbstractMazeGenerator;
import com.daedalus.engine.MazeGrid;
import com.daedalus.model.AlgorithmDescriptor;
import com.daedalus.model.MazeStats;

/**
 * Lightning Generator — Growing-Tree with a mostly-newest pick punctuated by occasional
 * quadratic-norm jumps. The result: long, RB-style corridors that sporadically fork
 * toward the high-norm corner of the grid, producing a jagged "lightning bolt with
 * branches" texture distinct from any other generator in the catalog.
 *
 * <p><b>History.</b> The 2026-05-07 Growing-Tree unification temporarily collapsed
 * Lightning onto {@link GaussGenerator} — both delegated to
 * {@link GrowingTreePolicies#quadraticNorm()} and so produced bit-identical output. Per
 * the BACKLOG resolution, Lightning was given a genuinely different selection policy
 * ({@link GrowingTreePolicies#newestWithNormJump(double)}) to restore its visual identity.
 * The seed → maze mapping for id {@code "lightning"} <em>changed</em> with this refactor;
 * pinned seeds from before 2026-05-11 will no longer resolve to the same maze.
 *
 * <p>Pre-2026-05-07 Lightning shipped a hand-tuned fast path (array-based shuffle,
 * filtered out-of-bounds neighbours before shuffling) that consumed
 * {@link java.util.Random} differently from every other Growing-Tree variant. That
 * fast-path was dropped during unification to keep one engine for the whole family — see
 * {@link GrowingTreeEngine}'s class Javadoc for the trade-off discussion.
 */
public class LightningGenerator extends AbstractMazeGenerator {

    /**
     * Probability that the cell-selection policy takes a quadratic-norm spike rather
     * than the newest cell. Tuned by eye: high enough to punctuate the long RB corridors
     * with visible forks, low enough that the dominant texture is still corridor-like.
     */
    static final double SPIKE_PROBABILITY = 0.15;

    @Override public String id()          { return "lightning"; }
    @Override public String displayName() { return "Lightning"; }

    @Override
    public AlgorithmDescriptor descriptor() {
        return new AlgorithmDescriptor(
                id(), displayName(), "generator",
                "O(n) time, O(n) space",
                "RB-style long corridors punctuated by quadratic-norm spike forks",
                "Mostly newest-pick (long carved corridors) with a " +
                Math.round(SPIKE_PROBABILITY * 100) + "% chance per turn of jumping to the " +
                "highest-norm active cell — produces a jagged lightning-bolt texture " +
                "distinct from Gauss's pure quadratic crystalline feel.");
    }

    @Override
    public MazeGrid generate(int rows, int cols, long seed, MazeStats stats) {
        return GrowingTreeEngine.run(rows, cols, seed, stats,
                GrowingTreePolicies.newestWithNormJump(SPIKE_PROBABILITY));
    }
}
