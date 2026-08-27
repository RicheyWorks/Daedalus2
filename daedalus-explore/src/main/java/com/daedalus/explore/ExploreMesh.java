// SPDX-License-Identifier: MIT

package com.daedalus.explore;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.TileType;

import java.util.ArrayList;
import java.util.List;

/**
 * Extruded dungeon from {@link MazeGrid#toTileGrid()} — ADR-017.
 *
 * <p>Cell {@code (r,c)} sits at {@code (c · CELL, r · CELL)}. North is −Z.
 * A WALL tile is a collision hull; room posts the projection already opened
 * stay floor.
 */
public final class ExploreMesh {

    public static final double CELL = 2.0;
    public static final double TILE = CELL / 2.0;
    public static final double WALL_HEIGHT = 2.8;
    public static final double PLAYER_RADIUS = 0.28;

    public enum Face {
        FLOOR,
        CEILING,
        WALL
    }

    public record Hull(double minX, double maxX, double minZ, double maxZ) {
        public boolean hits(double x, double z, double radius) {
            double nx = clamp(x, minX, maxX);
            double nz = clamp(z, minZ, maxZ);
            double dx = x - nx;
            double dz = z - nz;
            return dx * dx + dz * dz < radius * radius;
        }
    }

    public record Triangle(double x1, double y1, double z1,
                           double x2, double y2, double z2,
                           double x3, double y3, double z3,
                           Face face, int tr, int tc) {
        public boolean wall() {
            return face == Face.WALL;
        }
    }

    private final MazeGrid grid;
    private final TileType[][] tiles;
    private final List<Hull> hulls;
    private final List<Triangle> triangles;

    private ExploreMesh(MazeGrid grid, TileType[][] tiles, List<Hull> hulls,
                        List<Triangle> triangles) {
        this.grid = grid;
        this.tiles = tiles;
        this.hulls = hulls;
        this.triangles = triangles;
    }

    public static ExploreMesh of(MazeGrid grid) {
        if (grid == null) {
            throw new NullPointerException("grid");
        }
        TileType[][] tiles = grid.toTileGrid();
        List<Hull> hulls = new ArrayList<>();
        List<Triangle> triangles = new ArrayList<>();
        for (int tr = 0; tr < tiles.length; tr++) {
            for (int tc = 0; tc < tiles[tr].length; tc++) {
                double cx = tileCenterX(tc);
                double cz = tileCenterZ(tr);
                double h = TILE / 2.0;
                if (tiles[tr][tc] == TileType.WALL) {
                    hulls.add(new Hull(cx - h, cx + h, cz - h, cz + h));
                    addBox(triangles, cx, cz, h, tr, tc);
                } else {
                    addFloor(triangles, cx, cz, h, tr, tc);
                }
            }
        }
        return new ExploreMesh(grid, tiles, List.copyOf(hulls), List.copyOf(triangles));
    }

    public MazeGrid grid() {
        return grid;
    }

    public TileType[][] tiles() {
        return tiles;
    }

    public List<Hull> hulls() {
        return hulls;
    }

    public List<Triangle> triangles() {
        return triangles;
    }

    public boolean solidTile(int tr, int tc) {
        if (tr < 0 || tc < 0 || tr >= tiles.length || tc >= tiles[tr].length) {
            return true;
        }
        return tiles[tr][tc] == TileType.WALL;
    }

    public boolean blocked(double x, double z, double radius) {
        for (Hull hull : hulls) {
            if (hull.hits(x, z, radius)) {
                return true;
            }
        }
        return false;
    }

    public static double worldX(int col) {
        return col * CELL;
    }

    public static double worldZ(int row) {
        return row * CELL;
    }

    public static int cellCol(double x) {
        return (int) Math.round(x / CELL);
    }

    public static int cellRow(double z) {
        return (int) Math.round(z / CELL);
    }

    public static double tileCenterX(int tc) {
        return (tc - 1) * TILE;
    }

    public static double tileCenterZ(int tr) {
        return (tr - 1) * TILE;
    }

    private static double clamp(double v, double lo, double hi) {
        return Math.max(lo, Math.min(hi, v));
    }

    private static void addFloor(List<Triangle> out, double cx, double cz, double h,
                                int tr, int tc) {
        out.add(new Triangle(cx - h, 0, cz - h, cx + h, 0, cz - h, cx + h, 0, cz + h,
                Face.FLOOR, tr, tc));
        out.add(new Triangle(cx - h, 0, cz - h, cx + h, 0, cz + h, cx - h, 0, cz + h,
                Face.FLOOR, tr, tc));
        double y1 = WALL_HEIGHT;
        out.add(new Triangle(cx - h, y1, cz - h, cx + h, y1, cz + h, cx + h, y1, cz - h,
                Face.CEILING, tr, tc));
        out.add(new Triangle(cx - h, y1, cz - h, cx - h, y1, cz + h, cx + h, y1, cz + h,
                Face.CEILING, tr, tc));
    }

    private static void addBox(List<Triangle> out, double cx, double cz, double h,
                              int tr, int tc) {
        double y0 = 0;
        double y1 = WALL_HEIGHT;
        double x0 = cx - h;
        double x1 = cx + h;
        double z0 = cz - h;
        double z1 = cz + h;
        out.add(new Triangle(x0, y1, z0, x1, y1, z0, x1, y1, z1, Face.WALL, tr, tc));
        out.add(new Triangle(x0, y1, z0, x1, y1, z1, x0, y1, z1, Face.WALL, tr, tc));
        out.add(new Triangle(x0, y0, z0, x1, y0, z0, x1, y1, z0, Face.WALL, tr, tc));
        out.add(new Triangle(x0, y0, z0, x1, y1, z0, x0, y1, z0, Face.WALL, tr, tc));
        out.add(new Triangle(x0, y0, z1, x1, y1, z1, x1, y0, z1, Face.WALL, tr, tc));
        out.add(new Triangle(x0, y0, z1, x0, y1, z1, x1, y1, z1, Face.WALL, tr, tc));
        out.add(new Triangle(x0, y0, z0, x0, y1, z0, x0, y1, z1, Face.WALL, tr, tc));
        out.add(new Triangle(x0, y0, z0, x0, y1, z1, x0, y0, z1, Face.WALL, tr, tc));
        out.add(new Triangle(x1, y0, z0, x1, y0, z1, x1, y1, z1, Face.WALL, tr, tc));
        out.add(new Triangle(x1, y0, z0, x1, y1, z1, x1, y1, z0, Face.WALL, tr, tc));
    }
}
