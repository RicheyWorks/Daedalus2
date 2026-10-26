// SPDX-License-Identifier: MIT

package com.daedalus.world.labyrinth;

import com.daedalus.engine.MazeGenerator;
import com.daedalus.engine.MazeGrid;
import com.daedalus.model.Point;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.SplittableRandom;

/**
 * LAB08 Folding Maze boss: a living maze whose "mimic" walls fold open and shut on a schedule, while the exit always
 * stays reachable from where the player stands.
 *
 * <p>The maze comes from any Daedalus {@link MazeGenerator} (Kruskal's, Growing Tree and the rest of the engine). Mimic
 * walls are picked from both kinds of edge: half are passages of the perfect maze (closing one could cut the player
 * off) and half are solid walls (opening one makes a loop). Every fold flips mimics, and before any wall closes the
 * fold proves with a breadth-first search that the player can still reach the exit. A wall that would trap the player
 * is <b>vetoed</b> and stays open. That veto is the realm rule "restore an exit without destroying it".
 *
 * <p>Two schedules:
 * <ul>
 *   <li>{@link #fold(Point)}: a seeded flip of each mimic, the background breathing of the maze;</li>
 *   <li>{@link #bossFold(Point)}: the boss plays to lengthen the player's shortest route, greedily closing the mimic
 *       that hurts most and opening the one that helps least, under the same reachability proof.</li>
 * </ul>
 * Pure {@code java.*} plus the maze engine. Deterministic from (generator, size, seed). The host owns the wall actors.
 */
public final class FoldingMaze {

    /** A wall between two orthogonally adjacent cells, stored with {@code a} before {@code b}. */
    public record Wall(Point a, Point b) {
        public Wall {
            if (a == null || b == null || a.manhattan(b) != 1) {
                throw new IllegalArgumentException("a wall joins two adjacent cells");
            }
            if (a.row() > b.row() || (a.row() == b.row() && a.col() > b.col())) {
                Point t = a;
                a = b;
                b = t;
            }
        }
    }

    /** One fold: which mimics opened, which closed, which closes were vetoed, and the player's route length after it. */
    public record Fold(int index, List<Wall> opened, List<Wall> closed, List<Wall> vetoed, int routeLength) {
        public Fold {
            opened = List.copyOf(opened);
            closed = List.copyOf(closed);
            vetoed = List.copyOf(vetoed);
        }
    }

    public static final int MAX_SIDE = 64;
    public static final int MAX_MIMICS = 256;

    private final MazeGrid grid;
    private final List<Wall> mimics;
    private final boolean[] open;
    private final SplittableRandom rng;
    private int folds;

    private FoldingMaze(MazeGrid grid, List<Wall> mimics, boolean[] open, SplittableRandom rng) {
        this.grid = grid;
        this.mimics = List.copyOf(mimics);
        this.open = open;
        this.rng = rng;
    }

