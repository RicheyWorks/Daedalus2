// SPDX-License-Identifier: MIT

package com.daedalus.theory;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.Point;

import java.util.ArrayList;
import java.util.List;

/**
 * Where to put {@code k} facilities so the worst-served node is as close as possible — the metric
 * <b>k-center</b> problem (CLRS Ch. 35 approximation, Ch. 34 for the hardness).
 *
 * <p>This is the placement question behind edge caches, replica sets, rack anchors and CDN points
 * of presence: given a topology, choose {@code k} locations minimising the <em>covering radius</em>
 * — the distance from the farthest node to its nearest facility.
 *
 * <h3>Why greedy, and why that's respectable</h3>
 *
 * <p>k-center is NP-hard, so an exact answer is out of reach at any useful size. The
 * farthest-first greedy (Gonzalez): take any node, then repeatedly add the node currently
 * <em>worst served</em> by the facilities chosen so far. That is a <b>2-approximation</b> — the
 * radius is never worse than twice optimal — and no polynomial algorithm can guarantee better than
 * 2 unless P = NP, so the simple algorithm is also the best available guarantee.
 *
 * <p>The greedy step is exactly {@code MazeMetrics.farthestFrom} generalised to a set, and it is
 * the same rule {@code solver.LandmarkHeuristic} uses to spread its landmarks — which is not a
 * coincidence: both want points that are far from each other and from everything else.
 *
 * <p>Cost is {@code k} breadth-first sweeps. Deterministic: ties break row-major.
 *
 * <h3>Two behaviours, because "unreachable" means two different things</h3>
 *
 * <p>Both variants exist because both consumers do. In a <b>dungeon</b> (placing treasure,
 * save points or boss rooms across a level) unreachable cells are solid rock — not places, so
 * they should neither be served nor distort the radius. In a <b>partitioned network</b>
 * (placing replicas or edge caches after node failures have fragmented the topology) every
 * component still holds real nodes that need serving. The same greedy gives the wrong answer
 * for one of those two whichever way it is written, so it is written both ways.
 *
 * <p>{@link #kCenter} stays inside the component reachable from its first pick — the dungeon
 * reading.
 *
 * <p>It is wrong when the graph is a fragmented <em>network</em>, where every component holds
 * real nodes that still need serving. Measured on a 16×16 tree severed along one column —
 * cutting a spanning tree at 16 edges shatters it into 14 components of sizes
 * {@code [114, 43, 30, 22, 14, 12, 5, 5, 3, 3, 2, 1, 1, 1]} rather than halving it:
 *
 * <pre>
 *   k     kCenter                    kCenterAcrossComponents
 *         radius / cells served      radius / cells served
 *    1      82 / 114 of 256             82 / 114 of 256
 *    2      44 / 114                    82 / 126
 *    3      25 / 114                    82 / 169
 *    5      18 / 114                    82 / 192
 *    8      12 / 114                    82 / 212
 *   12       7 / 114                    82 / 254
 * </pre>
 *
 * <p>Read the left column carefully: adding facilities drives the covering radius steadily
 * down — 82 to 7, a placement that looks better and better — while coverage never moves off
 * <b>114 of 256 cells</b>. Every one of those extra facilities is refining service inside the
 * one component the greedy can see, and the other 142 cells are no closer to anything.
 * Nothing is lying; {@code servedCells} is right there in the result. But a quality metric
 * that <em>improves</em> while more than half the graph stays unreachable is a trap worth
 * naming. The right column pays radius (a flat 82, since it now spans components) to buy
 * coverage.
 *
 * <p>{@link #kCenterAcrossComponents} is the variant for that case: it ranks unreachable cells
 * as infinitely badly served, which is what the k-center objective actually says, so the greedy
 * spends its first picks reaching new components before refining within them.
 */
public final class FacilityPlacement {

    private FacilityPlacement() {
    }

    /**
     * A chosen set of facility locations.
     *
     * @param facilities     the chosen cells, in the order the greedy picked them
     * @param coveringRadius distance from the worst-served reachable cell to its nearest facility
     * @param servedCells    how many cells the facilities actually reach
     */
    public record Placement(List<Point> facilities, int coveringRadius, int servedCells) {
        public Placement {
            facilities = List.copyOf(facilities);
        }
    }

