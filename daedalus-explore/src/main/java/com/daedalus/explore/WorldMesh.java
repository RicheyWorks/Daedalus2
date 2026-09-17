// SPDX-License-Identifier: MIT

package com.daedalus.explore;

import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;
import com.daedalus.world.Chunk;
import com.daedalus.world.ChunkCoordinate;
import com.daedalus.world.World;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

/**
 * Second explore mesher: occupied cubes in a {@link World}, not
 * {@link ExploreMesh} stretched over chunks. Hidden faces against a solid
 * neighbor are culled. Collision is {@link World#contains}, not maze hulls.
 */
public final class WorldMesh {

    public enum Face {
        POS_X,
        NEG_X,
        POS_Y,
        NEG_Y,
        POS_Z,
        NEG_Z
    }

    public record Triangle(double x1, double y1, double z1,
                           double x2, double y2, double z2,
                           double x3, double y3, double z3,
                           Face face, BlockType type, BlockCoordinate at) {
        public Triangle {
            type = type == null ? BlockType.STONE : type;
        }
    }

    /** Same boot fraction as corridor wall skirting — cube sits, not floats. */
    public static final double BOOT_FRAC = 0.28;

    private static final int[][] DIRS = {
            {1, 0, 0}, {-1, 0, 0},
            {0, 1, 0}, {0, -1, 0},
            {0, 0, 1}, {0, 0, -1}
    };

    private final World world;
    private final List<Triangle> triangles;

    private WorldMesh(World world, List<Triangle> triangles) {
        this.world = world;
        this.triangles = triangles;
    }

    public static WorldMesh of(World world) {
        Objects.requireNonNull(world, "world");
        List<Triangle> out = new ArrayList<>();
        for (ChunkCoordinate cc : world.chunkKeys()) {
            Chunk chunk = world.chunk(cc);
            if (chunk == null) {
                continue;
            }
            int ox = cc.x() * Chunk.SIZE;
            int oy = cc.y() * Chunk.SIZE;
            int oz = cc.z() * Chunk.SIZE;
            for (int lz = 0; lz < Chunk.SIZE; lz++) {
                for (int ly = 0; ly < Chunk.SIZE; ly++) {
                    for (int lx = 0; lx < Chunk.SIZE; lx++) {
                        BlockType type = chunk.get(lx, ly, lz);
                        if (!type.solid()) {
                            continue;
                        }
                        BlockCoordinate at = new BlockCoordinate(ox + lx, oy + ly, oz + lz);
                        addExposed(world, out, at, type);
                    }
                }
            }
        }
        return new WorldMesh(world, List.copyOf(out));
    }

    public World world() {
        return world;
    }

    public List<Triangle> triangles() {
        return triangles;
    }

    /**
     * Discrete occupancy — the cube that contains the point, not a maze hull.
     */
    public boolean blocked(double x, double y, double z) {
        return world.contains(new BlockCoordinate(
                (int) Math.floor(x), (int) Math.floor(y), (int) Math.floor(z)));
    }

    private static void addExposed(World world, List<Triangle> out,
                                   BlockCoordinate at, BlockType type) {
        Face[] faces = Face.values();
        for (int i = 0; i < faces.length; i++) {
            int nx = at.x() + DIRS[i][0];
            int ny = at.y() + DIRS[i][1];
            int nz = at.z() + DIRS[i][2];
            if (world.contains(new BlockCoordinate(nx, ny, nz))) {
                continue;
            }
            emitFace(out, at, type, faces[i]);
        }
    }

    private static void emitFace(List<Triangle> out, BlockCoordinate at, BlockType type, Face face) {
        double x = at.x();
        double y = at.y();
        double z = at.z();
        double x1 = x + 1;
        double y1 = y + 1;
        double z1 = z + 1;
        switch (face) {
            case POS_X -> {
                side(out, x1, y, z, x1, y1, z, x1, y1, z1, x1, y, z1, face, type, at);
            }
            case NEG_X -> {
                side(out, x, y, z1, x, y1, z1, x, y1, z, x, y, z, face, type, at);
            }
            case POS_Y -> {
                quad(out, x, y1, z, x, y1, z1, x1, y1, z1, x1, y1, z, face, type, at);
            }
            case NEG_Y -> {
                quad(out, x, y, z1, x, y, z, x1, y, z, x1, y, z1, face, type, at);
            }
            case POS_Z -> {
                side(out, x1, y, z1, x1, y1, z1, x, y1, z1, x, y, z1, face, type, at);
            }
            case NEG_Z -> {
                side(out, x, y, z, x, y1, z, x1, y1, z, x1, y, z, face, type, at);
            }
            default -> {
                // Face is exhaustive; keep checkstyle happy if the enum grows.
            }
        }
    }

    private static void side(List<Triangle> out,
                             double ax, double ay, double az,
                             double bx, double by, double bz,
                             double cx, double cy, double cz,
                             double dx, double dy, double dz,
                             Face face, BlockType type, BlockCoordinate at) {
        double y0 = Math.min(ay, Math.min(by, Math.min(cy, dy)));
        double yb = y0 + BOOT_FRAC;
        quad(out, ax, y0, az, bx, yb, bz, cx, yb, cz, dx, y0, dz, face, type, at);
        quad(out, ax, yb, az, bx, by, bz, cx, cy, cz, dx, yb, dz, face, type, at);
    }

    private static void quad(List<Triangle> out,
                             double ax, double ay, double az,
                             double bx, double by, double bz,
                             double cx, double cy, double cz,
                             double dx, double dy, double dz,
                             Face face, BlockType type, BlockCoordinate at) {
        out.add(new Triangle(ax, ay, az, bx, by, bz, cx, cy, cz, face, type, at));
        out.add(new Triangle(ax, ay, az, cx, cy, cz, dx, dy, dz, face, type, at));
    }
}
