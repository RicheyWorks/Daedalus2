// SPDX-License-Identifier: MIT

package com.daedalus.world.art;

import com.daedalus.engine.MazeGenerator;
import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.AldousBroderGenerator;
import com.daedalus.engine.generators.BinaryTreeGenerator;
import com.daedalus.engine.generators.EllersGenerator;
import com.daedalus.engine.generators.HuntAndKillGenerator;
import com.daedalus.engine.generators.KruskalsGenerator;
import com.daedalus.engine.generators.PrimsGenerator;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.engine.generators.SidewinderGenerator;
import com.daedalus.engine.generators.WilsonsGenerator;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.model.TileType;

import java.util.ArrayDeque;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.SplittableRandom;

/**
 * Art for the galleries (ADR-035), grown from Daedalus' own mazes: a seed picks one of nine generators
 * and a palette, the maze is drawn wall by wall, and its solution runs through it as a rainbow from start
 * to goal. Mazes are what Daedalus began as; every frame in Gallery City shows one. The same seed always
 * gives the same picture, so a frame needs to store nothing but its seed.
 */
public final class MazeArt {

    public static final int SIZE = 256;
    static final int CELLS = 15;

    private static final List<MazeGenerator> GENERATORS = List.of(new RecursiveBacktrackerGenerator(),
            new PrimsGenerator(), new KruskalsGenerator(), new WilsonsGenerator(), new EllersGenerator(),
            new SidewinderGenerator(), new BinaryTreeGenerator(), new HuntAndKillGenerator(),
            new AldousBroderGenerator());

    private final long seed;
    private final String generator;
    private final int[] rgb;
    private final int pathLength;

    private MazeArt(long seed, String generator, int[] rgb, int pathLength) {
        this.seed = seed;
        this.generator = generator;
        this.rgb = rgb;
        this.pathLength = pathLength;
    }

    public long seed() {
        return seed;
    }

    /** The generator's name, e.g. "Wilson's". */
    public String generator() {
        return generator;
    }

    /** Cells on the solution, start and goal included. */
    public int pathLength() {
        return pathLength;
    }

    /** The picture's title: the generator and the seed, like a numbered print. */
    public String title() {
        return generator + " No. " + Long.toUnsignedString(seed);
    }

    public int rgbAt(int x, int y) {
        return rgb[y * SIZE + x];
    }

    public byte[] png() {
        return Png.encode(SIZE, SIZE, rgb);
    }

    public static MazeArt of(long seed) {
        SplittableRandom rng = new SplittableRandom(seed * 0x9E3779B97F4A7C15L + 0x5DEECE66DL);
        MazeGenerator gen = GENERATORS.get(rng.nextInt(GENERATORS.size()));
        MazeGrid maze = gen.generate(CELLS, CELLS, seed, new MazeStats());
        TileType[][] tiles = maze.toTileGrid();
        int n = tiles.length;                          // 2 × CELLS + 1
        double hue = rng.nextDouble();
        int ground = hsv(hue, 0.18, 0.96);
        int wall = hsv((hue + 0.5) % 1.0, 0.55, 0.28);
        int frameLine = hsv(hue, 0.35, 0.82);
        Map<Point, Integer> order = solve(maze);
        int tile = SIZE / n;                           // 8 pixels
        int margin = (SIZE - tile * n) / 2;
        int[] rgb = new int[SIZE * SIZE];
        java.util.Arrays.fill(rgb, frameLine);
        for (int tr = 0; tr < n; tr++) {
            for (int tc = 0; tc < n; tc++) {
                int color = tiles[tr][tc] == TileType.WALL ? wall : ground;
                Integer step = stepOf(order, tr, tc);
                if (step != null) {
                    color = hsv((hue + step / (double) Math.max(1, order.size() * 2)) % 1.0, 0.75, 0.95);
                }
                for (int py = 0; py < tile; py++) {
                    for (int px = 0; px < tile; px++) {
                        rgb[(margin + tr * tile + py) * SIZE + margin + tc * tile + px] = color;
                    }
                }
            }
        }
        return new MazeArt(seed, gen.displayName(), rgb, order.size());
    }

    /** The solution's cells in order from start (0) to goal, by breadth-first search. */
    static Map<Point, Integer> solve(MazeGrid maze) {
        Point start = maze.start() == null ? new Point(0, 0) : maze.start();
        Point goal = maze.goal() == null ? new Point(maze.rows() - 1, maze.cols() - 1) : maze.goal();
        Map<Point, Point> from = new HashMap<>();
        ArrayDeque<Point> queue = new ArrayDeque<>();
        queue.add(start);
        from.put(start, start);
        while (!queue.isEmpty()) {
            Point p = queue.poll();
            if (p.equals(goal)) {
                break;
            }
            for (Point q : maze.openNeighbors(p)) {
                if (!from.containsKey(q)) {
                    from.put(q, p);
                    queue.add(q);
                }
            }
        }
        java.util.LinkedList<Point> path = new java.util.LinkedList<>();
        if (from.containsKey(goal)) {
            for (Point p = goal; !p.equals(start); p = from.get(p)) {
                path.addFirst(p);
            }
            path.addFirst(start);
        }
        Map<Point, Integer> order = new HashMap<>();
        int i = 0;
        for (Point p : path) {
            order.put(p, i++);
        }
        return order;
    }

    /** A tile's place on the path: cell tiles by their cell, the gap between two path cells halfway. */
    private static Integer stepOf(Map<Point, Integer> order, int tr, int tc) {
        if (tr % 2 != 0 && tc % 2 != 0) {
            Integer s = order.get(new Point(tr / 2, tc / 2));
            return s == null ? null : s * 2;
        }
        if (tr % 2 != 0 && tc % 2 == 0 && tc > 0 && tc < CELLS * 2) {
            Integer a = order.get(new Point(tr / 2, tc / 2 - 1));
            Integer b = order.get(new Point(tr / 2, tc / 2));
            return a != null && b != null && Math.abs(a - b) == 1 ? a + b : null;
        }
        if (tr % 2 == 0 && tc % 2 != 0 && tr > 0 && tr < CELLS * 2) {
            Integer a = order.get(new Point(tr / 2 - 1, tc / 2));
            Integer b = order.get(new Point(tr / 2, tc / 2));
            return a != null && b != null && Math.abs(a - b) == 1 ? a + b : null;
        }
        return null;
    }

    static int hsv(double h, double s, double v) {
        int i = (int) Math.floor(h * 6) % 6;
        double f = h * 6 - Math.floor(h * 6);
        double p = v * (1 - s);
        double q = v * (1 - f * s);
        double t = v * (1 - (1 - f) * s);
        double[] c = switch (i) {
            case 0 -> new double[] {v, t, p};
            case 1 -> new double[] {q, v, p};
            case 2 -> new double[] {p, v, t};
            case 3 -> new double[] {p, q, v};
            case 4 -> new double[] {t, p, v};
            default -> new double[] {v, p, q};
        };
        return ((int) Math.round(c[0] * 255) << 16) | ((int) Math.round(c[1] * 255) << 8) | (int) Math.round(c[2] * 255);
    }
}
