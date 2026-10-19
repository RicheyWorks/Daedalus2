// SPDX-License-Identifier: MIT
package com.daedalus.world.labyrinth;

import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.Direction;
import com.daedalus.model.Point;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * LAB03b Echo Sonar: the second chapter of "listen to the maze before trusting a map".
 *
 * <p>The player carries a hand bell. Ringing it at a cell sends sound down every open corridor. A corridor that
 * only leads to dead ends echoes back after {@link EchoBellGate#echoDelayMs(int)} for its deepest reach (200 ms +
 * 70 ms per cell, capped at 40 cells), so a long branch answers late and a short one answers at once. The one
 * corridor that leads toward the exit returns no echo, because the sound escapes. Following the silence is always
 * the shortest way out; the tests prove that against a BFS for many seeds. Pings are limited, so the player has
 * to choose junctions to listen at.
 *
 * <p>Ear rules: each direction's echo uses one of the Echo Bell gate's low D pentatonic bells (N D3, E F3, S G3,
 * W A3; 146.832-219.999 Hz) at gain 0.3. Pure data on top of the maze engine.
 */
public final class EchoSonar {
    /** Echo gain for every direction (passing-note level, ear rule). */
    public static final double GAIN = 0.3;
    /** Deepest reach that still shapes the echo delay (same cap as the Echo Bell gate). */
    public static final int MAX_DEPTH = 40;

    /** One corridor's answer: silent = this way leads out; else echoMs after the ring. */
    public record Echo(Direction dir, boolean silent, int depthCells, int echoMs, double hz, double gain) { }

    private final MazeGrid maze;
    private final Point exit;

    private EchoSonar(MazeGrid maze) {
        this.maze = maze;
        this.exit = maze.goal();
    }

    /** A seeded perfect maze from the maze engine (recursive backtracker), entrance top-left, exit bottom-right. */
    public static EchoSonar seeded(int rows, int cols, long seed) {
        if (rows < 2 || cols < 2 || rows > 64 || cols > 64) {
            throw new IllegalArgumentException("maze 2-64 cells a side");
        }
        return new EchoSonar(new RecursiveBacktrackerGenerator().generate(rows, cols, seed));
    }

    /** Entrance cell (top-left). */
    public Point start() {
        return maze.start();
    }

    /** Exit cell (bottom-right). */
    public Point exit() {
        return exit;
    }

    /** True if a corridor leads from {@code p} in direction {@code d} (hosts build walls from this). */
    public boolean isOpen(Point p, Direction d) {
        return maze.inBounds(p) && maze.isOpen(p.row(), p.col(), d) && maze.inBounds(p.step(d));
    }

    /** Pitch for an echo from this direction, from the Echo Bell gate's bells. */
    public static double hzOf(Direction d) {
        return switch (d) {
            case NORTH -> 146.832;
            case EAST -> 174.614;
            case SOUTH -> 195.997;
            case WEST -> 219.999;
        };
    }

    /** Ring the bell at {@code at}: one answer per open corridor, in Direction order. */
    public List<Echo> ping(Point at) {
        if (!maze.inBounds(at)) {
            throw new IllegalArgumentException("outside the maze: " + at);
        }
        List<Echo> out = new ArrayList<>();
        for (Direction d : Direction.values()) {
            if (!maze.isOpen(at.row(), at.col(), d) || !maze.inBounds(at.step(d))) {
                continue;
            }
            int[] reach = branch(at, at.step(d));
            boolean silent = reach[1] == 1;
            int depth = Math.min(MAX_DEPTH, reach[0]);
            out.add(new Echo(d, silent, depth, silent ? -1 : EchoBellGate.echoDelayMs(depth), hzOf(d), silent ? 0.0 : GAIN));
        }
        return out;
    }

    /** {deepest cells reached, 1 if the exit lies down this corridor}, never walking back through {@code from}. */
    private int[] branch(Point from, Point first) {
        Map<Point, Integer> dist = new HashMap<>();
        Deque<Point> q = new ArrayDeque<>();
        dist.put(from, 0);
        dist.put(first, 1);
        q.add(first);
        int deepest = 1;
        int escapes = 0;
        while (!q.isEmpty()) {
            Point p = q.poll();
            int dp = dist.get(p);
            deepest = Math.max(deepest, dp);
            if (p.equals(exit)) {
                escapes = 1;
            }
            for (Point n : maze.openNeighbors(p)) {
                if (!dist.containsKey(n)) {
                    dist.put(n, dp + 1);
                    q.add(n);
                }
            }
        }
        return new int[] {deepest, escapes};
    }

    /** Fewest steps from {@code a} to the exit (BFS over open corridors). */
    public int stepsToExit(Point a) {
        Map<Point, Integer> dist = new HashMap<>();
        Deque<Point> q = new ArrayDeque<>();
        dist.put(a, 0);
        q.add(a);
        while (!q.isEmpty()) {
            Point p = q.poll();
            if (p.equals(exit)) {
                return dist.get(p);
            }
            for (Point n : maze.openNeighbors(p)) {
                if (dist.putIfAbsent(n, dist.get(p) + 1) == null) {
                    q.add(n);
                }
            }
        }
        return -1;
    }

    /** One walk from the entrance with a ping budget. */
    public final class Walk {
        private Point at = maze.start();
        private int pingsLeft;
        private int steps;

        /** Starts at the entrance with {@code pings} rings of the bell. */
        public Walk(int pings) {
            if (pings < 0) {
                throw new IllegalArgumentException("pings >= 0");
            }
            this.pingsLeft = pings;
        }

        /** Rings the bell here; throws once the budget is spent. */
        public List<Echo> ping() {
            if (pingsLeft == 0) {
                throw new IllegalStateException("the bell is out of rings");
            }
            pingsLeft--;
            return EchoSonar.this.ping(at);
        }

        /** Steps one cell; false (and no move) if a wall is in the way. */
        public boolean move(Direction d) {
            if (!maze.isOpen(at.row(), at.col(), d) || !maze.inBounds(at.step(d))) {
                return false;
            }
            at = at.step(d);
            steps++;
            return true;
        }

        /** Current cell. */
        public Point at() {
            return at;
        }

        /** True once the exit is reached. */
        public boolean out() {
            return at.equals(exit);
        }

        /** Steps taken. */
        public int steps() {
            return steps;
        }

        /** Rings left. */
        public int pingsLeft() {
            return pingsLeft;
        }

        /** Stars for the run: 3 = shortest route, 2 = within half again, 1 = out at all, 0 = not out. */
        public int stars() {
            if (!out()) {
                return 0;
            }
            int best = stepsToExit(maze.start());
            return steps == best ? 3 : steps * 2 <= best * 3 ? 2 : 1;
        }
    }
}
