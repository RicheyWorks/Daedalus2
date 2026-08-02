// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.solver.Heuristics;
import com.daedalus.solver.LandmarkHeuristic;
import com.daedalus.solver.solvers.AStarSolver;
import com.daedalus.theory.MazeMetrics;
import com.daedalus.visualize.MazeReplay;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import java.util.function.ToDoubleBiFunction;

/**
 * Why A* did the work it did (ADR-007 idea 8) — the provable version.
 *
 * <h3>The idea as written did not survive measurement</h3>
 *
 * <p>ADR-007 proposed "measure where A*'s heuristic lies most, and overlay it", to explain in
 * structural terms why a solver lost. The natural reading is per-cell heuristic error,
 * {@code trueDistance - h}, and the claim is that error predicts wasted expansions. It does not.
 * Measured across perfect, braided and dungeon mazes at two sizes, the correlation between a
 * cell's heuristic error and whether A* expanded it wastefully ranged from <b>+0.42 to −0.17</b>
 * — inconsistent in size and not even stable in sign. An overlay built on that would be a
 * plausible-looking picture that explains nothing.
 *
 * <h3>What actually explains it, exactly rather than statistically</h3>
 *
 * <p>A* with an admissible, consistent heuristic expands a node only when {@code f = g* + h} is
 * at most the optimal cost {@code C*}. That is not a tendency, it is the algorithm, so every cell
 * falls into one of three bands:
 *
 * <ul>
 *   <li><b>{@code f < C*} — must be expanded.</b> No tie-breaking rule, implementation detail or
 *       clever ordering can avoid these. This region <em>is</em> the heuristic's cost.</li>
 *   <li><b>{@code f = C*} — may be expanded.</b> The tie band, where the tie-breaking rule alone
 *       decides. Measured on a 21×21 dungeon this band holds 88 cells against a mandatory 30, so
 *       on some mazes tie-breaking matters more than the heuristic does.</li>
 *   <li><b>{@code f > C*} — never expanded.</b> Measured on six configurations, A* touched
 *       <b>zero</b> of these. A non-zero count here would mean the heuristic is inadmissible or
 *       the solver is broken, so the response reports it as a check rather than an assumption.</li>
 * </ul>
 *
 * <p>That reframing also makes "a better heuristic" a measurable claim rather than folklore.
 * Swapping Manhattan for the four-landmark ALT heuristic drops the mandatory band from 925 cells
 * to 0 on a 31×31 perfect maze, and cuts A*'s real expansions by 1.8× there, 5.5× on a braided
 * maze and 2.1× on a dungeon. The mandatory band alone under-predicts the saving, because with a
 * very sharp heuristic almost everything lands in the tie band — which is exactly the sort of
 * detail a correlation would have hidden.
 */
@Service
public class HeuristicLensService {

    /** Cell is below the optimal cost: A* has no choice but to expand it. */
    public static final int BAND_MUST_EXPAND = 0;
    /** Cell sits exactly at the optimal cost: tie-breaking decides. */
    public static final int BAND_TIE = 1;
    /** Cell is above the optimal cost: provably never expanded. */
    public static final int BAND_NEVER = 2;
    /** Cell cannot be reached from the start at all. */
    public static final int BAND_UNREACHABLE = -1;

    private final MazeGenerationService mazes;
    private final int maxFieldCells;

    public HeuristicLensService(MazeGenerationService mazes,
                                @Value("${daedalus.topography.max-field-cells:16384}")
                                int maxFieldCells) {
        this.mazes = mazes;
        this.maxFieldCells = maxFieldCells;
    }

    /**
     * Which heuristic the lens is applied to.
     *
     * <p>{@link #INFLATED} is deliberately <b>inadmissible</b> — Manhattan multiplied by
     * {@value #INFLATION} — and exists to make the guarantee visible by breaking it. Measured on
     * a 31x31 dungeon it cuts A*'s expansions from 341 to 213, and returns a 96-step route where
     * the optimum is 88. That is the weighted-A* trade in one request: real speed, and an answer
     * that is no longer the best one. It is also what gives the {@code expandedAboveOptimal}
     * check something to detect — a counter that only ever reports zero cannot be tested.
     *
     * <p>{@link #MANHATTAN_TIE_BROKEN} answers the question this lens kept raising and could not
     * measure. The note it prints says the tie band is "where the tie-breaking rule decides more
     * of this search than the heuristic does" — true, and useless without a way to see what a
     * tie-breaking rule would actually buy. This is Manhattan scaled by {@code 1 + eps}, the
     * classic straight-line bias, and on the 21x21 dungeon of seed 7 ({@code C* = 40}) the three
     * options line up like this:
     *
     * <pre>
     *                          mandatory   tie   expansions   above C*   route
     *   MANHATTAN                     30    88          115          0      40  (optimal)
     *   MANHATTAN_TIE_BROKEN          30     1           80         50      40  (optimal)
     *   INFLATED (x3)                  0     1           78         78      42  (worse)
     * </pre>
     *
     * <p>Read the third column against the last one. Tie-breaking captures almost all of the
     * speed that tripling the heuristic buys — 115 expansions down to 80, against 78 — and pays
     * none of its price: the route is still a shortest one, where {@code INFLATED} returns 42
     * steps for a best of 40. The mandatory band does not move, because that band is the
     * heuristic's business and this changes no cell's estimate relative to another's; the saving
     * comes entirely out of the tie band, which is the claim the note had been making in prose.
     *
     * <p><b>It is inadmissible, and that is fine — read the fourth column.</b> Scaling h up is
     * exactly what makes {@code INFLATED} inadmissible, and 50 cells above {@code C*} were
     * expanded here too. What differs is the size of the violation. {@code eps} is chosen per
     * maze as {@code 1 / (cells + 1)}: weighted A* returns a route within {@code (1 + eps)}
     * times optimal, no route on a grid exceeds its cell count, so the excess is under one whole
     * step — and costs are integers, so an excess under one step is no excess at all. The
     * optimality is therefore provable rather than lucky. The difference between a tie-breaker
     * and weighted A* is not that one scales and the other does not; it is that one keeps the
     * inflation below the resolution of the cost function.
     */
    public enum Heuristic { MANHATTAN, LANDMARK, INFLATED, MANHATTAN_TIE_BROKEN }

