// SPDX-License-Identifier: MIT

package com.daedalus.world.island;

import java.util.List;

/**
 * The voxel isle's shape (ADR-058), ported line for line from the Unreal plugin's
 * {@code DaedalusVoxelIsleCore.h}, so the web realm and Unreal raise the same isle from the same numbers.
 *
 * <p>A seed grows a floating isle:
 * <ul>
 *   <li>terraced hills rise to a summit, inside a noisy rim;</li>
 *   <li>underneath, a hanging rock tapers to a glowing heartstone tip;</li>
 *   <li>grass is on top, sand on a narrow beach and round the pond, dirt below, then stone;</li>
 *   <li>an optional pond is sunk into the top.</li>
 * </ul>
 * Coordinates are cubes: X and Y across, Z up, with (0, 0) the centre column. Only cubes with an open face are
 * emitted.
 *
 * <p>Parity: {@code engines/unreal/core-test/voxel_isle_core_test.cpp --write voxel_isle_parity.txt} writes counts,
 * an FNV hash of every cube and sample columns for seven isles; {@code VoxelIsleTest} recomputes them here. Unsigned
 * 32-bit hashing is done in {@code int} with {@code >>>}; everything else is double, as in C++.
 */
public final class VoxelIsle {

    /** "No column here". */
    public static final int OFF = Integer.MIN_VALUE;

    /** What a cube is made of; the ordinals match the C++ {@code Layer} enum. */
    public enum Layer { GRASS, SAND, DIRT, STONE, HEART, MEADOW }

    /** An isle's settings, as on the Unreal actor. Pond radius 0 = no pond. */
    public record Params(int seed, int radius, int summitHeight, int depth, int pondX, int pondY, int pondRadius) {
        public Params {
            if (radius < 4 || radius > 400) {
                throw new IllegalArgumentException("isle radius must be 4..400, was " + radius);
            }
            if (summitHeight < 0 || summitHeight > 200 || depth < 0 || depth > 400 || pondRadius < 0) {
                throw new IllegalArgumentException("summit 0..200, depth 0..400 and pond radius >= 0");
            }
        }
    }

    /** Receives each visible cube. */
    @FunctionalInterface
    public interface Emitter {
        void cube(int x, int y, int z, Layer layer);
    }

    /** One isle of a named group, offset from the group's centre in centimetres (Unreal units). */
    public record Placed(String name, Params params, double dx, double dy, double dz) {
    }

    /**
     * The Orrery Reach: Claude Island and its four neighbours, exactly as {@code tools/claude_island} places them in
     * Unreal (orr_place.py and orr_reach.py).
     */
    public static List<Placed> orreryReach() {
        return List.of(
                new Placed("Claude Island", new Params(7, 140, 16, 70, -70, 45, 14), 0, 0, 0),
                new Placed("Bloomfields", new Params(31, 70, 6, 40, 20, -15, 10), -3200, -24000, -1800),
                new Placed("Tidewells", new Params(47, 60, 8, 50, 0, 0, 22), 22000, 16000, 1200),
                new Placed("Lens Forge", new Params(53, 38, 14, 45, 0, 0, 0), -22000, 14000, 4200),
                new Placed("Vault", new Params(61, 46, 20, 60, 0, 0, 0), 6000, -52000, 2600));
    }

    private VoxelIsle() {
    }

    private static double hash(Params p, int ix, int iy, int salt) {
        int h = ix * 374761393 + iy * 668265263 + p.seed() * (int) 2246822519L + salt * (int) 3266489917L;
        h = (h ^ (h >>> 13)) * 1274126177;
        return ((h ^ (h >>> 16)) & 0xFFFF) / 65535.0;
    }

    /** Value noise on an integer lattice, smoothly interpolated; 0..1. */
    public static double noise(Params p, double x, double y, int salt) {
        double fx0 = Math.floor(x);
        double fy0 = Math.floor(y);
        int x0 = (int) fx0;
        int y0 = (int) fy0;
        double fx = x - fx0;
        double fy = y - fy0;
        double sx = fx * fx * (3.0 - 2.0 * fx);
        double sy = fy * fy * (3.0 - 2.0 * fy);
        double a = hash(p, x0, y0, salt) + (hash(p, x0 + 1, y0, salt) - hash(p, x0, y0, salt)) * sx;
        double b = hash(p, x0, y0 + 1, salt) + (hash(p, x0 + 1, y0 + 1, salt) - hash(p, x0, y0 + 1, salt)) * sx;
        return a + (b - a) * sy;
    }

    private static double dist(double x, double y) {
        return Math.sqrt(x * x + y * y);
    }

    public static boolean inPond(Params p, int x, int y) {
        if (p.pondRadius() <= 0) {
            return false;
        }
        double r = p.pondRadius() * (0.85 + 0.3 * noise(p, x * 0.15, y * 0.15, 9));
        return dist(x - p.pondX(), y - p.pondY()) < r;
    }

