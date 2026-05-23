// SPDX-License-Identifier: MIT

package com.daedalus.engine.generators;

import com.daedalus.engine.AbstractMazeGenerator;
import com.daedalus.engine.MazeGrid;
import com.daedalus.model.AlgorithmDescriptor;
import com.daedalus.model.MazeStats;

/**
 * Oldest-Pick Growing-Tree variant. Always expands the front of the active list (FIFO),
 * which gives the Growing-Tree skeleton a BFS-shaped wave-front and produces
 * <em>visually distinctive</em> mazes: short corridors, lots of branches, and a wide
 * "expanding ring" growth pattern radiating from the start cell — the stylistic
 * opposite of {@link RecursiveBacktrackerGenerator}'s long winding rivers.
 *
 * <p>Existence as a one-liner here is the demonstration that the
 * {@link GrowingTreeEngine} + {@link GrowingTreePolicy} extraction pays off: a new
 * registered generator is now a five-line class plus one line in
 * {@code AlgorithmConfig.builtInGenerators()}.
 *
 * <p>Complexity: O(n) time, O(n) space — same as every other Growing-Tree variant. The
 * BFS-like growth keeps the active list shorter on average than newest-pick, but that's a
 * texture difference, not an asymptotic one.
 */
public class OldestPickGenerator extends AbstractMazeGenerator {

    @Override public String id() { return "oldest-pick"; }
    @Override public String displayName() { return "Oldest-Pick (BFS Wave)"; }

    @Override
    public AlgorithmDescriptor descriptor() {
        return new AlgorithmDescriptor(
                id(), displayName(), "generator",
                "O(n) time, O(n) space",
                "BFS-shaped wave-front growth; short branches, expanding-ring texture",
                "Growing-Tree variant that always picks the oldest active cell. Visual opposite of Recursive Backtracker.");
    }

    @Override
    public MazeGrid generate(int rows, int cols, long seed, MazeStats stats) {
        return GrowingTreeEngine.run(rows, cols, seed, stats, GrowingTreePolicies.oldest());
    }
}
