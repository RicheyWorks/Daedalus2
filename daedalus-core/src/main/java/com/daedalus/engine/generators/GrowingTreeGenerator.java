// SPDX-License-Identifier: MIT

package com.daedalus.engine.generators;

import com.daedalus.engine.AbstractMazeGenerator;
import com.daedalus.engine.MazeGrid;
import com.daedalus.model.AlgorithmDescriptor;
import com.daedalus.model.MazeStats;

/**
 * Growing Tree (mixed). The "meta-algorithm" — picks a cell from an active list and
 * carves to a random unvisited neighbor. Different cell-selection policies recover
 * different algorithms:
 *
 * <ul>
 *   <li>Always pick newest → Recursive Backtracker</li>
 *   <li>Always pick random → Prim's-ish</li>
 *   <li>Mix → custom textures</li>
 * </ul>
 *
 * <p>This implementation uses a 50/50 newest/random pick via
 * {@link GrowingTreePolicies#mixed(double)} for a textured middle-ground feel. The shared
 * loop body lives in {@link GrowingTreeEngine}; only the cell-selection rule is plugged in
 * here.
 */
public class GrowingTreeGenerator extends AbstractMazeGenerator {

    @Override public String id() { return "growing-tree"; }
    @Override public String displayName() { return "Growing Tree (mixed)"; }

    @Override
    public AlgorithmDescriptor descriptor() {
        return new AlgorithmDescriptor(
                id(), displayName(), "generator",
                "O(n) time, O(n) space",
                "Tunable bias; default 50/50 newest/random gives mixed texture",
                "Generalization of Prim's and DFS via cell-selection policy.");
    }

    @Override
    public MazeGrid generate(int rows, int cols, long seed, MazeStats stats) {
        return GrowingTreeEngine.run(rows, cols, seed, stats, GrowingTreePolicies.mixed(0.5));
    }
}
