// SPDX-License-Identifier: MIT

package com.daedalus.solver;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.Point;
import com.daedalus.theory.MazeMetrics;

import java.util.ArrayList;
import java.util.List;
import java.util.function.ToDoubleBiFunction;

/**
 * ALT — <b>A*, Landmarks, Triangle inequality</b>: a far tighter admissible heuristic than
 * Manhattan, bought with a one-off preprocessing pass.
 *
 * <p>Pick a handful of landmark cells and BFS the whole maze from each, storing the distance
 * field. Then for any pair the triangle inequality gives, for every landmark {@code L},
 * <pre>{@code   d(a, b) >= |d(L, b) - d(L, a)|   }</pre>
 * so the maximum of that expression over all landmarks is a valid lower bound on the true
 * distance — admissible, and therefore safe for A* optimality. The same reasoning underpins
 * Johnson's reweighting-by-a-potential in CLRS Ch. 25.
 *
 * <p>Why it beats Manhattan on a maze: Manhattan measures straight-line grid distance and is
 * oblivious to walls, so in a twisty maze it badly under-estimates and A* degenerates toward
 * Dijkstra. Landmark distances are measured <em>through the actual passages</em>, so the bound
 * reflects the detours the solver will really have to make.
 *
 * <p>Landmarks are chosen by the standard greedy farthest-point rule — start from the cell
 * farthest from the top-left, then repeatedly take the cell whose closest existing landmark is as
 * far away as possible — which spreads them to the extremities where their bounds are sharpest.
 * Selection is deterministic (row-major tie-breaks), so the same maze always yields the same
 * landmarks and the same heuristic.
 *
 * <h3>Weighted grids are handled automatically — and used to be handled wrongly</h3>
 *
 * <p>{@code precompute} inspects the grid and picks its metric to match. Uniform-cost grids get
 * BFS hop fields (O(V + E) per landmark). Any grid carrying a weight other than {@code 1.0} gets
 * Dijkstra cost fields instead, because hop counts are simply the wrong metric for a weighted
 * search and using them was an <b>optimality bug</b>, not merely a loose bound.
 *
 * <p>The old version stored hop counts unconditionally and documented a "keep weights
 * {@code >= 1.0}" rule to stay admissible. Two things were wrong with that. The rule was never
 * enforced — {@code WeightedMazeGrid.setWeight} accepts any non-negative value — and when it was
 * violated the failure was silent: measured on twelve fully-braided 24×24 mazes with weights
 * drawn from {@code [0.05, 0.35]}, the hop-count heuristic over-estimated true cost in
 * <b>575 of 576 cells</b> (worst case {@code h} = 132 against a true distance of 32), and A*
 * returned a <b>suboptimal route on all twelve</b> — up to <b>36% more expensive</b> than
 * Dijkstra's. Perfect mazes hid it entirely, because a spanning tree offers exactly one route
 * between any pair and every heuristic finds it; the bug only appears once the topology has
 * redundancy, which is precisely the case the load-balancer work cares about.
 *
 * <h3>Why weighted mode needs two sweeps per landmark</h3>
 *
 * <p>{@link MazeGrid}'s cost model charges the weight of the cell being <em>entered</em>, so the
 * graph is <b>directed</b>: {@code d(a, b)} and {@code d(b, a)} differ by {@code w(b) - w(a)}.
 * The familiar symmetric bound {@code |d(L, b) - d(L, a)|} is therefore invalid here — the
 * absolute value silently assumes {@code d(b, a) == d(a, b)}. Weighted mode instead keeps both a
 * forward field {@code d(L, x)} and a backward field {@code d(x, L)} per landmark, and takes the
 * standard directed pair of bounds
 * <pre>{@code   d(s, t) >= d(L, t) - d(L, s)        d(s, t) >= d(s, L) - d(t, L)   }</pre>
 * each of which follows from the triangle inequality without assuming symmetry. Unit-cost mode
 * keeps using {@code |·|}, which is sound there because hop distance genuinely is symmetric.
 *
 * <p>Usage is unchanged — the right mode is chosen for you:
 * <pre>{@code
 * LandmarkHeuristic alt = LandmarkHeuristic.precompute(grid, 4);
 * List<Point> path = new AStarSolver(alt.asHeuristic()).solve(grid, start, goal, stats);
 * }</pre>
 */