    /** Multiplier making {@link Heuristic#INFLATED} overestimate, and so inadmissible. */
    public static final double INFLATION = 3.0;

    /**
     * Tolerance for placing {@code f} against {@code C*}.
     *
     * <p>The three heuristics wired up here all return integral values on a unit-cost grid, so
     * exact comparison happens to work — and SpotBugs was right to reject it anyway. The band
     * logic takes an arbitrary {@code ToDoubleBiFunction}, and {@code Heuristics.EUCLIDEAN} is
     * already in the codebase: a cell whose true {@code f} is exactly {@code C*} would land in
     * the tie band or the never band depending on the last bit of a square root. The same
     * mistake was fixed once before in this project, on float comparison of cell costs.
     */
    private static final double EPSILON = 1e-9;

    /**
     * @param bands           per-cell band, using the {@code BAND_*} constants
     * @param mustExpand      cells A* is obliged to expand
     * @param tie             cells at exactly the optimal cost, where tie-breaking decides
     * @param never           cells provably out of reach of the search
     * @param actualExpansions cells A* really expanded, recorded from the search itself
     * @param expandedAboveOptimal cells above {@code C*} that were nevertheless expanded — must
     *                             be zero for an admissible heuristic, and is reported so the
     *                             claim is checked on every request rather than trusted
     * @param routeLength  steps in the route this heuristic actually produced
     * @param routeOptimal whether that route is a shortest one; false is only possible with an
     *                     inadmissible heuristic, and is the price {@link Heuristic#INFLATED} pays
     */
    public record Lens(UUID mazeId, int rows, int cols, Heuristic heuristic, Point start,
                       Point goal, int optimalCost, int reachable, int mustExpand, int tie,
                       int never, int actualExpansions, int expandedAboveOptimal,
                       int routeLength, boolean routeOptimal, int[][] bands, String note) { }

    /** {@code null} when the maze is unknown; throws when the grid is too large to serialise. */
    public Lens forMaze(UUID mazeId, Heuristic which) {
        var cached = mazes.find(mazeId);
        if (cached == null) {
            return null;
        }
        MazeGrid grid = cached.grid();
        int cells = grid.rows() * grid.cols();
        if (cells > maxFieldCells) {
            throw new IllegalArgumentException(
                    "a " + grid.rows() + "x" + grid.cols() + " heuristic lens is " + cells
                            + " cells, over the " + maxFieldCells + "-cell payload cap — the same "
                            + "bound the distance field uses, and for the same reason: the sweep "
                            + "is linear, the JSON is not.");
        }

        Point start = grid.start();
        Point goal = grid.goal();
        int[][] fromStart = MazeMetrics.distancesFrom(grid, start);
        int optimal = MazeMetrics.distancesFrom(grid, goal)[start.row()][start.col()];

        ToDoubleBiFunction<Point, Point> h = switch (which) {
            case LANDMARK -> LandmarkHeuristic.precompute(grid, 4)::estimate;
            case INFLATED -> (from, to) -> INFLATION * Heuristics.MANHATTAN.applyAsDouble(from, to);
            case MANHATTAN -> Heuristics.MANHATTAN;
            // eps small enough that eps * C* < 1 — see the enum's javadoc for why that is the
            // whole argument for optimality, and why the constant has to depend on the maze.
            case MANHATTAN_TIE_BROKEN -> Heuristics.manhattanWithTieBreaker(1.0 / (cells + 1.0));
        };

        MazeReplay.Replay replay = MazeReplay.record(
                new AStarSolver(h), grid, start, goal, new MazeStats());
        Set<Point> expanded = new HashSet<>(replay.expansions());

        int[][] bands = new int[grid.rows()][grid.cols()];
        int reachable = 0;
        int mustExpand = 0;
        int tie = 0;
        int never = 0;
        int expandedAbove = 0;
        for (int r = 0; r < grid.rows(); r++) {
            for (int c = 0; c < grid.cols(); c++) {
                if (fromStart[r][c] < 0 || optimal < 0) {
                    bands[r][c] = BAND_UNREACHABLE;
                    continue;
                }
                reachable++;
                Point p = new Point(r, c);
                double f = fromStart[r][c] + h.applyAsDouble(p, goal);
                double delta = f - optimal;
                if (delta < -EPSILON) {
                    bands[r][c] = BAND_MUST_EXPAND;
                    mustExpand++;
                } else if (delta <= EPSILON) {
                    bands[r][c] = BAND_TIE;
                    tie++;
                } else {
                    bands[r][c] = BAND_NEVER;
                    never++;
                    if (expanded.contains(p)) {
                        expandedAbove++;
                    }
                }
            }
        }

        int routeLength = replay.path().isEmpty() ? -1 : replay.path().size() - 1;
        boolean routeOptimal = routeLength == optimal;
        return new Lens(mazeId, grid.rows(), grid.cols(), which, start, goal, optimal, reachable,
                mustExpand, tie, never, expanded.size(), expandedAbove, routeLength, routeOptimal,
                bands, note(which, mustExpand, tie, reachable, expanded.size(), expandedAbove,
                        routeLength, routeOptimal, optimal));
    }

