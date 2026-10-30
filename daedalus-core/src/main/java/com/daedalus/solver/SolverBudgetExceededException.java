// SPDX-License-Identifier: MIT

package com.daedalus.solver;

/**
 * Thrown when a solver gives up because it has spent its node budget.
 *
 * <h3>Why this is an exception and not an empty path</h3>
 *
 * <p>{@link MazeSolver#solve} documents an empty list as "unreachable". A solver that ran out of
 * budget has learned nothing about reachability — returning empty would state, in the API's own
 * vocabulary, that no route exists, about a maze that may be trivially solvable. Every other
 * caller downstream (the compare table, the arena, the sweep) would then record a confident
 * wrong answer. Failing loudly is the only option that does not put a lie in a data structure.
 *
 * <p>Callers that run several solvers over one maze should catch this per solver and report that
 * one as "gave up", rather than letting it end the whole comparison.
 */
public class SolverBudgetExceededException extends RuntimeException {

    private static final long serialVersionUID = 1L;

    private final String solverId;
    private final long budget;

    public SolverBudgetExceededException(String solverId, long budget) {
        super(solverId + " gave up after expanding " + budget + " nodes without finding a route. "
                + "This is a cost guard, not a statement that the maze is unsolvable — try a "
                + "solver whose cost does not depend on re-expansion, such as A* or BFS.");
        this.solverId = solverId;
        this.budget = budget;
    }

    public String solverId() {
        return solverId;
    }

    public long budget() {
        return budget;
    }
}
