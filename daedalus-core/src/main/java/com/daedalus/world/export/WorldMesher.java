// SPDX-License-Identifier: MIT

package com.daedalus.world.export;

import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;
import com.daedalus.world.Chunk;
import com.daedalus.world.ChunkCoordinate;
import com.daedalus.world.World;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

/**
 * Turns a world's cubes into triangle meshes, one per 16³ chunk, exactly as the web realm draws them
 * (ADR-032): a face is drawn when the neighbour beyond it is see-through and not the same cube type;
 * faces are shaded top 100%, ±X 86%, +Z 94%, −Z 78%, bottom 62%, times the realm's per-cube grain; colours
 * are linear RGB (sRGB decoded) as glTF expects. Opaque and translucent cubes go to separate parts, so an
 * engine can blend water, glass, rainbows and gate doorways. Winding is counter-clockwise from outside.
 */
public final class WorldMesher {

    /** One drawable part: positions, normals, linear RGB colours (3 floats each) and triangle indices. */
    public static final class Part {
        final FloatList positions = new FloatList();
        final FloatList normals = new FloatList();
        final FloatList colors = new FloatList();
        final IntList indices = new IntList();
        float[] min = {Float.MAX_VALUE, Float.MAX_VALUE, Float.MAX_VALUE};
        float[] max = {-Float.MAX_VALUE, -Float.MAX_VALUE, -Float.MAX_VALUE};

        public int vertexCount() {
            return positions.size() / 3;
        }

        public int faceCount() {
            return indices.size() / 6;
        }

        public boolean isEmpty() {
            return indices.size() == 0;
        }

        void vertex(float x, float y, float z, int nx, int ny, int nz, float r, float g, float b) {
            positions.add(x).add(y).add(z);
            normals.add(nx).add(ny).add(nz);
            colors.add(r).add(g).add(b);
            min[0] = Math.min(min[0], x);
            min[1] = Math.min(min[1], y);
            min[2] = Math.min(min[2], z);
            max[0] = Math.max(max[0], x);
            max[1] = Math.max(max[1], y);
            max[2] = Math.max(max[2], z);
        }
    }

    /** A chunk's two parts. */
    public record ChunkMesh(ChunkCoordinate at, Part opaque, Part translucent) {
    }

    private static final int[][] NORMALS = {{1, 0, 0}, {-1, 0, 0}, {0, 1, 0}, {0, -1, 0}, {0, 0, 1}, {0, 0, -1}};
    private static final double[] SHADE = {0.86, 0.86, 1.0, 0.62, 0.94, 0.78};
    private static final int[][][] CORNERS = {
        {{1, 0, 0}, {1, 1, 0}, {1, 1, 1}, {1, 0, 1}},
        {{0, 0, 1}, {0, 1, 1}, {0, 1, 0}, {0, 0, 0}},
        {{0, 1, 1}, {1, 1, 1}, {1, 1, 0}, {0, 1, 0}},
        {{0, 0, 0}, {1, 0, 0}, {1, 0, 1}, {0, 0, 1}},
        {{1, 0, 1}, {1, 1, 1}, {0, 1, 1}, {0, 0, 1}},
        {{0, 0, 0}, {0, 1, 0}, {1, 1, 0}, {1, 0, 0}},
    };

    private WorldMesher() {
    }

    /** Every non-empty chunk, meshed, in (y, z, x) order so the output is the same on every run. */
    public static List<ChunkMesh> mesh(World world) {
        List<ChunkCoordinate> keys = new ArrayList<>(world.chunkKeys());
        keys.sort(Comparator.comparingInt(ChunkCoordinate::y).thenComparingInt(ChunkCoordinate::z)
                .thenComparingInt(ChunkCoordinate::x));
        List<ChunkMesh> out = new ArrayList<>();
        BlockType[] palette = BlockType.values();
        for (ChunkCoordinate cc : keys) {
            Chunk chunk = world.chunk(cc);
            if (chunk == null || chunk.isEmpty()) {
                continue;
            }
            Part opaque = new Part();
            Part translucent = new Part();
            byte[] cubes = chunk.ordinals();
            int ox = cc.x() * Chunk.SIZE;
            int oy = cc.y() * Chunk.SIZE;
            int oz = cc.z() * Chunk.SIZE;
            for (int i = 0; i < cubes.length; i++) {
                BlockType type = palette[Byte.toUnsignedInt(cubes[i])];
                if (type == BlockType.AIR) {
                    continue;
                }
                int lx = i % Chunk.SIZE;
                int ly = (i / Chunk.SIZE) % Chunk.SIZE;
                int lz = i / (Chunk.SIZE * Chunk.SIZE);
                int x = ox + lx;
                int y = oy + ly;
                int z = oz + lz;
                Part part = BlockColors.translucent(type) ? translucent : opaque;
                float[] linear = linear(BlockColors.rgb(type));
                for (int f = 0; f < 6; f++) {
                    int[] n = NORMALS[f];
                    BlockType nb = world.get(new BlockCoordinate(x + n[0], y + n[1], z + n[2]));
                    if (!nb.seeThrough() || nb == type) {
                        continue;
                    }
                    double s = SHADE[f] * BlockColors.jitter(x, y, z);
                    int base = part.vertexCount();
                    for (int[] c : CORNERS[f]) {
                        // glTF requires colours in 0..1; the brightest cubes (cloud, ×1.06 grain) would overshoot.
                        part.vertex(x + c[0], y + c[1], z + c[2], n[0], n[1], n[2],
                                clamp(linear[0] * s), clamp(linear[1] * s), clamp(linear[2] * s));
                    }
                    part.indices.add(base).add(base + 1).add(base + 2).add(base).add(base + 2).add(base + 3);
                }
            }
            if (!opaque.isEmpty() || !translucent.isEmpty()) {
                out.add(new ChunkMesh(cc, opaque, translucent));
            }
        }
        return out;
    }

    private static float clamp(double v) {
        return (float) Math.max(0.0, Math.min(1.0, v));
    }

    /** sRGB 0xRRGGBB to linear RGB, the decode three.js's convertSRGBToLinear does. */
    static float[] linear(int rgb) {
        return new float[] {lin((rgb >> 16) & 255), lin((rgb >> 8) & 255), lin(rgb & 255)};
    }

    private static float lin(int c) {
        double v = c / 255.0;
        return (float) (v < 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4));
    }

    /** A growable float array without boxing. */
    static final class FloatList {
        private float[] a = new float[1024];
        private int n;

        FloatList add(float v) {
            if (n == a.length) {
                a = java.util.Arrays.copyOf(a, n * 2);
            }
            a[n++] = v;
            return this;
        }

        int size() {
            return n;
        }

        float get(int i) {
            return a[i];
        }

        float[] toArray() {
            return java.util.Arrays.copyOf(a, n);
        }
    }

    /** A growable int array without boxing. */
    static final class IntList {
        private int[] a = new int[1024];
        private int n;

        IntList add(int v) {
            if (n == a.length) {
                a = java.util.Arrays.copyOf(a, n * 2);
            }
            a[n++] = v;
            return this;
        }

        int size() {
            return n;
        }

        int get(int i) {
            return a[i];
        }
    }
}
