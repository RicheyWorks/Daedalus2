// SPDX-License-Identifier: MIT

package com.daedalus.explore;

import com.daedalus.model.TileType;

import java.util.ArrayList;
import java.util.List;

/**
 * Flat Doom-like tints for extruded faces. GLFW only applies these;
 * tests lock the palette so the well stays a maze, not a void.
 */
public final class ExplorePaint {

    public static final float SKY_R = 0.10f;
    public static final float SKY_G = 0.08f;
    public static final float SKY_B = 0.07f;
    public static final int TEX = 64;
    public static final int MAP = 36;
    public static final double TORCH_REACH = 11.0;

    public enum MapKind {
        FLOOR,
        WALL,
        HERE,
        MARK
    }

    public record MapDot(int x, int y, MapKind kind) {
    }

    private ExplorePaint() {
    }

    public static void tint(ExploreMesh.Triangle tri, boolean visible, float[] rgb) {
        tint(tri, visible, rgb, Double.NaN, Double.NaN, 0);
    }

    public static void tint(ExploreMesh.Triangle tri, boolean visible, float[] rgb,
                            double eyeX, double eyeZ, double yaw) {
        if (rgb == null || rgb.length < 3 || tri == null || tri.face() == null) {
            return;
        }
        if (!visible) {
            if (tri.face() == ExploreMesh.Face.WALL) {
                set(rgb, 0.09f, 0.07f, 0.06f);
            } else {
                set(rgb, SKY_R, SKY_G, SKY_B);
            }
            return;
        }
        switch (tri.face()) {
            case FLOOR -> floor(tri, rgb);
            case CEILING -> set(rgb, 0.20f, 0.14f, 0.11f);
            case WALL -> wall(tri, rgb);
            default -> set(rgb, SKY_R, SKY_G, SKY_B);
        }
        if (!Double.isNaN(eyeX)) {
            torch(tri, eyeX, eyeZ, yaw, rgb);
        }
    }

    public static byte[] brickRgba() {
        return raster((x, y) -> {
            boolean mortar = (y % 8 == 0) || (((x + ((y / 8) & 1) * 16) % 16) == 0);
            int n = hash(x, y) & 15;
            if (mortar) {
                return rgbBytes(46, 34, 26);
            }
            return rgbBytes(170 + n, 98 + (n / 2), 54);
        });
    }

    public static byte[] floorRgba() {
        return raster((x, y) -> {
            int cell = ((x / 8) + (y / 8)) & 1;
            int n = hash(x, y) & 11;
            if (cell == 0) {
                return rgbBytes(92 + n, 64 + n / 2, 38);
            }
            return rgbBytes(74 + n, 52 + n / 2, 30);
        });
    }

    public static byte[] ceilingRgba() {
        return raster((x, y) -> {
            int n = hash(x, y) & 19;
            return rgbBytes(58 + n / 2, 42 + n / 3, 34);
        });
    }

    public static void uv(ExploreMesh.Triangle tri, double x, double y, double z, float[] out) {
        if (tri == null || out == null || out.length < 2) {
            return;
        }
        if (tri.face() == ExploreMesh.Face.WALL) {
            double nx = (tri.y2() - tri.y1()) * (tri.z3() - tri.z1())
                    - (tri.z2() - tri.z1()) * (tri.y3() - tri.y1());
            double nz = (tri.x2() - tri.x1()) * (tri.y3() - tri.y1())
                    - (tri.y2() - tri.y1()) * (tri.x3() - tri.x1());
            double along = Math.abs(nx) > Math.abs(nz) ? z : x;
            out[0] = (float) (along / ExploreMesh.TILE);
            out[1] = (float) (y / ExploreMesh.WALL_HEIGHT);
            return;
        }
        out[0] = (float) (x / ExploreMesh.TILE);
        out[1] = (float) (z / ExploreMesh.TILE);
    }

    public static List<MapDot> automap(ExploreFog fog, ExploreMesh mesh, ExploreBody body,
                                      List<ExploreMarker> markers) {
        if (fog == null || mesh == null || mesh.tiles() == null) {
            return List.of();
        }
        TileType[][] tiles = mesh.tiles();
        int minR = Integer.MAX_VALUE;
        int maxR = Integer.MIN_VALUE;
        int minC = Integer.MAX_VALUE;
        int maxC = Integer.MIN_VALUE;
        for (int tr = 0; tr < tiles.length; tr++) {
            for (int tc = 0; tc < tiles[tr].length; tc++) {
                if (!fog.tileVisible(tr, tc)) {
                    continue;
                }
                minR = Math.min(minR, tr);
                maxR = Math.max(maxR, tr);
                minC = Math.min(minC, tc);
                maxC = Math.max(maxC, tc);
            }
        }
        if (minR == Integer.MAX_VALUE) {
            return List.of();
        }
        List<MapDot> out = new ArrayList<>();
        for (int tr = minR; tr <= maxR; tr++) {
            for (int tc = minC; tc <= maxC; tc++) {
                if (!fog.tileVisible(tr, tc)) {
                    continue;
                }
                int x = project(tc, minC, maxC);
                int y = MAP - 1 - project(tr, minR, maxR);
                out.add(new MapDot(x, y, mesh.solidTile(tr, tc) ? MapKind.WALL : MapKind.FLOOR));
            }
        }
        if (markers != null) {
            for (ExploreMarker mark : markers) {
                if (mark == null || mark.cell() == null) {
                    continue;
                }
                int tr = 2 * mark.cell().row() + 1;
                int tc = 2 * mark.cell().col() + 1;
                if (!fog.tileVisible(tr, tc)) {
                    continue;
                }
                out.add(new MapDot(project(tc, minC, maxC),
                        MAP - 1 - project(tr, minR, maxR), MapKind.MARK));
            }
        }
        if (body != null) {
            int tc = (int) Math.round(body.x() / ExploreMesh.TILE + 1);
            int tr = (int) Math.round(body.z() / ExploreMesh.TILE + 1);
            out.add(new MapDot(project(tc, minC, maxC),
                    MAP - 1 - project(tr, minR, maxR), MapKind.HERE));
        }
        return List.copyOf(out);
    }

