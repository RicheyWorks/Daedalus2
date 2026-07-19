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
 * <p>Cost is {@code k} breadth-first sweeps. Operates on the connected component reachable from
 * the first facility, so unreachable cells (a dungeon's solid rock) are simply not served and do
 * not distort the radius. Deterministic: ties break row-major.
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
        Point first = MazeMetrics.farthestFrom(grid, new Point(0, 0));
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