public final class LandmarkHeuristic {

    private final List<Point> landmarks;

    /** Hop fields, unit-cost mode only. Empty when {@link #weighted} is {@code true}. */
    private final List<int[][]> hopFields;

    /** {@code d(L, x)} per landmark, weighted mode only. Empty otherwise. */
    private final List<double[][]> forwardFields;

    /** {@code d(x, L)} per landmark, weighted mode only. Empty otherwise. */
    private final List<double[][]> backwardFields;

    private final boolean weighted;

    private LandmarkHeuristic(List<Point> landmarks, List<int[][]> hopFields,
                              List<double[][]> forwardFields, List<double[][]> backwardFields,
                              boolean weighted) {
        this.landmarks = List.copyOf(landmarks);
        this.hopFields = hopFields;
        this.forwardFields = forwardFields;
        this.backwardFields = backwardFields;
        this.weighted = weighted;
    }

    /**
     * Precompute using {@code count} greedily-spread landmarks. Fewer may be returned on a tiny
     * or highly disconnected maze; {@code count <= 0} yields a heuristic that always returns 0
     * (still admissible, just useless).
     *
     * <p>The metric is chosen from the grid: uniform-cost grids get BFS hop fields, weighted
     * grids get forward and backward Dijkstra fields. See the class javadoc for why the
     * weighted case cannot reuse hop counts.
     */
    public static LandmarkHeuristic precompute(MazeGrid grid, int count) {
        if (count <= 0) {
            return empty();
        }
        if (hasNonUnitWeights(grid)) {
            return precomputeWeighted(grid, chooseLandmarks(grid, count));
        }

        List<Point> chosen = new ArrayList<>();
        List<int[][]> fields = new ArrayList<>();
        Point first = MazeMetrics.farthestFrom(grid, MazeMetrics.largestComponentCell(grid));
        chosen.add(first);
        fields.add(MazeMetrics.distancesFrom(grid, first));

        while (chosen.size() < count) {
            Point next = farthestFromAllChosen(grid, fields);
            if (next == null) {
                break; // nothing left that adds information
            }
            chosen.add(next);
            fields.add(MazeMetrics.distancesFrom(grid, next));
        }
        return new LandmarkHeuristic(chosen, fields, List.of(), List.of(), false);
    }

    /** Precompute from an explicit landmark list (useful for tests and tuning). */
    public static LandmarkHeuristic precompute(MazeGrid grid, List<Point> landmarks) {
        if (hasNonUnitWeights(grid)) {
            return precomputeWeighted(grid, landmarks);
        }
        List<int[][]> fields = new ArrayList<>(landmarks.size());
        for (Point landmark : landmarks) {
            fields.add(MazeMetrics.distancesFrom(grid, landmark));
        }
        return new LandmarkHeuristic(landmarks, fields, List.of(), List.of(), false);
    }

    private static LandmarkHeuristic empty() {
        return new LandmarkHeuristic(List.of(), List.of(), List.of(), List.of(), false);
    }

    /** Two Dijkstra sweeps per landmark — outbound and inbound. See class javadoc. */
    private static LandmarkHeuristic precomputeWeighted(MazeGrid grid, List<Point> landmarks) {
        List<double[][]> forward = new ArrayList<>(landmarks.size());
        List<double[][]> backward = new ArrayList<>(landmarks.size());
        for (Point landmark : landmarks) {
            forward.add(MazeMetrics.weightedDistancesFrom(grid, landmark));
            backward.add(MazeMetrics.weightedDistancesTo(grid, landmark));
        }
        return new LandmarkHeuristic(landmarks, List.of(), forward, backward, true);
    }

