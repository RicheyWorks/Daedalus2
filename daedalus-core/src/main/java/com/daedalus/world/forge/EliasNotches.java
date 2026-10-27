// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.Arrays;

/**
 * Elias Notches: tally sticks are notched with Elias universal codes (gamma, delta, omega) as '0'/'1' strings,
 * so positive counts of any size can be read back from one continuous stream.
 *
 * <p>Reusable plain long/String API: {@link #encode}, {@link #encodeAll}, {@link #decodeAll}, {@link #length}.
 */
public final class EliasNotches {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_elias_notches";

    /** Code family. */
    public enum Kind { GAMMA, DELTA, OMEGA }

    /** Grade band. */
    public enum Grade { READ, SPLINTERED }

    private EliasNotches() {
    }

    /** Code word for n &gt;= 1. */
    public static String encode(Kind kind, long n) {
        if (n < 1) {
            throw new IllegalArgumentException("n must be positive");
        }
        StringBuilder sb = new StringBuilder();
        switch (kind) {
            case GAMMA -> gamma(sb, n);
            case DELTA -> {
                int nb = 63 - Long.numberOfLeadingZeros(n);
                gamma(sb, nb + 1);
                for (int b = nb - 1; b >= 0; b--) {
                    sb.append(((n >>> b) & 1L) == 1L ? '1' : '0');
                }
            }
            case OMEGA -> {
                sb.append('0');
                long x = n;
                while (x > 1) {
                    String bin = Long.toBinaryString(x);
                    sb.insert(0, bin);
                    x = bin.length() - 1;
                }
            }
            default -> throw new IllegalArgumentException("unknown kind");
        }
        return sb.toString();
    }

    /** Concatenated code words. */
    public static String encodeAll(Kind kind, long... values) {
        StringBuilder sb = new StringBuilder();
        for (long v : values) {
            sb.append(encode(kind, v));
        }
        return sb.toString();
    }

    /** All values in a stream; throws on a truncated or malformed stream. */
    public static long[] decodeAll(Kind kind, String bits) {
        long[] out = new long[16];
        int k = 0;
        int[] pos = {0};
        while (pos[0] < bits.length()) {
            long v = switch (kind) {
                case GAMMA -> readGamma(bits, pos);
                case DELTA -> {
                    long nb = readGamma(bits, pos) - 1;
                    yield readBits(bits, pos, 1L, (int) nb);
                }
                case OMEGA -> readOmega(bits, pos);
            };
            if (k == out.length) {
                out = Arrays.copyOf(out, 2 * k);
            }
            out[k++] = v;
        }
        return Arrays.copyOf(out, k);
    }

    /** Closed-form code length. */
    public static int length(Kind kind, long n) {
        if (n < 1) {
            throw new IllegalArgumentException("n must be positive");
        }
        int nb = 63 - Long.numberOfLeadingZeros(n);
        return switch (kind) {
            case GAMMA -> 2 * nb + 1;
            case DELTA -> nb + 2 * (31 - Integer.numberOfLeadingZeros(nb + 1)) + 1;
            case OMEGA -> {
                int len = 1;
                long x = n;
                while (x > 1) {
                    int b = 64 - Long.numberOfLeadingZeros(x);
                    len += b;
                    x = b - 1;
                }
                yield len;
            }
        };
    }

    /** READ when the stream decodes to exactly the claimed counts. */
    public static Grade grade(Kind kind, String bits, long[] claimed) {
        try {
            return Arrays.equals(decodeAll(kind, bits), claimed) ? Grade.READ : Grade.SPLINTERED;
        } catch (IllegalArgumentException e) {
            return Grade.SPLINTERED;
        }
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case READ -> "Forgemaster: every notch read true, end to end, no count lost between them.";
            case SPLINTERED -> "Forgemaster: the stick is splintered. Find where one count ends, then read on.";
        };
    }

    private static void gamma(StringBuilder sb, long n) {
        int nb = 63 - Long.numberOfLeadingZeros(n);
        for (int i = 0; i < nb; i++) {
            sb.append('0');
        }
        for (int b = nb; b >= 0; b--) {
            sb.append(((n >>> b) & 1L) == 1L ? '1' : '0');
        }
    }

    private static long readGamma(String s, int[] pos) {
        int zeros = 0;
        while (pos[0] < s.length() && s.charAt(pos[0]) == '0') {
            zeros++;
            pos[0]++;
        }
        if (zeros > 62 || pos[0] >= s.length()) {
            throw new IllegalArgumentException("malformed gamma code");
        }
        pos[0]++;
        return readBits(s, pos, 1L, zeros);
    }

    private static long readOmega(String s, int[] pos) {
        long n = 1;
        while (true) {
            if (pos[0] >= s.length()) {
                throw new IllegalArgumentException("truncated omega code");
            }
            if (s.charAt(pos[0]) == '0') {
                pos[0]++;
                return n;
            }
            if (n > 62) {
                throw new IllegalArgumentException("omega value too large");
            }
            pos[0]++;
            n = readBits(s, pos, 1L, (int) n);
        }
    }

    private static long readBits(String s, int[] pos, long start, int count) {
        if (count < 0 || count > 62 || pos[0] + count > s.length()) {
            throw new IllegalArgumentException("truncated code");
        }
        long v = start;
        for (int i = 0; i < count; i++) {
            char c = s.charAt(pos[0]++);
            if (c != '0' && c != '1') {
                throw new IllegalArgumentException("bad notch");
            }
            v = (v << 1) | (c - '0');
        }
        return v;
    }
}
