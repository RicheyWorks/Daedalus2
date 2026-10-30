// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

/**
 * Parity Plates: forge signals are stamped as Hamming(7,4) plates plus an overall parity bit (SECDED 8,4).
 * Bit i-1 of a plate holds Hamming position i (1..7); bit 7 holds overall parity. Data sits at positions
 * 3, 5, 6, 7 and parity at 1, 2, 4. Any single flip is corrected and any double flip is flagged.
 *
 * <p>Reusable plain int API: {@link #encode}, {@link #decode}, {@link #syndrome}, plus byte helpers.
 */
public final class ParityPlates {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_parity_plates";

    private static final int[] DATA_POS = {3, 5, 6, 7};

    /** Decode outcome. */
    public enum Status { CLEAN, CORRECTED, DOUBLE }

    /** Grade band. */
    public enum Grade { MENDED, GARBLED }

    /** Decoded nibble (-1 when a double flip was detected) and status. */
    public record Decoded(int data, Status status) {
    }

    private ParityPlates() {
    }

    /** 8-bit SECDED plate for a 4-bit nibble. */
    public static int encode(int nibble) {
        if (nibble < 0 || nibble > 15) {
            throw new IllegalArgumentException("nibble out of range: " + nibble);
        }
        int w = 0;
        for (int i = 0; i < 4; i++) {
            if (((nibble >>> i) & 1) == 1) {
                w |= 1 << (DATA_POS[i] - 1);
            }
        }
        int s = syndrome(w);
        if ((s & 1) == 1) {
            w |= 1;
        }
        if ((s & 2) == 2) {
            w |= 1 << 1;
        }
        if ((s & 4) == 4) {
            w |= 1 << 3;
        }
        if ((Integer.bitCount(w) & 1) == 1) {
            w |= 1 << 7;
        }
        return w;
    }

    /** XOR of the Hamming positions (1..7) whose bits are set; 0 for a valid Hamming(7,4) word. */
    public static int syndrome(int plate) {
        int s = 0;
        for (int p = 1; p <= 7; p++) {
            if (((plate >>> (p - 1)) & 1) == 1) {
                s ^= p;
            }
        }
        return s;
    }

    /** Correct a single flip or flag a double flip. */
    public static Decoded decode(int plate) {
        if (plate < 0 || plate > 255) {
            throw new IllegalArgumentException("plate out of range: " + plate);
        }
        int s = syndrome(plate);
        boolean odd = (Integer.bitCount(plate) & 1) == 1;
        int w = plate;
        Status st;
        if (!odd && s == 0) {
            st = Status.CLEAN;
        } else if (odd) {
            st = Status.CORRECTED;
            w ^= s == 0 ? 1 << 7 : 1 << (s - 1);
        } else {
            return new Decoded(-1, Status.DOUBLE);
        }
        int d = 0;
        for (int i = 0; i < 4; i++) {
            if (((w >>> (DATA_POS[i] - 1)) & 1) == 1) {
                d |= 1 << i;
            }
        }
        return new Decoded(d, st);
    }

    /** Two plates per byte (low nibble first). */
    public static byte[] encodeBytes(byte[] data) {
        byte[] out = new byte[data.length * 2];
        for (int i = 0; i < data.length; i++) {
            out[2 * i] = (byte) encode(data[i] & 0xF);
            out[2 * i + 1] = (byte) encode((data[i] >>> 4) & 0xF);
        }
        return out;
    }

    /** Inverse of {@link #encodeBytes}; throws when any plate shows a double flip. */
    public static byte[] decodeBytes(byte[] plates) {
        if ((plates.length & 1) == 1) {
            throw new IllegalArgumentException("odd plate count");
        }
        byte[] out = new byte[plates.length / 2];
        for (int i = 0; i < out.length; i++) {
            Decoded lo = decode(plates[2 * i] & 0xFF);
            Decoded hi = decode(plates[2 * i + 1] & 0xFF);
            if (lo.status() == Status.DOUBLE || hi.status() == Status.DOUBLE) {
                throw new IllegalArgumentException("double flip at byte " + i);
            }
            out[i] = (byte) (lo.data() | (hi.data() << 4));
        }
        return out;
    }

    /** MENDED when the decoded nibble matches what was sent. */
    public static Grade grade(int sent, Decoded d) {
        return d.data() == sent ? Grade.MENDED : Grade.GARBLED;
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case MENDED -> "Forgemaster: the spark struck, the parity caught it, the signal reads true. Mended.";
            case GARBLED -> "Forgemaster: garbled. Check the syndrome before you trust that plate.";
        };
    }
}
