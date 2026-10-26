// SPDX-License-Identifier: MIT

package com.daedalus.world.art;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.util.zip.CRC32;
import java.util.zip.Deflater;

/** A minimal PNG writer (8-bit RGB, no filtering, zlib): the same bytes for the same pixels, on every JVM. */
public final class Png {

    private Png() {
    }

    /** Encode {@code rgb} (0xRRGGBB, row-major, {@code w × h}) as a PNG. */
    public static byte[] encode(int w, int h, int[] rgb) {
        if (w < 1 || h < 1 || rgb.length != w * h) {
            throw new IllegalArgumentException("need " + w + "×" + h + " pixels, got " + rgb.length);
        }
        try {
            ByteArrayOutputStream raw = new ByteArrayOutputStream(h * (w * 3 + 1));
            for (int y = 0; y < h; y++) {
                raw.write(0);
                for (int x = 0; x < w; x++) {
                    int p = rgb[y * w + x];
                    raw.write((p >> 16) & 255);
                    raw.write((p >> 8) & 255);
                    raw.write(p & 255);
                }
            }
            Deflater deflater = new Deflater(Deflater.BEST_COMPRESSION);
            deflater.setInput(raw.toByteArray());
            deflater.finish();
            ByteArrayOutputStream z = new ByteArrayOutputStream();
            byte[] buf = new byte[65536];
            while (!deflater.finished()) {
                z.write(buf, 0, deflater.deflate(buf));
            }
            deflater.end();
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            out.write(new byte[] {(byte) 0x89, 'P', 'N', 'G', '\r', '\n', 0x1a, '\n'});
            ByteBuffer ihdr = ByteBuffer.allocate(13);
            ihdr.putInt(w).putInt(h).put((byte) 8).put((byte) 2).put((byte) 0).put((byte) 0).put((byte) 0);
            chunk(out, "IHDR", ihdr.array());
            chunk(out, "IDAT", z.toByteArray());
            chunk(out, "IEND", new byte[0]);
            return out.toByteArray();
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    private static void chunk(ByteArrayOutputStream out, String type, byte[] data) throws IOException {
        byte[] t = type.getBytes(StandardCharsets.US_ASCII);
        out.write(ByteBuffer.allocate(4).putInt(data.length).array());
        out.write(t);
        out.write(data);
        CRC32 crc = new CRC32();
        crc.update(t);
        crc.update(data);
        out.write(ByteBuffer.allocate(4).putInt((int) crc.getValue()).array());
    }
}