    public static void marker(String kind, float[] rgb) {
        if (rgb == null || rgb.length < 3) {
            return;
        }
        if ("BOSS".equals(kind)) {
            set(rgb, 0.72f, 0.18f, 0.12f);
        } else if ("ENTRANCE".equals(kind)) {
            set(rgb, 0.82f, 0.62f, 0.18f);
        } else {
            set(rgb, 0.28f, 0.52f, 0.58f);
        }
    }

    private static void floor(ExploreMesh.Triangle tri, float[] rgb) {
        float check = ((tri.tr() + tri.tc()) & 1) == 0 ? 1f : 0.82f;
        set(rgb, 0.34f * check, 0.24f * check, 0.14f * check);
    }

    private static void wall(ExploreMesh.Triangle tri, float[] rgb) {
        double nx = (tri.y2() - tri.y1()) * (tri.z3() - tri.z1())
                - (tri.z2() - tri.z1()) * (tri.y3() - tri.y1());
        double nz = (tri.x2() - tri.x1()) * (tri.y3() - tri.y1())
                - (tri.y2() - tri.y1()) * (tri.x3() - tri.x1());
        boolean eastWest = Math.abs(nx) > Math.abs(nz);
        double midY = (tri.y1() + tri.y2() + tri.y3()) / 3.0;
        float boot = midY < ExploreMesh.WALL_HEIGHT * 0.38 ? 0.70f : 1f;
        float stripe = stripe(tri, eastWest);
        float shade = boot * stripe;
        if (eastWest) {
            set(rgb, 0.48f * shade, 0.28f * shade, 0.16f * shade);
        } else {
            set(rgb, 0.64f * shade, 0.40f * shade, 0.22f * shade);
        }
    }

    private static float stripe(ExploreMesh.Triangle tri, boolean eastWest) {
        double u = eastWest
                ? (tri.z1() + tri.z2() + tri.z3()) / 3.0
                : (tri.x1() + tri.x2() + tri.x3()) / 3.0;
        int band = (int) Math.floor(u / ExploreMesh.TILE);
        return (band & 1) == 0 ? 1f : 0.84f;
    }

    private static void torch(ExploreMesh.Triangle tri, double eyeX, double eyeZ,
                             double yaw, float[] rgb) {
        double cx = (tri.x1() + tri.x2() + tri.x3()) / 3.0;
        double cz = (tri.z1() + tri.z2() + tri.z3()) / 3.0;
        double dx = cx - eyeX;
        double dz = cz - eyeZ;
        double dist = Math.hypot(dx, dz);
        double facing = 1;
        if (dist > 1e-6) {
            facing = (dx * Math.sin(yaw) + dz * (-Math.cos(yaw))) / dist;
        }
        float lamp = (float) (0.40 + 0.60 * Math.max(0, facing)
                * Math.max(0, 1.0 - dist / TORCH_REACH));
        rgb[0] = Math.min(1f, rgb[0] * lamp);
        rgb[1] = Math.min(1f, rgb[1] * lamp);
        rgb[2] = Math.min(1f, rgb[2] * lamp);
    }

    private static int project(int value, int min, int max) {
        int span = Math.max(1, max - min);
        return (int) Math.round((value - min) * (MAP - 1) / (double) span);
    }

    private static void set(float[] rgb, float r, float g, float b) {
        rgb[0] = r;
        rgb[1] = g;
        rgb[2] = b;
    }

    @FunctionalInterface
    private interface Texel {
        int[] at(int x, int y);
    }

    private static byte[] raster(Texel texel) {
        byte[] out = new byte[TEX * TEX * 4];
        for (int y = 0; y < TEX; y++) {
            for (int x = 0; x < TEX; x++) {
                int[] rgb = texel.at(x, y);
                int i = (y * TEX + x) * 4;
                out[i] = (byte) rgb[0];
                out[i + 1] = (byte) rgb[1];
                out[i + 2] = (byte) rgb[2];
                out[i + 3] = (byte) 255;
            }
        }
        return out;
    }

    private static int[] rgbBytes(int r, int g, int b) {
        return new int[] {clampByte(r), clampByte(g), clampByte(b)};
    }

    private static int clampByte(int v) {
        return Math.max(0, Math.min(255, v));
    }

    private static int hash(int x, int y) {
        return (x * 374761393 + y * 668265263) >>> 8;
    }
}