    /**
     * Place {@code k} facilities by farthest-first greedy.
     *
     * <p>Fewer than {@code k} may be returned when the component runs out of distinct useful
     * locations — once every reachable cell is a facility, more cannot help.
     *
     * @throws IllegalArgumentException if {@code k < 1}
     */
    public static Placement kCenter(MazeGrid grid, int k) {
        if (k < 1) {
            throw new IllegalArgumentException("Need at least one facility, got " + k);
        }
        int rows = grid.rows();
        int cols = grid.cols();

        // Any starting point preserves the 2-approximation; an extreme one tends to do better.
        Point first = MazeMetrics.farthestFrom(grid, MazeMetrics.largestComponentCell(grid));
        List<Point> facilities = new ArrayList<>();
        facilities.add(first);

        int[][] nearest = MazeMetrics.distancesFrom(grid, first);

        while (facilities.size() < k) {
            Point worstServed = null;
            int worstDistance = 0;
            for (int r = 0; r < rows; r++) {
                for (int c = 0; c < cols; c++) {
                    if (nearest[r][c] > worstDistance) {
                        worstDistance = nearest[r][c];
                        worstServed = new Point(r, c);
                    }
                }
            }
            if (worstServed == null) {
                break; // every reachable cell is already a facility
            }
            facilities.add(worstServed);
            mergeNearest(nearest, MazeMetrics.distancesFrom(grid, worstServed), rows, cols);
        }

        int radius = 0;
        int served = 0;
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                if (nearest[r][c] >= 0) {
                    served++;
                    radius = Math.max(radius, nearest[r][c]);
                }
            }
        }
        return new Placement(facilities, radius, served);
    }

    /**
     * Farthest-first greedy that treats a cell it cannot reach as <b>infinitely badly served</b>,
     * so facilities spread across disconnected components instead of clustering in whichever one
     * the first pick landed in.
     *
     * <p>This is not a heuristic tweak — it is what the k-center objective already says. The
     * cost of a placement is the distance from the worst-served node to its nearest facility,
     * and for a node no facility can reach that distance is infinite. {@link #kCenter} scores
     * such nodes as {@code -1} and therefore never selects them; ranking them above every finite
     * distance restores the intended ordering. The consequence is that the greedy spends its
     * early picks <em>reaching</em> new components, and only refines within components once every
     * component holds a facility.
     *
     * <p>On the severed 16×16 grid described in the class javadoc, at {@code k = 3} this turns
     * {@code (radius 25, 114 of 256 cells served)} into {@code (radius 82, 169 served)} — it
     * trades a worse worst-case walk for reaching two further components.
     *
     * <p>The 2-approximation guarantee is per-component: within each component the selection is
     * still Gonzalez's greedy. Across components no ratio is claimed, because with fewer
     * facilities than components the objective is unbounded — some component is unreachable no
     * matter what. Check {@link Placement#servedCells()} to see how much of the graph was
     * covered.
     *
     * <p>Use {@link #kCenter} when unreachable means "not a place" (solid rock). Use this when
     * unreachable means "a node we still have to serve" (a partitioned network).
     *
     * @throws IllegalArgumentException if {@code k < 1}
     */
    public static Placement kCenterAcrossComponents(MazeGrid grid, int k) {
        if (k < 1) {
            throw new IllegalArgumentException("Need at least one facility, got " + k);
        }
        int rows = grid.rows();
        int cols = grid.cols();

        Point first = MazeMetrics.farthestFrom(grid, MazeMetrics.largestComponentCell(grid));
        List<Point> facilities = new ArrayList<>();
        facilities.add(first);
        int[][] nearest = MazeMetrics.distancesFrom(grid, first);

        while (facilities.size() < k) {
            Point worstServed = null;
            int worstDistance = 0;
            boolean worstIsUnreached = false;

            for (int r = 0; r < rows; r++) {
                for (int c = 0; c < cols; c++) {
                    int d = nearest[r][c];
                    if (d < 0) {
                        // Unreachable outranks every finite distance. First one wins, so the
                        // row-major tie-break still makes this deterministic.
                        if (!worstIsUnreached) {
                            worstIsUnreached = true;
                            worstServed = new Point(r, c);
                        }
                    } else if (!worstIsUnreached && d > worstDistance) {
                        worstDistance = d;
                        worstServed = new Point(r, c);
                    }
                }
            }
            if (worstServed == null) {
                break; // every cell in the grid is already a facility
            }
            facilities.add(worstServed);
            mergeNearest(nearest, MazeMetrics.distancesFrom(grid, worstServed), rows, cols);
        }

        int radius = 0;
        int served = 0;
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                if (nearest[r][c] >= 0) {
                    served++;
                    radius = Math.max(radius, nearest[r][c]);
                }
            }
        }
        return new Placement(facilities, radius, served);
    }

    /**
     * Covering radius of a caller-chosen facility set — for scoring a placement you already have
     * against what {@link #kCenter} would pick. {@code -1} if nothing is reachable.
     */
    public static int coveringRadius(MazeGrid grid, List<Point> facilities) {
        if (facilities.isEmpty()) {
            return -1;
        }
        int rows = grid.rows();
        int cols = grid.cols();
        int[][] nearest = MazeMetrics.distancesFrom(grid, facilities.get(0));
        for (int i = 1; i < facilities.size(); i++) {
            mergeNearest(nearest, MazeMetrics.distancesFrom(grid, facilities.get(i)), rows, cols);
        }
        int radius = -1;
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                radius = Math.max(radius, nearest[r][c]);
            }
        }
        return radius;
    }

    /** Keep the smaller of two distance fields per cell, treating {@code -1} as unreachable. */
    private static void mergeNearest(int[][] nearest, int[][] candidate, int rows, int cols) {
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                int other = candidate[r][c];
                if (other >= 0 && (nearest[r][c] < 0 || other < nearest[r][c])) {
                    nearest[r][c] = other;
                }
            }
        }
    }
}