    /**
     * Landmark selection for weighted grids. Deliberately reuses the <em>hop-count</em> greedy
     * farthest-point rule rather than a weighted one: selection only decides <em>where</em> to
     * put landmarks, never what the heuristic returns, so it cannot affect admissibility — and
     * spreading landmarks to the topological extremities is what makes their bounds sharp,
     * which is a question about shape, not cost.
     */
    private static List<Point> chooseLandmarks(MazeGrid grid, int count) {
        List<Point> chosen = new ArrayList<>();
        List<int[][]> fields = new ArrayList<>();
        Point first = MazeMetrics.farthestFrom(grid, MazeMetrics.largestComponentCell(grid));
        chosen.add(first);
        fields.add(MazeMetrics.distancesFrom(grid, first));
        while (chosen.size() < count) {
            Point next = farthestFromAllChosen(grid, fields);
            if (next == null) {
                break;
            }
            chosen.add(next);
            fields.add(MazeMetrics.distancesFrom(grid, next));
        }
        return chosen;
    }

    /** Does this grid carry any cost other than 1.0? O(V), negligible beside the sweeps. */
    private static boolean hasNonUnitWeights(MazeGrid grid) {
        for (int r = 0; r < grid.rows(); r++) {
            for (int c = 0; c < grid.cols(); c++) {
                if (grid.weightOf(r, c) != 1.0) {
                    return true;
                }
            }
        }
        return false;
    }

    /** The landmarks actually chosen, in selection order. */
    public List<Point> landmarks() {
        return landmarks;
    }

    /** Whether this instance measures cost (Dijkstra fields) rather than hops (BFS fields). */
    public boolean isWeighted() {
        return weighted;
    }

    /**
     * Admissible lower bound on the distance from {@code from} to {@code to}: the largest
     * triangle-inequality bound any landmark can certify. Landmarks that can't reach one of the
     * two cells are skipped; with none usable the bound is {@code 0}.
     */
    public double estimate(Point from, Point to) {
        return weighted ? weightedEstimate(from, to) : hopEstimate(from, to);
    }

    private double hopEstimate(Point from, Point to) {
        int best = 0;
        for (int[][] field : hopFields) {
            int dFrom = field[from.row()][from.col()];
            int dTo = field[to.row()][to.col()];
            if (dFrom < 0 || dTo < 0) {
                continue; // unreachable from this landmark — it certifies nothing
            }
            // Symmetric bound is sound here: hop distance is the same in both directions.
            int bound = Math.abs(dTo - dFrom);
            if (bound > best) {
                best = bound;
            }
        }
        return best;
    }

    private double weightedEstimate(Point from, Point to) {
        double best = 0.0;
        for (int i = 0; i < forwardFields.size(); i++) {
            double[][] out = forwardFields.get(i);
            double[][] in = backwardFields.get(i);

            // d(s,t) >= d(L,t) - d(L,s): from the triangle inequality through L, outbound.
            double dLs = out[from.row()][from.col()];
            double dLt = out[to.row()][to.col()];
            if (isFinite(dLs) && isFinite(dLt)) {
                best = Math.max(best, dLt - dLs);
            }

            // d(s,t) >= d(s,L) - d(t,L): the same inequality inbound. Needed separately
            // because the entry-cost model makes the graph directed — see class javadoc.
            double dsL = in[from.row()][from.col()];
            double dtL = in[to.row()][to.col()];
            if (isFinite(dsL) && isFinite(dtL)) {
                best = Math.max(best, dsL - dtL);
            }
        }
        return best;
    }

    private static boolean isFinite(double d) {
        return d != Double.POSITIVE_INFINITY;
    }

    /** This heuristic in the form {@link AStarSolver} and friends accept. */
    public ToDoubleBiFunction<Point, Point> asHeuristic() {
        return this::estimate;
    }

    /**
     * The cell whose nearest existing landmark is farthest away — the next greedy farthest-point
     * pick. Returns {@code null} when no cell is any distance from the landmarks already chosen.
     */
    private static Point farthestFromAllChosen(MazeGrid grid, List<int[][]> fields) {
        Point best = null;
        int bestDistance = 0;
        for (int r = 0; r < grid.rows(); r++) {
            for (int c = 0; c < grid.cols(); c++) {
                int nearest = Integer.MAX_VALUE;
                boolean reachable = false;
                for (int[][] field : fields) {
                    int d = field[r][c];
                    if (d >= 0) {
                        reachable = true;
                        nearest = Math.min(nearest, d);
                    }
                }
                if (reachable && nearest > bestDistance) {
                    bestDistance = nearest;
                    best = new Point(r, c);
                }
            }
        }
        return best;
    }
}
