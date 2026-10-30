// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

/**
 * Tally Sums: cargo manifests are stamped with Adler-32 and Fletcher-16/32 checksums, and a fixed window slides
 * along a stream with an O(1) rolling Adler update.
 *
 * <p>Reusable plain byte[] API: {@link #adler32}, {@link #fletcher16}, {@link #fletcher32}, {@link #roll}.
 */
public final class TallySums {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_tally_sums";

    private static final int MOD_ADLER = 65_521;
    private static final int NMAX = 5552;

    /** Grade band. */
    public enum Grade { TALLIED, SHORT }

    private TallySums() {
    }

    /** Adler-32 of the whole array. */
    public static long adler32(byte[] data) {
        return adler32(data, 0, data.length);
    }

    /** Adler-32 of data[off, off+len), with deferred modulo. */
    public static long adler32(byte[] data, int off, int len) {
        if (off < 0 || len < 0 || off + len > data.length) {
            throw new IllegalArgumentException("range out of bounds");
        }
        long a = 1;
        long b = 0;
        int i = off;
        int end = off + len;
        while (i < end) {
            int stop = Math.min(end, i + NMAX);
            for (; i < stop; i++) {
                a += data[i] & 0xFF;
                b += a;
            }
            a %= MOD_ADLER;
            b %= MOD_ADLER;
        }
        return (b << 16) | a;
    }

    /** Adler-32 of a window of length n after dropping byte out and appending byte in. */
    public static long roll(long adler, int n, byte out, byte in) {
        long a = adler & 0xFFFF;
        long b = (adler >>> 16) & 0xFFFF;
        int o = out & 0xFF;
        int x = in & 0xFF;
        a = Math.floorMod(a - o + x, MOD_ADLER);
        b = Math.floorMod(b - (long) n * o + a - 1, MOD_ADLER);
        return (b << 16) | a;
    }

    /** Fletcher-16 over bytes (sums mod 255). */
    public static int fletcher16(byte[] data) {
        int s1 = 0;
        int s2 = 0;
        for (byte v : data) {
            s1 = (s1 + (v & 0xFF)) % 255;
            s2 = (s2 + s1) % 255;
        }
        return (s2 << 8) | s1;
    }

    /** Fletcher-32 over little-endian 16-bit words (odd tail zero-padded, sums mod 65535). */
    public static long fletcher32(byte[] data) {
        long s1 = 0;
        long s2 = 0;
        for (int i = 0; i < data.length; i += 2) {
            int w = data[i] & 0xFF;
            if (i + 1 < data.length) {
                w |= (data[i + 1] & 0xFF) << 8;
            }
            s1 = (s1 + w) % 65_535;
            s2 = (s2 + s1) % 65_535;
        }
        return (s2 << 16) | s1;
    }

    /** TALLIED when the claimed Adler-32 matches. */
    public static Grade grade(byte[] data, long claimed) {
        return adler32(data) == claimed ? Grade.TALLIED : Grade.SHORT;
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case TALLIED -> "Forgemaster: the stamp tallies with the cargo, crate for crate. Wave it through.";
            case SHORT -> "Forgemaster: the manifest comes up short. Something in that hold was changed.";
        };
    }
}
