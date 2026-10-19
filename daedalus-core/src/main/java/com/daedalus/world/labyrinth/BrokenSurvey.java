// SPDX-License-Identifier: MIT
package com.daedalus.world.labyrinth;

import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.Direction;
import com.daedalus.model.Point;
import com.daedalus.solver.solvers.BfsSolver;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Random;
import java.util.Set;

/** LAB04: compare damaged archive surveys, then verify the route in the real maze. */
public final class BrokenSurvey {
    public static final int VERSION = 1;
    public static final int MAX_SIDE = 64;

    /** One undirected interior edge, always east or south from a to b. */
    public record Passage(Point a, Point b, boolean open) { }

    /** Immutable player-facing survey. Neither survey is an authoritative maze. */
    public record Survey(List<Passage> passages) {
        public Survey {
            passages = List.copyOf(passages);
        }
    }

    public enum Verdict {
        VALID, MISSING_ROUTE, TOO_LONG, OUT_OF_BOUNDS, REPEATED_CELL,
        WRONG_ENDPOINTS, NON_ADJACENT, WALL
    }

    private final long seed;
    private final MazeGrid truth;
    private final List<Point> solution;
    private final Survey first;
    private final Survey second;

    private BrokenSurvey(long seed, MazeGrid truth) {
        this.seed = seed;
        this.truth = truth;
        solution = List.copyOf(new BfsSolver().solve(truth));
        List<Passage> edges = edges(truth);
        // Distinct route edges ensure both surveys are wrong, different, and
        // individually unsolvable in the perfect maze. Noise never carves truth.
        Random noise = new Random(seed ^ 0x42524F4B454EL);
        int one = noise.nextInt(solution.size() - 1);
        int two = (one + 1 + noise.nextInt(solution.size() - 2)) % (solution.size() - 1);
        first = damaged(edges, solution.get(one), solution.get(one + 1));
        second = damaged(edges, solution.get(two), solution.get(two + 1));
    }

    /** Bounded deterministic generation; dimensions are each in [2,64]. */
    public static BrokenSurvey generate(int rows, int cols, long seed) {
        if (rows < 2 || cols < 2 || rows > MAX_SIDE || cols > MAX_SIDE) {
            throw new IllegalArgumentException("survey dimensions must be between 2 and 64");
        }
        return new BrokenSurvey(seed, new RecursiveBacktrackerGenerator().generate(rows, cols, seed));
    }

    public long seed() { return seed; }
    public int rows() { return truth.rows(); }
    public int cols() { return truth.cols(); }
    public Point start() { return truth.start(); }
    public Point goal() { return truth.goal(); }
    public Survey first() { return first; }
    public Survey second() { return second; }

    /** Host-only answer; immutable and independently checkable against truthSnapshot(). */
    public List<Point> solution() { return solution; }

    /** Host-only defensive copy. Never send this answer key as a player survey. */
    public MazeGrid truthSnapshot() { return truth.copy(); }

    /** Pure replay-safe validation; does not award, persist, or trust either survey. */
    public Verdict verify(List<Point> route) {
        if (route == null || route.isEmpty()) {
            return Verdict.MISSING_ROUTE;
        }
        if (route.size() > rows() * cols()) {
            return Verdict.TOO_LONG;
        }
        Set<Point> visited = new HashSet<>();
        for (Point point : route) {
            if (point == null || !truth.inBounds(point)) {
                return Verdict.OUT_OF_BOUNDS;
            }
            if (!visited.add(point)) {
                return Verdict.REPEATED_CELL;
            }
        }
        if (!route.get(0).equals(start()) || !route.get(route.size() - 1).equals(goal())) {
            return Verdict.WRONG_ENDPOINTS;
        }
        for (int i = 1; i < route.size(); i++) {
            Point a = route.get(i - 1);
            Point b = route.get(i);
            if (a.manhattan(b) != 1) {
                return Verdict.NON_ADJACENT;
            }
            Direction direction = direction(a, b);
            if (!truth.cell(a).isOpen(direction) || !truth.cell(b).isOpen(direction.opposite())) {
                return Verdict.WALL;
            }
        }
        return Verdict.VALID;
    }

    private static Direction direction(Point a, Point b) {
        if (b.row() > a.row()) {
            return Direction.SOUTH;
        }
        if (b.row() < a.row()) {
            return Direction.NORTH;
        }
        return b.col() > a.col() ? Direction.EAST : Direction.WEST;
    }

    private static List<Passage> edges(MazeGrid grid) {
        List<Passage> result = new ArrayList<>();
        for (int row = 0; row < grid.rows(); row++) {
            for (int col = 0; col < grid.cols(); col++) {
                Point a = new Point(row, col);
                if (col + 1 < grid.cols()) {
                    result.add(new Passage(a, a.step(Direction.EAST), grid.cell(a).isOpen(Direction.EAST)));
                }
                if (row + 1 < grid.rows()) {
                    result.add(new Passage(a, a.step(Direction.SOUTH), grid.cell(a).isOpen(Direction.SOUTH)));
                }
            }
        }
        return result;
    }

    private static Survey damaged(List<Passage> edges, Point a, Point b) {
        return new Survey(edges.stream().map(edge ->
                (edge.a().equals(a) && edge.b().equals(b)) || (edge.a().equals(b) && edge.b().equals(a))
                        ? new Passage(edge.a(), edge.b(), false) : edge).toList());
    }
}