    private static String note(Heuristic which, int mustExpand, int tie, int reachable,
                               int actual, int expandedAbove, int routeLength,
                               boolean routeOptimal, int optimalCost) {
        StringBuilder note = new StringBuilder();
        note.append(mustExpand).append(" of ").append(reachable)
                .append(" reachable cells sit below the optimal cost, so A* has no choice but to "
                        + "expand them whatever its tie-breaking. ");
        if (tie > mustExpand) {
            note.append("The tie band is larger still (").append(tie)
                    .append(" cells at exactly the optimal cost), which means the tie-breaking "
                            + "rule decides more of this search than the heuristic does. ");
        }
        note.append("A* actually expanded ").append(actual).append(". ");
        if (expandedAbove > 0 && which == Heuristic.INFLATED) {
            note.append(expandedAbove)
                    .append(" cells above the optimal cost were expanded — exactly what an "
                            + "inadmissible heuristic buys and costs. The search is cheaper, and "
                            + "the route is ")
                    .append(routeOptimal
                            ? "still a shortest one here, though nothing guarantees that on the "
                                    + "next maze. "
                            : routeLength + " steps against a best of " + optimalCost
                                    + " — no longer optimal. ");
        } else if (expandedAbove > 0 && which == Heuristic.MANHATTAN_TIE_BROKEN) {
            note.append(expandedAbove)
                    .append(" cells above the optimal cost were expanded, which is what scaling h "
                            + "by 1 + eps costs: the tie band moved above C*, and A* works "
                            + "through some of it while the goal is still undiscovered. The "
                            + "route is ")
                    .append(routeOptimal
                            ? "nevertheless optimal, and provably so — eps * C* is below one "
                                    + "whole step and costs are integers. "
                            : routeLength + " steps against a best of " + optimalCost
                                    + ", which means eps was too large for this maze. ");
        } else if (expandedAbove > 0) {
            note.append("WARNING: ").append(expandedAbove).append(" cells above the optimal cost "
                    + "were expanded, which should be impossible with an admissible heuristic — "
                    + "either the heuristic overestimates or the search is wrong. ");
        } else {
            note.append("No cell above the optimal cost was expanded, as an admissible heuristic "
                    + "guarantees. ");
        }
        if (which == Heuristic.MANHATTAN && tie > mustExpand) {
            note.append("Try MANHATTAN_TIE_BROKEN to see what that tie band is worth: the same "
                    + "heuristic scaled by 1 + 1/cells pushes every tie above the optimal cost, "
                    + "so A* stops expanding them — and the scaling stays below one whole step, "
                    + "so the route is still optimal. ");
        }
        if (which == Heuristic.MANHATTAN) {
            note.append("Try the landmark heuristic: measured, it drops the mandatory band from "
                    + "925 cells to 0 on a 31x31 perfect maze and cuts real expansions by "
                    + "1.8x to 5.5x.");
        }
        if (which == Heuristic.MANHATTAN_TIE_BROKEN) {
            note.append("Ties are broken toward the straight line, so the ")
                    .append(tie)
                    .append(" cells still at exactly the optimal cost are the ones no bias can "
                            + "separate. Compare with heuristic=MANHATTAN on the same maze.");
        }
        return note.toString().trim();
    }

    /** The band names, for a client that would rather not hardcode integers. */
    public static List<String> bandNames() {
        return List.of("mustExpand", "tie", "never");
    }
}
