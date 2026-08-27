// SPDX-License-Identifier: MIT

package com.daedalus.explore;

import com.daedalus.model.Point;
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
    public static final int GLYPH_W = 5;
    public static final int GLYPH_H = 7;
    /** Ortho strip under the crosshair — Doom status height in NDC. */
    public static final float STATUS_H = 0.28f;
    public static final double TORCH_REACH = 11.0;

    public enum MapKind {
        FLOOR,
        WALL,
        HERE,
        MARK
    }

    public record MapDot(int x, int y, MapKind kind) {
    }

    /**
     * Bottom strip: named place, compass, how much stone is earned.
     * GLFW only paints this; tests lock the words so the bar cannot lie.
     */
    public record Status(String place, String facing, int stood, int marks, int mood) {
    }

    public enum HandPart {
        GRIP,
        SHAFT,
        FLAME
    }

    /** Ortho triangles for the torch hand — GLFW fills these; tests lock the silhouette. */
    public record HandTri(float x1, float y1, float x2, float y2, float x3, float y3, HandPart part) {
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

    public static byte[] skyRgba() {
        return raster((x, y) -> {
            int n = hash(x, y) & 31;
            boolean star = y < 20 && (hash(x, y) & 63) == 0;
            if (star) {
                return rgbBytes(220, 196, 140);
            }
            if (y < 18) {
                return rgbBytes(78 + n / 3, 30 + n / 6, 24);
            }
            if (y < 36) {
                return rgbBytes(148 + n / 2, 56 + n / 4, 30);
            }
            if (y < 46) {
                return rgbBytes(196 + n / 3, 88 + n / 5, 34);
            }
            boolean hill = y > 50 && ((hash(x / 6, 3) & 15) > (64 - y));
            if (hill) {
                return rgbBytes(30 + n / 4, 16, 14);
            }
            return rgbBytes(52 + n / 3, 24, 20);
        });
    }

    public static byte[] faceRgba(int mood) {
        int grim = Math.max(0, Math.min(2, mood));
        return raster((x, y) -> {
            int px = x / 8;
            int py = y / 8;
            if (px <= 0 || px >= 7 || py <= 0 || py >= 7) {
                return rgbBytes(34, 22, 16);
            }
            if (py == 1) {
                return rgbBytes(62, 36, 22);
            }
            if (py == 3 && (px == 2 || px == 5)) {
                return rgbBytes(18, 12, 10);
            }
            if (py == 5) {
                return mouth(grim, px);
            }
            return rgbBytes(186, 128, 78);
        });
    }

    public static void skyUv(double yaw, double pitch, float sx, float sy, float[] out) {
        if (out == null || out.length < 2) {
            return;
        }
        out[0] = sx + (float) (yaw / (Math.PI * 2.0));
        out[1] = sy - (float) (pitch * 0.35);
    }

    public static Status status(ExploreFog fog, ExploreBody body, List<ExploreMarker> markers) {
        String facing = facing(body == null ? 0 : body.yaw());
        int stood = fog == null ? 0 : fog.memorySize();
        ExploreMarker near = nearestVisible(fog, body, markers);
        int marks = countVisible(fog, markers);
        if (near == null) {
            return new Status("HALL", facing, stood, marks, 0);
        }
        return new Status(placeName(near.kind()), facing, stood, marks, mood(near.kind()));
    }

    public static String caption(Status status) {
        if (status == null) {
            return "HALL";
        }
        return status.place() + "  " + status.facing() + "  " + status.stood();
    }

    /**
     * Crosshair Y in ortho NDC. Status eats the bottom strip, so aim sits in
     * the center of what is left — not the window midpoint.
     */
    public static float aimY() {
        return STATUS_H * 0.5f;
    }

    public static void keyTint(int slot, int marks, int mood, float[] rgb) {
        if (rgb == null || rgb.length < 3) {
            return;
        }
        boolean last = marks > 0 && slot == marks - 1;
        if (last && mood >= 2) {
            set(rgb, 0.78f, 0.22f, 0.16f);
        } else if (last && mood == 1) {
            set(rgb, 0.28f, 0.52f, 0.58f);
        } else {
            set(rgb, 0.82f, 0.62f, 0.18f);
        }
    }

    /** Idle bob so the torch is not a pasted sticker. */
    public static float handBob(double seconds) {
        return (float) (Math.sin(seconds * 5.2) * 0.018);
    }

    /**
     * Lower-right torch above the status strip. Same band as Doom's weapon —
     * presence, not combat.
     */
    public static List<HandTri> handMesh(double aspect, float bob) {
        float ox = (float) (Math.max(0.55, aspect) * 0.48);
        float oy = -1f + STATUS_H + 0.06f + bob;
        List<HandTri> out = new ArrayList<>();
        // Fist / grip
        tri(out, ox - 0.02f, oy, ox + 0.12f, oy - 0.02f, ox + 0.10f, oy + 0.10f, HandPart.GRIP);
        tri(out, ox - 0.02f, oy, ox + 0.10f, oy + 0.10f, ox - 0.04f, oy + 0.08f, HandPart.GRIP);
        // Shaft
        tri(out, ox + 0.04f, oy + 0.08f, ox + 0.09f, oy + 0.08f, ox + 0.07f, oy + 0.28f, HandPart.SHAFT);
        tri(out, ox + 0.04f, oy + 0.08f, ox + 0.07f, oy + 0.28f, ox + 0.03f, oy + 0.26f, HandPart.SHAFT);
        // Flame
        tri(out, ox + 0.02f, oy + 0.26f, ox + 0.12f, oy + 0.26f, ox + 0.07f, oy + 0.42f, HandPart.FLAME);
        tri(out, ox + 0.04f, oy + 0.26f, ox + 0.10f, oy + 0.26f, ox + 0.07f, oy + 0.36f, HandPart.FLAME);
        return List.copyOf(out);
    }

    public static void handTint(HandPart part, int mood, float[] rgb) {
        if (rgb == null || rgb.length < 3 || part == null) {
            return;
        }
        int grim = Math.max(0, Math.min(2, mood));
        switch (part) {
            case GRIP -> set(rgb, 0.72f, 0.48f, 0.30f);
            case SHAFT -> set(rgb, 0.28f, 0.18f, 0.12f);
            case FLAME -> {
                if (grim >= 2) {
                    set(rgb, 0.95f, 0.28f, 0.12f);
                } else if (grim == 1) {
                    set(rgb, 0.95f, 0.62f, 0.22f);
                } else {
                    set(rgb, 0.98f, 0.78f, 0.28f);
                }
            }
            default -> set(rgb, 0.5f, 0.5f, 0.5f);
        }
    }

    public static boolean glyphDot(char raw, int x, int y) {
        if (x < 0 || x >= GLYPH_W || y < 0 || y >= GLYPH_H) {
            return false;
        }
        long bits = glyphBits(Character.toUpperCase(raw));
        return ((bits >>> (y * GLYPH_W + x)) & 1L) == 1L;
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

    static String facing(double yaw) {
        double a = yaw;
        while (a <= -Math.PI) {
            a += Math.PI * 2.0;
        }
        while (a > Math.PI) {
            a -= Math.PI * 2.0;
        }
        if (a > Math.PI * 0.75 || a <= -Math.PI * 0.75) {
            return "S";
        }
        if (a > Math.PI * 0.25) {
            return "E";
        }
        if (a < -Math.PI * 0.25) {
            return "W";
        }
        return "N";
    }

    private static ExploreMarker nearestVisible(ExploreFog fog, ExploreBody body,
                                               List<ExploreMarker> markers) {
        if (fog == null || markers == null) {
            return null;
        }
        Point here = body == null ? new Point(0, 0) : body.cell();
        ExploreMarker best = null;
        double bestDist = Double.POSITIVE_INFINITY;
        for (ExploreMarker mark : markers) {
            if (mark == null || mark.cell() == null) {
                continue;
            }
            int tr = 2 * mark.cell().row() + 1;
            int tc = 2 * mark.cell().col() + 1;
            if (!fog.tileVisible(tr, tc)) {
                continue;
            }
            double dist = Math.hypot(mark.cell().row() - here.row(),
                    mark.cell().col() - here.col());
            if (dist < bestDist) {
                bestDist = dist;
                best = mark;
            }
        }
        return best;
    }

    private static int countVisible(ExploreFog fog, List<ExploreMarker> markers) {
        if (fog == null || markers == null) {
            return 0;
        }
        int n = 0;
        for (ExploreMarker mark : markers) {
            if (mark == null || mark.cell() == null) {
                continue;
            }
            if (fog.tileVisible(2 * mark.cell().row() + 1, 2 * mark.cell().col() + 1)) {
                n++;
            }
        }
        return n;
    }

    private static String placeName(String kind) {
        if ("BOSS".equals(kind)) {
            return "BOSS";
        }
        if ("ENTRANCE".equals(kind)) {
            return "ENTRANCE";
        }
        if ("TREASURE".equals(kind) || "VAULT".equals(kind)) {
            return "VAULT";
        }
        return "HALL";
    }

    private static int mood(String kind) {
        if ("BOSS".equals(kind)) {
            return 2;
        }
        if ("TREASURE".equals(kind) || "VAULT".equals(kind)) {
            return 1;
        }
        return 0;
    }

    private static int[] mouth(int grim, int px) {
        if (grim == 1 && px >= 2 && px <= 5) {
            return rgbBytes(92, 36, 28);
        }
        if (grim == 2 && px >= 3 && px <= 4) {
            return rgbBytes(48, 22, 18);
        }
        if (grim == 0 && (px == 3 || px == 4)) {
            return rgbBytes(92, 48, 36);
        }
        return rgbBytes(186, 128, 78);
    }

    private static long glyphBits(char c) {
        // Exactly 35 cells (5×7), row-major. long — int only holds 32 bits.
        return switch (c) {
            case '0' -> bits(".###.#...##...##...##...##...#.###.");
            case '1' -> bits("..#....##....#....#....#....#.#####");
            case '2' -> bits(".###.#...#....#..##..#...#....#####");
            case '3' -> bits(".###.#...#....#.###.....##...#.###.");
            case '4' -> bits("#...##...#.#...######....#....#...#");
            case '5' -> bits("######....#.....####....##...#.###.");
            case '6' -> bits(".###.#....#....####.#...##...#.###.");
            case '7' -> bits("#####....#...#...#...#....#....#...");
            case '8' -> bits(".###.#...##...#.###.#...##...#.###.");
            case '9' -> bits(".###.#...##...#.####.....#....#.###");
            case 'A' -> bits(".###.#...##...#######...##...##...#");
            case 'B' -> bits("####.#...##...#####.#...##...#####.");
            case 'C' -> bits(".###.#...##....#....#....#...#.###.");
            case 'E' -> bits("######....#....####.#....#....#####");
            case 'H' -> bits("#...##...##...#######...##...##...#");
            case 'L' -> bits("#....#....#....#....#....#....#####");
            case 'N' -> bits("#...###..##.#.##.#.##..###...##...#");
            case 'O' -> bits(".###.#...##...##...##...##...#.###.");
            case 'R' -> bits("####.#...##...#####.#.#.##..##...#.");
            case 'S' -> bits(".####.#....#....###.....#....#####.");
            case 'T' -> bits("#####..#....#....#....#....#....#..");
            case 'U' -> bits("#...##...##...##...##...##...#.###.");
            case 'V' -> bits("#...##...##...##...##...#.#.#...#..");
            case 'W' -> bits("#...##...##...##.#.##.#.##.#.#.#.#.");
            case '-' -> bits("....................#####..........");
            default -> 0L;
        };
    }

    private static long bits(String pattern) {
        if (pattern == null || pattern.length() != GLYPH_W * GLYPH_H) {
            return 0L;
        }
        long out = 0L;
        for (int i = 0; i < pattern.length(); i++) {
            char ch = pattern.charAt(i);
            if (ch == '#' || ch == '1') {
                out |= 1L << i;
            }
        }
        return out;
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

    private static void tri(List<HandTri> out, float x1, float y1, float x2, float y2,
                            float x3, float y3, HandPart part) {
        out.add(new HandTri(x1, y1, x2, y2, x3, y3, part));
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
