package com.daedalus.world.audio;

import java.util.Arrays;
import java.util.Locale;

/** Immutable genome bytes (hex), the same hash that drives coats and bodies. Genes read as 0..1. */
public final class Genome {
    private final byte[] bytes;

    private Genome(byte[] bytes) {
        this.bytes = bytes;
    }

    /** Parses a non-empty even-length hex string; an optional 0x prefix is accepted. */
    public static Genome ofHex(String hex) {
        if (hex == null) {
            throw new IllegalArgumentException("genome hex is null");
        }
        String h = hex.strip().toLowerCase(Locale.ROOT);
        if (h.startsWith("0x")) {
            h = h.substring(2);
        }
        if (h.isEmpty() || h.length() % 2 != 0) {
            throw new IllegalArgumentException("genome hex must be non-empty and even length");
        }
        byte[] b = new byte[h.length() / 2];
        for (int i = 0; i < b.length; i++) {
            int hi = Character.digit(h.charAt(2 * i), 16);
            int lo = Character.digit(h.charAt(2 * i + 1), 16);
            if (hi < 0 || lo < 0) {
                throw new IllegalArgumentException("bad hex digit in genome");
            }
            b[i] = (byte) (hi << 4 | lo);
        }
        return new Genome(b);
    }

    /** Number of genes (bytes). */
    public int length() {
        return bytes.length;
    }

    /** Gene i as 0..1; indices wrap so short genomes still answer every trait. */
    public double gene(int i) {
        return (bytes[Math.floorMod(i, bytes.length)] & 0xff) / 255.0;
    }

    /** 64-bit seed folded from all genes (FNV-1a). */
    public long seed() {
        long h = 0xcbf29ce484222325L;
        for (byte x : bytes) {
            h ^= x & 0xff;
            h *= 0x100000001b3L;
        }
        return h;
    }

    @Override
    public boolean equals(Object o) {
        return o instanceof Genome g && Arrays.equals(bytes, g.bytes);
    }

    @Override
    public int hashCode() {
        return Arrays.hashCode(bytes);
    }
}