    /**
     * Builds a folding maze: {@code gen} carves a perfect {@code rows x cols} maze from {@code seed}, then
     * {@code mimicCount} walls become mimics (half current passages, half solid walls, seeded).
     */
    public static FoldingMaze create(MazeGenerator gen, int rows, int cols, long seed, int mimicCount) {
        if (gen == null || rows < 2 || cols < 2 || rows > MAX_SIDE || cols > MAX_SIDE || mimicCount < 0
                || mimicCount > MAX_MIMICS) {
            throw new IllegalArgumentException("rows/cols 2.." + MAX_SIDE + ", mimics 0.." + MAX_MIMICS);
        }
        MazeGrid g = gen.generate(rows, cols, seed);
        SplittableRandom rng = new SplittableRandom(seed ^ 0x9E3779B97F4A7C15L);
        List<Wall> passages = new ArrayList<>(), solid = new ArrayList<>();
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                Point p = new Point(r, c);
                for (Point q : new Point[] {new Point(r, c + 1), new Point(r + 1, c)}) {
                    if (!g.inBounds(q)) {
                        continue;
                    }
                    (g.openNeighbors(p).contains(q) ? passages : solid).add(new Wall(p, q));
                }
            }
        }
        shuffle(passages, rng);
        shuffle(solid, rng);
        List<Wall> chosen = new ArrayList<>();
        int fromPassages = Math.min(passages.size(), mimicCount / 2);
        chosen.addAll(passages.subList(0, fromPassages));
        chosen.addAll(solid.subList(0, Math.min(solid.size(), mimicCount - fromPassages)));
        boolean[] open = new boolean[chosen.size()];
        for (int i = 0; i < chosen.size(); i++) {
            open[i] = i < fromPassages;
        }
        return new FoldingMaze(g, chosen, open, rng);
    }

    private static <T> void shuffle(List<T> l, SplittableRandom rng) {
        for (int i = l.size() - 1; i > 0; i--) {
            Collections.swap(l, i, rng.nextInt(i + 1));
        }
    }

    public int rows() { return grid.rows(); }
    public int cols() { return grid.cols(); }
    public Point start() { return grid.start(); }
    public Point exit() { return grid.goal(); }
    public List<Wall> mimics() { return List.copyOf(mimics); }
    public int folds() { return folds; }

    /** True if mimic {@code i} is currently open. */
    public boolean isOpen(int i) { return open[i]; }

    /** True if the two adjacent cells are joined right now. */
    public boolean passable(Point a, Point b) { return grid.openNeighbors(a).contains(b); }

    /** Shortest route length in steps from {@code from} to the exit, or -1 if there is none. */
    public int routeLength(Point from) {
        return bfs(from, exit());
    }

    /** True if the exit can be reached from {@code from} right now. */
    public boolean exitReachable(Point from) {
        return routeLength(from) >= 0;
    }

    /** The background fold: each mimic flips with probability 1/2 (seeded); closes that would trap the player are vetoed. */
    public Fold fold(Point player) {
        checkPlayer(player);
        List<Wall> opened = new ArrayList<>(), closed = new ArrayList<>(), vetoed = new ArrayList<>();
        for (int i = 0; i < mimics.size(); i++) {
            if (!rng.nextBoolean()) {
                continue;
            }
            if (open[i]) {
                tryClose(i, player, closed, vetoed);
            } else {
                set(i, true);
                opened.add(mimics.get(i));
            }
        }
        return new Fold(folds++, List.copyOf(opened), List.copyOf(closed), List.copyOf(vetoed), routeLength(player));
    }

    /**
     * The boss fold: close the one open mimic that lengthens the player's route most (if it keeps the exit reachable),
     * and open the one closed mimic that shortens it least. Ties go to the lowest index, so it is deterministic.
     */
    public Fold bossFold(Point player) {
        checkPlayer(player);
        List<Wall> opened = new ArrayList<>(), closed = new ArrayList<>(), vetoed = new ArrayList<>();
        int best = -1, bestLen = routeLength(player);
        for (int i = 0; i < mimics.size(); i++) {
            if (!open[i]) {
                continue;
            }
            set(i, false);
            int len = routeLength(player);
            set(i, true);
            if (len < 0) {
                vetoed.add(mimics.get(i));
            } else if (len > bestLen) {
                best = i;
                bestLen = len;
            }
        }
        if (best >= 0) {
            set(best, false);
            closed.add(mimics.get(best));
        }
        int pick = -1, pickLen = -1;
        for (int i = 0; i < mimics.size(); i++) {
            if (open[i] || i == best) {
                continue;
            }
            set(i, true);
            int len = routeLength(player);
            set(i, false);
            if (len > pickLen) {
                pick = i;
                pickLen = len;
            }
        }
        if (pick >= 0) {
            set(pick, true);
            opened.add(mimics.get(pick));
        }
        return new Fold(folds++, List.copyOf(opened), List.copyOf(closed), List.copyOf(vetoed), routeLength(player));
    }

    private void tryClose(int i, Point player, List<Wall> closed, List<Wall> vetoed) {
        set(i, false);
        if (exitReachable(player)) {
            closed.add(mimics.get(i));
        } else {
            set(i, true); // would trap the player: the maze restores the exit instead
            vetoed.add(mimics.get(i));
        }
    }

    private void set(int i, boolean isOpen) {
        Wall w = mimics.get(i);
        if (isOpen) {
            grid.carve(w.a(), w.b());
        } else {
            grid.seal(w.a(), w.b());
        }
        open[i] = isOpen;
    }

    private void checkPlayer(Point p) {
        if (p == null || !grid.inBounds(p)) {
            throw new IllegalArgumentException("player must stand inside the maze");
        }
    }

    private int bfs(Point from, Point to) {
        if (!grid.inBounds(from) || !grid.inBounds(to)) {
            return -1;
        }
        int cols = grid.cols();
        int[] dist = new int[grid.rows() * cols];
        Arrays.fill(dist, -1);
        ArrayDeque<Point> q = new ArrayDeque<>();
        dist[from.row() * cols + from.col()] = 0;
        q.add(from);
        while (!q.isEmpty()) {
            Point p = q.poll();
            int dp = dist[p.row() * cols + p.col()];
            if (p.equals(to)) {
                return dp;
            }
            for (Point n : grid.openNeighbors(p)) {
                int k = n.row() * cols + n.col();
                if (dist[k] < 0) {
                    dist[k] = dp + 1;
                    q.add(n);
                }
            }
        }
        return -1;
    }
}