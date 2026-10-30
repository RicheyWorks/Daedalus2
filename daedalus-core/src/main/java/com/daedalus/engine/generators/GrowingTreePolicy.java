// SPDX-License-Identifier: MIT

package com.daedalus.engine.generators;

import com.daedalus.model.Point;

import java.util.List;
import java.util.Random;

/**
 * Cell-selection strategy for the Growing-Tree meta-algorithm. The Growing-Tree family
 * (named for Jamis Buck's classic taxonomy) all share the same skeleton:
 *
 * <ol>
 *   <li>Maintain an "active" list of frontier cells.</li>
 *   <li>Each turn, <b>pick one</b> cell from the active list, try to carve to a random
 *       unvisited neighbor.</li>
 *   <li>If a carve succeeded, push the new cell on the active list. If no neighbor was
 *       available, drop the picked cell.</li>
 * </ol>
 *
 * <p>The algorithm's identity is determined entirely by step 2's <i>pick</i> rule:
 *
 * <ul>
 *   <li>Always pick the newest → Recursive Backtracker.</li>
 *   <li>Pick uniformly at random → Prim's-ish.</li>
 *   <li>Pick the farthest from origin in some norm → Gauss / Lightning (quadratic).</li>
 *   <li>Cycle through several rules → Turing state-machine.</li>
 *   <li>50/50 mix newest/random → mixed-mode Growing Tree.</li>
 * </ul>
 *
 * <p>Implementations may be stateful (e.g., the Turing state-machine policy advances a
 * counter on every call) — the {@link GrowingTreeEngine} constructs a fresh policy per
 * generation, so per-call state is safe and per-instance state is the right scope.
 *
 * @since 1.0
 */
@FunctionalInterface
public interface GrowingTreePolicy {

    /**
     * Pick the index in {@code active} of the cell to expand from this turn.
     *
     * @param active the current frontier list — never empty when this is called
     * @param rng    the same {@link Random} the engine uses; consult it for tie-breaks
     *               or randomized selection so the seed → maze mapping stays deterministic
     * @return an index in {@code [0, active.size())}
     */
    int pickNext(List<Point> active, Random rng);
}
