// SPDX-License-Identifier: MIT

package com.daedalus.world.island;

import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.ByteBuffer;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.zip.CRC32;
import java.util.zip.Deflater;

/**
 * An isometric portrait of an island as its seed grows it (ADR-027): the picture a deed shows.
 * Pure Java — no AWT, no fonts — so it renders the same on a headless server and in a test, and
 * the pixels are a function of the plan alone. {@link #digest()} pins them.
 *
 * <p>Projection: the camera looks down from +X, +Y, +Z. A cube's top-face centre lands at
 * {@code ((x − z)·a, (x + z)·a/2 − y·a)} for a cube edge of {@code a} pixels, chosen so the whole
 * island fits the frame (clouds do not count; they may run off the edge). Cubes are painted far to near by {@code x + y + z}; a cube whose three
 * camera-facing neighbours are all opaque is never seen and is skipped. Faces are shaded top 100%,
 * +Z 80%, +X 64%, with a ±6% per-cube jitter like the realm's mesher; water and glass blend.
 */
public final class IslandPortrait {

    public static final int SIZE = 512;
    private static final int MARGIN = 24;

    private final int[] argb;

    private IslandPortrait(int[] argb) {
        this.argb = argb;
    }

    public int width() {
        return SIZE;
    }

    public int height() {
        return SIZE;
    }

    /** A copy of the pixels, row-major ARGB. */
    public int[] pixels() {
        return argb.clone();
    }

    public static IslandPortrait of(IslandPlan plan) {
        Map<BlockCoordinate, BlockType> blocks = plan.blocks();
        int minSx = Integer.MAX_VALUE;
        int maxSx = Integer.MIN_VALUE;
        int minSy = Integer.MAX_VALUE;
        int maxSy = Integer.MIN_VALUE;
        for (Map.Entry<BlockCoordinate, BlockType> e : blocks.entrySet()) {
            if (e.getValue() == BlockType.CLOUD) {
                continue;                          // frame the island; a drifting cloud may crop
            }
            BlockCoordinate c = e.getKey();
            int sx = c.x() - c.z();
            int sy2 = c.x() + c.z() - 2 * c.y();   // screen y in half-units of a
            minSx = Math.min(minSx, sx);
            maxSx = Math.max(maxSx, sx);
            minSy = Math.min(minSy, sy2);
            maxSy = Math.max(maxSy, sy2);
        }
        // The cube's sprite spans [sx·a − a, sx·a + a] and [sy·a/2 − a/2, sy·a/2 + 3a/2].
        int wUnits = (maxSx - minSx) + 2;
        int hUnits = (maxSy - minSy) / 2 + 2;
        int a = Math.max(2, Math.min(12, Math.min((SIZE - 2 * MARGIN) / wUnits, (SIZE - 2 * MARGIN) / hUnits)));
        a -= a % 2;
        int ox = (SIZE - (maxSx + minSx) * a) / 2;
        int oy = (SIZE - (maxSy + minSy) * a / 2 - a) / 2;

        int[] px = new int[SIZE * SIZE];
        for (int y = 0; y < SIZE; y++) {
            int sky = sky(y / (double) (SIZE - 1));
            for (int x = 0; x < SIZE; x++) {
                px[y * SIZE + x] = sky;
            }
        }
        byte[] mask = sprite(a);
        List<Map.Entry<BlockCoordinate, BlockType>> order = new ArrayList<>();
        for (Map.Entry<BlockCoordinate, BlockType> e : blocks.entrySet()) {
            BlockCoordinate c = e.getKey();
            if (opaque(blocks, c.x() + 1, c.y(), c.z()) && opaque(blocks, c.x(), c.y() + 1, c.z())
                    && opaque(blocks, c.x(), c.y(), c.z() + 1)) {
                continue;
            }
            order.add(e);
        }
        order.sort(Comparator.<Map.Entry<BlockCoordinate, BlockType>>comparingInt(
                e -> e.getKey().x() + e.getKey().y() + e.getKey().z())
                .thenComparingInt(e -> e.getKey().y())
                .thenComparingInt(e -> e.getKey().x()));
        for (Map.Entry<BlockCoordinate, BlockType> e : order) {
            BlockCoordinate c = e.getKey();
            BlockType t = e.getValue();
            int base = com.daedalus.world.export.BlockColors.rgb(t);
            double j = jitter(c.x(), c.y(), c.z());
            boolean blend = t == BlockType.WATER || t == BlockType.GLASS;
            int left = ox + (c.x() - c.z()) * a - a;
            int top = oy + (c.x() + c.z()) * a / 2 - c.y() * a - a / 2;
            int w = 2 * a;
            int h = 2 * a;
            for (int sy = 0; sy < h; sy++) {
                int y = top + sy;
                if (y < 0 || y >= SIZE) {
                    continue;
                }
                for (int sx = 0; sx < w; sx++) {
                    int face = mask[sy * w + sx];
                    int x = left + sx;
                    if (face == 0 || x < 0 || x >= SIZE) {
                        continue;
                    }
                    double shade = (face == 1 ? 1.0 : face == 2 ? 0.80 : 0.64) * j;
                    int rgb = scale(base, shade);
                    int at = y * SIZE + x;
                    px[at] = blend ? mix(px[at], rgb, 0.68) : 0xFF000000 | rgb;
                }
            }
        }
        return new IslandPortrait(px);
    }

