// SPDX-License-Identifier: MIT

package com.daedalus.engine;

import com.daedalus.graph.MazeGraph;
import com.daedalus.model.Point;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Queue;
import java.util.Random;

/**
 * The inverse of {@link Braider}: closes passages so a maze gets harder, without ever
 * disconnecting it.
 *
 * <p>ADR-006 left wall-closing out of living-mazes v1 because opening is safe by construction
 * and closing is not — sealing a bridge splits the graph and can strand a player. The named
 * re-fire trigger was a connectivity proof per closure. The proof used here is a
 * <em>spanning-forest complement</em>, not a cut-vertex check (the ADR's wording): closing a
 * wall removes an <em>edge</em>, so the relevant certificate is a cut-edge / bridge. A
 * spanning forest of the habitable graph is computed by BFS in the grid's stable neighbour
 * order; every edge <em>not</em> in that forest can be removed at once and the forest still
 * connects every habitable cell. That is a simultaneously-safe set — stronger than "each
 * edge is a non-bridge on its own", which is not safe as a batch (two parallel paths are
 * each a non-bridge; closing both disconnects).
 *
 * <p>On a perfect maze the forest is the whole edge set, so this is a no-op — the same
 * honesty ADR-007's hardest-route endpoint learned on trees. Deterministic: the forest
 * walk and the shuffle of closable edges are both seeded only through {@code seed} for the
 * shuffle; the walk itself is seedless and uses {@link MazeGrid#openNeighbors} order.
 */
public final class Sealer {

    private Sealer() {
    }

    /**
     * Outcome of a seal pass.
     *
     * @param closableBefore non-forest passages present when the pass started
     * @param wallsClosed    walls actually sealed
     * @param closableAfter  non-forest passages remaining afterwards
     */
    public record SealResult(int closableBefore, int wallsClosed, int closableAfter) {
    }

    /**
     * Close {@code factor} of the maze's simultaneously-safe extra passages.
     *
     * @param grid   maze to harden, modified in place
     * @param factor fraction of closable passages to seal, clamped to {@code [0.0, 1.0]};
     *               {@code 0.0} is a no-op, {@code 1.0} reduces the maze to a spanning forest
     * @param seed   seed for the deterministic shuffle of which extras go first
     */
    public static SealResult seal(MazeGrid grid, double factor, long seed) {
        double clamped = Math.max(0.0, Math.min(1.0, factor));
        List<Point[]> closable = closablePassages(grid);
        int before = closable.size();
        if (clamped == 0.0 || before == 0) {
            return new SealResult(before, 0, before);
        }

        Random rng = new Random(seed);
        Collections.shuffle(closable, rng);
        int target = (int) Math.round(clamped * before);

        int closed = 0;
        for (Point[] edge : closable) {
            if (closed >= target) {
                break;
            }
            grid.seal(edge[0], edge[1]);
            closed++;
        }
        return new SealResult(before, closed, closablePassages(grid).size());
    }

    /** Close every extra passage this pass can reach — the maze becomes a spanning forest. */
    public static SealResult seal(MazeGrid grid, long seed) {
        return seal(grid, 1.0, seed);
    }

    /**
     * Passages that are not in a spanning forest of the habitable graph, in row-major
     * discovery order. Empty on a tree. Public so the living-maze ticker can apply the
     * same "at least one while any remain" rule erosion uses, without sealing when the
     * caller asked for a zero factor.
     */
    public static List<Point[]> closablePassages(MazeGrid grid) {
        boolean[] inForest = forestEdges(grid);
        List<Point[]> out = new ArrayList<>();
        int cols = grid.cols();
        for (int r = 0; r < grid.rows(); r++) {
            for (int c = 0; c < grid.cols(); c++) {
                Point p = new Point(r, c);
                for (Point n : grid.openNeighbors(p)) {
                    if (!isBefore(p, n)) {
                        continue; // each undirected edge once
                    }
                    if (!inForest[edgeKey(p, n, cols)]) {
                        out.add(new Point[]{p, n});
                    }
                }
            }
        }
        return out;
    }

    /**
     * Undirected edges of a spanning forest, keyed by {@link #edgeKey}. Habitable cells
     * (degree &gt; 0) are visited by BFS from each unvisited seed in row-major order;
     * rock (degree 0) is skipped, so a dungeon keeps its rooms and never "serves" solid
     * stone. Neighbour order is {@link MazeGrid#openNeighbors}, which is stable.
     */
    private static boolean[] forestEdges(MazeGrid grid) {
        int cols = grid.cols();
        int nodes = grid.rows() * cols;
        // Four possible undirected edges per cell (N/E/S/W), but we key by the lesser
        // endpoint × 4 + direction-to-greater, so nodes * 4 is a tight upper bound.
        boolean[] inForest = new boolean[nodes * 4];
        boolean[] seen = new boolean[nodes];
        MazeGraph graph = new MazeGraph(grid);
        int[] buf = new int[graph.maxDegree()];
        Queue<Integer> q = new ArrayDeque<>();

        for (int start = 0; start < nodes; start++) {
            if (seen[start] || graph.neighbors(start, buf) == 0) {
                continue;
            }
            seen[start] = true;
            q.add(start);
            while (!q.isEmpty()) {
                int u = q.remove();
                int degree = graph.neighbors(u, buf);
                for (int i = 0; i < degree; i++) {
                    int v = buf[i];
                    if (seen[v]) {
                        continue;
                    }
                    seen[v] = true;
                    inForest[edgeKey(u, v, cols)] = true;
                    q.add(v);
                }
            }
        }
        return inForest;
    }

    /** Pack an undirected grid edge into {@code minId * 4 + dir}, dir in {0=N,1=E,2=S,3=W}. */
    private static int edgeKey(Point a, Point b, int cols) {
        return edgeKey(a.row() * cols + a.col(), b.row() * cols + b.col(), cols);
    }

    private static int edgeKey(int u, int v, int cols) {
        int lo = Math.min(u, v);
        int hi = Math.max(u, v);
        int dr = (hi / cols) - (lo / cols);
        int dc = (hi % cols) - (lo % cols);
        int dir = dr == -1 ? 0 : dc == 1 ? 1 : dr == 1 ? 2 : 3;
        return lo * 4 + dir;
    }

    private static boolean isBefore(Point a, Point b) {
        return a.row() != b.row() ? a.row() < b.row() : a.col() <= b.col();
    }
}