    /** The column's top in cubes above the rim level, -2 in the pond, or {@link #OFF} past the rim. */
    public static int columnTop(Params p, int x, int y) {
        double r = dist(x, y);
        double cx = r > 0 ? x / r : 1.0;
        double cy = r > 0 ? y / r : 0.0;
        double edge = p.radius() * (0.84 + 0.16 * noise(p, cx * 3.0 + 10.0, cy * 3.0 + 10.0, 1));
        if (r >= edge) {
            return OFF;
        }
        double t = 1.0 - r / edge;
        double h = p.summitHeight() * StrictMath.pow(t, 1.6) + 2.5 * noise(p, x * 0.07, y * 0.07, 2)
                + 1.2 * noise(p, x * 0.2, y * 0.2, 3);
        h = Math.floor(h / 2.0) * 2.0;
        if (inPond(p, x, y)) {
            return -2;
        }
        return h > 0 ? (int) h : 0;
    }

    /** The lowest cube of the hanging rock under the column. */
    public static int columnBottom(Params p, int x, int y) {
        double t = 1.0 - dist(x, y) / p.radius();
        t = t < 0 ? 0 : (t > 1 ? 1 : t);
        return -3 - (int) (p.depth() * StrictMath.pow(t, 1.1) * (0.8 + 0.4 * noise(p, x * 0.1, y * 0.1, 4)));
    }

    static boolean shore(Params p, int x, int y) {
        if (inPond(p, x, y)) {
            return true;
        }
        if (p.pondRadius() > 0 && dist(x - p.pondX(), y - p.pondY()) < p.pondRadius() + 2.5) {
            return true;
        }
        return columnTop(p, x + 2, y) == OFF || columnTop(p, x - 2, y) == OFF
                || columnTop(p, x, y + 2) == OFF || columnTop(p, x, y - 2) == OFF;
    }

    static Layer layerOf(Params p, int x, int y, int z, int top, int bottom, boolean isShore) {
        Layer l = Layer.STONE;
        if (z == top) {
            l = isShore ? Layer.SAND : (noise(p, x * 0.09, y * 0.09, 7) > 0.55 ? Layer.MEADOW : Layer.GRASS);
        } else if (z >= top - 2) {
            l = Layer.DIRT;
        }
        if (z <= bottom + 1 && dist(x, y) < 4.0) {
            l = Layer.HEART;
        }
        return l;
    }

    /** Every visible cube, in Y-major, X, then Z order (the C++ order). Returns the column count. */
    public static int build(Params p, Emitter out) {
        int n = p.radius() + 2;
        int w = 2 * n + 1;
        int[] tops = new int[w * w];
        int[] bots = new int[w * w];
        for (int y = -n; y <= n; ++y) {
            for (int x = -n; x <= n; ++x) {
                int i = (y + n) * w + (x + n);
                tops[i] = columnTop(p, x, y);
                bots[i] = tops[i] == OFF ? 0 : columnBottom(p, x, y);
            }
        }
        int[] nx = {1, -1, 0, 0};
        int[] ny = {0, 0, 1, -1};
        int columns = 0;
        for (int y = -n; y <= n; ++y) {
            for (int x = -n; x <= n; ++x) {
                int top = tops[(y + n) * w + (x + n)];
                if (top == OFF) {
                    continue;
                }
                ++columns;
                int bottom = bots[(y + n) * w + (x + n)];
                boolean isShore = shore(p, x, y);
                for (int z = bottom; z <= top; ++z) {
                    boolean open = z == top || z == bottom;
                    for (int k = 0; k < 4 && !open; ++k) {
                        int ax = x + nx[k];
                        int ay = y + ny[k];
                        boolean inside = ax >= -n && ax <= n && ay >= -n && ay <= n;
                        int nt = inside ? tops[(ay + n) * w + (ax + n)] : OFF;
                        int nb = inside ? bots[(ay + n) * w + (ax + n)] : 0;
                        open = nt == OFF || nt < z || nb > z;
                    }
                    if (open) {
                        out.cube(x, y, z, layerOf(p, x, y, z, top, bottom, isShore));
                    }
                }
            }
        }
        return columns;
    }

    /** Column tops and bottoms on the (2r+5)^2 grid, row-major from (-r-2, -r-2): what a renderer needs. */
    public static int[][] columns(Params p) {
        int n = p.radius() + 2;
        int w = 2 * n + 1;
        int[] tops = new int[w * w];
        int[] bots = new int[w * w];
        for (int y = -n; y <= n; ++y) {
            for (int x = -n; x <= n; ++x) {
                int i = (y + n) * w + (x + n);
                tops[i] = columnTop(p, x, y);
                bots[i] = tops[i] == OFF ? 0 : columnBottom(p, x, y);
            }
        }
        return new int[][] {tops, bots};
    }
}