    private static boolean opaque(Map<BlockCoordinate, BlockType> blocks, int x, int y, int z) {
        BlockType t = blocks.get(new BlockCoordinate(x, y, z));
        return t != null && t != BlockType.WATER && t != BlockType.GLASS && t != BlockType.CLOUD;
    }

    /** Face index per pixel of a cube sprite {@code 2a × 2a}: 0 none, 1 top, 2 +Z side, 3 +X side. */
    static byte[] sprite(int a) {
        int w = 2 * a;
        int h = 2 * a;
        byte[] m = new byte[w * h];
        double half = a / 2.0;
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                double px = x + 0.5;
                double py = y + 0.5;
                // Top rhombus: centre (a, a/2), |dx|/a + |dy|/(a/2) <= 1.
                if (Math.abs(px - a) / a + Math.abs(py - half) / half <= 1.0) {
                    m[y * w + x] = 1;
                    continue;
                }
                // Sides: between the rhombus's lower edges and the same edges dropped by a.
                double lower = px <= a ? half + px * half / a : half + (w - px) * half / a;
                if (py >= half && py >= lower - 1e-9 && py <= lower + a) {
                    m[y * w + x] = (byte) (px <= a ? 2 : 3);
                }
            }
        }
        return m;
    }

    private static int sky(double t) {
        int top = 0x1f3f86;
        int mid = 0x8fa9d6;
        int low = 0xf2b98a;
        return 0xFF000000 | (t < 0.55 ? lerp(top, mid, t / 0.55) : lerp(mid, low, (t - 0.55) / 0.45));
    }

    private static int lerp(int c0, int c1, double t) {
        int r = (int) Math.round(((c0 >> 16) & 255) + (((c1 >> 16) & 255) - ((c0 >> 16) & 255)) * t);
        int g = (int) Math.round(((c0 >> 8) & 255) + (((c1 >> 8) & 255) - ((c0 >> 8) & 255)) * t);
        int b = (int) Math.round((c0 & 255) + ((c1 & 255) - (c0 & 255)) * t);
        return (r << 16) | (g << 8) | b;
    }

    private static int scale(int rgb, double k) {
        int r = Math.min(255, (int) Math.round(((rgb >> 16) & 255) * k));
        int g = Math.min(255, (int) Math.round(((rgb >> 8) & 255) * k));
        int b = Math.min(255, (int) Math.round((rgb & 255) * k));
        return (r << 16) | (g << 8) | b;
    }

    private static int mix(int under, int over, double alpha) {
        return 0xFF000000 | lerp(under & 0xFFFFFF, over, alpha);
    }

    /** The realm mesher's per-cube brightness, so the portrait has the same grain. */
    static double jitter(int x, int y, int z) {
        return com.daedalus.world.export.BlockColors.jitter(x, y, z);
    }

    /** SHA-256 over the ARGB pixels: the same island, the same picture, on any JVM. */
    public String digest() {
        try {
            MessageDigest sha = MessageDigest.getInstance("SHA-256");
            ByteBuffer buf = ByteBuffer.allocate(argb.length * 4);
            for (int p : argb) {
                buf.putInt(p);
            }
            return HexFormat.of().formatHex(sha.digest(buf.array()));
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 is required by every JVM", e);
        }
    }

    /** The portrait as a PNG (8-bit RGB, no filtering, zlib). */
    public byte[] png() {
        try {
            ByteArrayOutputStream raw = new ByteArrayOutputStream(SIZE * (SIZE * 3 + 1));
            for (int y = 0; y < SIZE; y++) {
                raw.write(0);
                for (int x = 0; x < SIZE; x++) {
                    int p = argb[y * SIZE + x];
                    raw.write((p >> 16) & 255);
                    raw.write((p >> 8) & 255);
                    raw.write(p & 255);
                }
            }
            Deflater deflater = new Deflater(Deflater.BEST_COMPRESSION);
            deflater.setInput(raw.toByteArray());
            deflater.finish();
            ByteArrayOutputStream z = new ByteArrayOutputStream();
            byte[] chunk = new byte[65536];
            while (!deflater.finished()) {
                int n = deflater.deflate(chunk);
                z.write(chunk, 0, n);
            }
            deflater.end();

            ByteArrayOutputStream out = new ByteArrayOutputStream();
            out.write(new byte[] {(byte) 0x89, 'P', 'N', 'G', '\r', '\n', 0x1a, '\n'});
            ByteBuffer ihdr = ByteBuffer.allocate(13);
            ihdr.putInt(SIZE).putInt(SIZE).put((byte) 8).put((byte) 2).put((byte) 0).put((byte) 0).put((byte) 0);
            chunk(out, "IHDR", ihdr.array());
            chunk(out, "IDAT", z.toByteArray());
            chunk(out, "IEND", new byte[0]);
            return out.toByteArray();
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    private static void chunk(ByteArrayOutputStream out, String type, byte[] data) throws IOException {
        byte[] t = type.getBytes(java.nio.charset.StandardCharsets.US_ASCII);
        out.write(ByteBuffer.allocate(4).putInt(data.length).array());
        out.write(t);
        out.write(data);
        CRC32 crc = new CRC32();
        crc.update(t);
        crc.update(data);
        out.write(ByteBuffer.allocate(4).putInt((int) crc.getValue()).array());
    }
}
