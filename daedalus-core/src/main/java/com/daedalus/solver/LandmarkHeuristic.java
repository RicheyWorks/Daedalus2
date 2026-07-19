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
 * <p><b>Unit cost only.</b> The distance fields are BFS hop counts, so this is admissible on a
 * plain {@link MazeGrid}. It is <em>not</em> valid for a
 * {@link com.daedalus.engine.WeightedMazeGrid} carrying weights above {@code 1.0} — hop counts
 * would over-estimate true cost and break optimality. Use Dijkstra, or a weight-scaled heuristic,
 * for those.
 *
 * <p>Usage:
 * <pre>{@code
 * LandmarkHeuristic alt = LandmarkHeuristic.precompute(grid, 4);
 * List<Point> path = new AStarSolver(alt.asHeuristic()).solve(grid, start, goal, stats);
 * }</pre>
 */
public final class LandmarkHeuristic {

    private final List<Point> landmarks;
    private final List<int[][]> distanceFields;

    private LandmarkHeuristic(List<Point> landmarks, List<int[][]> distanceFields) {
        this.landmarks = List.copyOf(landmarks);
        this.distanceFields = distanceFields;
    }

    /**
     * Precompute using {@code count} greedily-spread landmarks. Fewer may be returned on a tiny
     * or highly disconnected maze; {@code count <= 0} yields a heuristic that always returns 0
     * (still admissible, just useless).
     */
    public static LandmarkHeuristic precompute(MazeGrid grid, int count) {
        List<Point> chosen = new ArrayList<>();
        List<int[][]> fields = new ArrayList<>();
        if (count <= 0) {
            return new LandmarkHeuristic(chosen, fields);
        }

        Point first = MazeMetrics.farthestFrom(grid, new Point(0, 0));
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
        return new LandmarkHeuristic(chosen, fields);
    }

    /** Precompute from an explicit landmark list (useful for tests and tuning). */
    public static LandmarkHeuristic precompute(MazeGrid grid, List<Point> landmarks) {
        List<int[][]> fields = new ArrayList<>(landmarks.size());
        for (Point landmark : landmarks) {
            fields.add(MazeMetrics.distancesFrom(grid, landmark));
        }
        return new LandmarkHeuristic(landmarks, fields);
    }

    /** The landmarks actually chosen, in selection order. */
    public List<Point> landmarks() {
        return landmarks;
    }

    /**
     * Admissible lower bound on the passage distance from {@code from} to {@code to}: the largest
     * triangle-inequality bound any landmark can certify. Landmarks that can't reach one of the
     * two cells are skipped; with none usable the bound is {@code 0}.
     */
    public double estimate(Point from, Point to) {
        int best = 0;
        for (int[][] field : distanceFields) {
            int dFrom = field[from.row()][from.col()];
            int dTo = field[to.row()][to.col()];
            if (dFrom < 0 || dTo < 0) {
                continue; // unreachable from this landmark — it certifies nothing
            }
            int bound = Math.abs(dTo - dFrom);
            if (bound > best) {
                best = bound;
            }
        }
        return best;
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
