// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.Arrays;

/**
 * Chain Links: counts are forged as LEB128 chains, 7 payload bits per link with the high bit marking that another
 * link follows. Unsigned (ULEB128) and signed (SLEB128, two's complement) forms are supported; decoding rejects
 * truncated, overlong (non-canonical) and overflowing chains.
 *
 * <p>Reusable plain long/byte[] API: {@link #encode}, {@link #encodeAll}, {@link #decodeAll}, {@link #length}.
 */
public final class ChainLinks {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_chain_links";

    /** Chain flavour. */
    public enum Kind { UNSIGNED, SIGNED }

    /** Grade band. */
    public enum Grade { LINKED, SNAPPED }

    private ChainLinks() {
    }

    /** Chain for v (UNSIGNED treats v as an unsigned 64-bit value). */
    public static byte[] encode(Kind kind, long v) {
        byte[] out = new byte[10];
        int k = 0;
        long x = v;
        if (kind == Kind.UNSIGNED) {
            do {
                int b = (int) (x & 0x7F);
                x >>>= 7;
                if (x != 0) {
                    b |= 0x80;
                }
                out[k++] = (byte) b;
            } while (x != 0);
        } else {
            boolean more = true;
            while (more) {
                int b = (int) (x & 0x7F);
                x >>= 7;
                boolean signBit = (b & 0x40) != 0;
                more = !((x == 0 && !signBit) || (x == -1 && signBit));
                if (more) {
                    b |= 0x80;
                }
                out[k++] = (byte) b;
            }
        }
        return Arrays.copyOf(out, k);
    }

    /** Concatenated chains. */
    public static byte[] encodeAll(Kind kind, long... values) {
        byte[] out = new byte[values.length * 10];
        int k = 0;
        for (long v : values) {
            byte[] c = encode(kind, v);
            System.arraycopy(c, 0, out, k, c.length);
            k += c.length;
        }
        return Arrays.copyOf(out, k);
    }

    /** All values in a stream of chains; throws on truncated, overlong or overflowing chains. */
    public static long[] decodeAll(Kind kind, byte[] data) {
        long[] out = new long[8];
        int n = 0;
        int i = 0;
        while (i < data.length) {
            long result = 0;
            int shift = 0;
            int start = i;
            int b;
            do {
                if (i >= data.length) {
                    throw new IllegalArgumentException("truncated chain at " + start);
                }
                b = data[i++] & 0xFF;
                int payload = b & 0x7F;
                if (shift == 63) {
                    boolean ok = kind == Kind.UNSIGNED ? payload <= 1 : payload == 0 || payload == 0x7F;
                    if (!ok || (b & 0x80) != 0) {
                        throw new IllegalArgumentException("overflowing chain at " + start);
                    }
                }
                result |= (long) payload << shift;
                shift += 7;
            } while ((b & 0x80) != 0);
            int len = i - start;
            if (kind == Kind.SIGNED && shift < 64 && (b & 0x40) != 0) {
                result |= -1L << shift;
            }
            if (len > 1) {
                int prev = data[i - 2] & 0xFF;
                boolean overlong = kind == Kind.UNSIGNED
                    ? b == 0
                    : (b == 0 && (prev & 0x40) == 0) || (b == 0x7F && (prev & 0x40) != 0);
                if (overlong) {
                    throw new IllegalArgumentException("overlong chain at " + start);
                }
            }
            if (n == out.length) {
                out = Arrays.copyOf(out, 2 * n);
            }
            out[n++] = result;
        }
        return Arrays.copyOf(out, n);
    }

    /** Closed-form chain length. */
    public static int length(Kind kind, long v) {
        int bits = kind == Kind.UNSIGNED
            ? 64 - Long.numberOfLeadingZeros(v)
            : 65 - Long.numberOfLeadingZeros(v ^ (v >> 63));
        return Math.max(1, (bits + 6) / 7);
    }

    /** LINKED when the stream decodes to exactly the claimed values. */
    public static Grade grade(Kind kind, byte[] data, long[] claimed) {
        try {
            return Arrays.equals(decodeAll(kind, data), claimed) ? Grade.LINKED : Grade.SNAPPED;
        } catch (IllegalArgumentException e) {
            return Grade.SNAPPED;
        }
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case LINKED -> "Forgemaster: every chain closed where it should, not one link spare. Well linked.";
            case SNAPPED -> "Forgemaster: a chain snapped. Mind the high bit on each link before you close it.";
        };
    }
}
