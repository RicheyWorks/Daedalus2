// SPDX-License-Identifier: MIT

package com.daedalus.engine.generators;

import com.daedalus.engine.AbstractMazeGenerator;
import com.daedalus.engine.MazeGrid;
import com.daedalus.model.AlgorithmDescriptor;
import com.daedalus.model.MazeStats;

/**
 * Turing State-Machine Generator.
 *
 * <p>Inspired directly by Alan Turing's finite-state machines and universal computation.
 * The Growing-Tree active list is shared with all the other generators in this family;
 * the wrinkle is a 4-state machine that decides HOW we pick the next cell to expand.
 * Simple rules → wildly complex, ever-shifting textures. Exactly the kind of emergent
 * behavior Turing loved.
 *
 * <p>Visually unique: hybrid of backtracker rivers, Prim bushiness, and chaotic
 * state-driven branching. The cell-selection state lives in
 * {@link GrowingTreePolicies#turingMachine()} and is fresh per generation —
 * {@link GrowingTreeEngine} constructs nothing per-call beyond what we hand it, so a
 * stateful policy is the right scope.
 */
public class TuringGenerator extends AbstractMazeGenerator {

    @Override public String id() { return "turing"; }
    @Override public String displayName() { return "Turing (State Machine)"; }

    @Override
    public AlgorithmDescriptor descriptor() {
        return new AlgorithmDescriptor(
                id(), displayName(), "generator",
                "O(n) time, O(n) space",
                "Simple rules → complex emergent patterns (pure Turing spirit)",
                "Finite-state machine controls cell selection. Honors Alan Turing's legacy of computation & morphogenesis.");
    }

    @Override
    public MazeGrid generate(int rows, int cols, long seed, MazeStats stats) {
        return GrowingTreeEngine.run(rows, cols, seed, stats, GrowingTreePolicies.turingMachine());
    }
}
