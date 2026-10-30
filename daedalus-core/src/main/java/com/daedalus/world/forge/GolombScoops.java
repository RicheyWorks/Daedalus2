// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.Arrays;
import java.util.SplittableRandom;

/**
 * Golomb Scoops: scoop counts are logged with Golomb codes as '0'/'1' strings: the quotient n / m in unary
 * (q ones then a zero), then the remainder in truncated binary. Rice codes are the case m = 2^k.
 *
 * <p>Reusable plain long/String API: {@link #encode}, {@link #encodeAll}, {@link #decodeAll}, {@link #length},
 * {@link #bestM}.
 */
public final class GolombScoops {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_golomb_scoops";

    /** Longest unary run allowed. */
    public static final long MAX_QUOTIENT = 1 << 20;

    /** Grade band. */
    public enum Grade { PACKED, SPILLED }

    private GolombScoops() {
    }

    /** Seeded geometric scoop log. */
    public static long[] scoopLog(long seed, int n, double p) {
        SplittableRandom r = new SplittableRandom(seed);
        long[] out = new long[n];
        for (int i = 0; i < n; i++) {
            long c = 0;
            while (r.nextDouble() > p && c < 10_000) {
                c++;
            }
            out[i] = c;
        }
        return out;
    }

    /** Golomb code of n &gt;= 0 with divisor m &gt;= 1. */
    public static String encode(long n, long m) {
        check(n, m);
        StringBuilder sb = new StringBuilder();
        long q = n / m;
        long r = n % m;
        for (long i = 0; i < q; i++) {
            sb.append('1');
        }
        sb.append('0');
        if (m > 1) {
            int b = bits(m);
            long u = (1L << b) - m;
            if (r < u) {
                appendBits(sb, r, b - 1);
            } else {
                appendBits(sb, r + u, b);
            }
        }
        return sb.toString();
    }

    /** Rice code (m = 2^k). */
    public static String rice(long n, int k) {
        if (k < 0 || k > 62) {
            throw new IllegalArgumentException("k out of range");
        }
        return encode(n, 1L << k);
    }

    /** Concatenated codes. */
    public static String encodeAll(long m, long... values) {
        StringBuilder sb = new StringBuilder();
        for (long v : values) {
            sb.append(encode(v, m));
        }
        return sb.toString();
    }

    /** All values in a stream; throws on a truncated or malformed stream. */
    public static long[] decodeAll(String s, long m) {
        check(0, m);
        long[] out = new long[16];
        int k = 0;
        int i = 0;
        int b = m > 1 ? bits(m) : 0;
        long u = m > 1 ? (1L << b) - m : 0;
        while (i < s.length()) {
            long q = 0;
            while (i < s.length() && s.charAt(i) == '1') {
                q++;
                i++;
                if (q > MAX_QUOTIENT) {
                    throw new IllegalArgumentException("unary run too long");
                }
            }
            if (i >= s.length() || s.charAt(i) != '0') {
                throw new IllegalArgumentException("truncated code");
            }
            i++;
            long r = 0;
            if (m > 1) {
                if (i + b - 1 > s.length()) {
                    throw new IllegalArgumentException("truncated remainder");
                }
                long x = readBits(s, i, b - 1);
                i += b - 1;
                if (x < u) {
                    r = x;
                } else {
                    if (i >= s.length()) {
                        throw new IllegalArgumentException("truncated remainder");
                    }
                    x = x * 2 + readBits(s, i, 1);
                    i++;
                    r = x - u;
                }
            }
            if (k == out.length) {
                out = Arrays.copyOf(out, 2 * k);
            }
            out[k++] = q * m + r;
        }
        return Arrays.copyOf(out, k);
    }

    /** Closed-form code length. */
    public static long length(long n, long m) {
        check(n, m);
        long q = n / m;
        if (m == 1) {
            return q + 1;
        }
        int b = bits(m);
        long u = (1L << b) - m;
        return q + 1 + (n % m < u ? b - 1 : b);
    }

    /** Divisor in [1, maxM] giving the shortest total code for log (smallest on ties). */
    public static long bestM(long[] log, long maxM) {
        long best = 1;
        long bestLen = Long.MAX_VALUE;
        for (long m = 1; m <= maxM; m++) {
            long total = 0;
            for (long v : log) {
                total += length(v, m);
            }
            if (total < bestLen) {
                bestLen = total;
                best = m;
            }
        }
        return best;
    }

    /** PACKED when the stream decodes to exactly the claimed log. */
    public static Grade grade(String bits, long m, long[] claimed) {
        try {
            return Arrays.equals(decodeAll(bits, m), claimed) ? Grade.PACKED : Grade.SPILLED;
        } catch (IllegalArgumentException e) {
            return Grade.SPILLED;
        }
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case PACKED -> "Forgemaster: every scoop logged tight, not a lump of coal unaccounted. Packed.";
            case SPILLED -> "Forgemaster: the log is spilled. A quotient or a remainder bit went astray.";
        };
    }

    private static int bits(long m) {
        return 64 - Long.numberOfLeadingZeros(m - 1);
    }

    private static void appendBits(StringBuilder sb, long v, int count) {
        for (int b = count - 1; b >= 0; b--) {
            sb.append(((v >> b) & 1L) == 1L ? '1' : '0');
        }
    }

    private static long readBits(String s, int from, int count) {
        long v = 0;
        for (int i = 0; i < count; i++) {
            char c = s.charAt(from + i);
            if (c != '0' && c != '1') {
                throw new IllegalArgumentException("bad bit");
            }
            v = v * 2 + (c - '0');
        }
        return v;
    }

    private static void check(long n, long m) {
        if (n < 0 || m < 1 || n / m > MAX_QUOTIENT) {
            throw new IllegalArgumentException("n or m out of range");
        }
    }
}
