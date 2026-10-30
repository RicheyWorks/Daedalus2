// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

/**
 * Bin Labels: storage bins carry labels in bijective base-k (no zero digit), like spreadsheet columns
 * A..Z, AA, AB, ... Every positive bin number has exactly one label over a given alphabet.
 *
 * <p>Reusable plain long/String API: {@link #label}, {@link #number}, {@link #advance}.
 */
public final class BinLabels {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_bin_labels";

    /** Spreadsheet-style alphabet. */
    public static final String LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";

    /** Grade band. */
    public enum Grade { FILED, MISFILED }

    private BinLabels() {
    }

    /** Label of bin n &gt;= 1 over alphabet (at least one distinct symbol). */
    public static String label(long n, String alphabet) {
        int k = checkAlphabet(alphabet);
        if (n < 1) {
            throw new IllegalArgumentException("bin numbers start at 1");
        }
        StringBuilder sb = new StringBuilder();
        long x = n;
        while (x > 0) {
            long d = (x - 1) % k;
            sb.append(alphabet.charAt((int) d));
            x = (x - 1) / k;
        }
        return sb.reverse().toString();
    }

    /** Bin number of a label; throws on unknown symbols, empty labels or overflow. */
    public static long number(String label, String alphabet) {
        int k = checkAlphabet(alphabet);
        if (label.isEmpty()) {
            throw new IllegalArgumentException("empty label");
        }
        long v = 0;
        try {
            for (int i = 0; i < label.length(); i++) {
                int d = alphabet.indexOf(label.charAt(i));
                if (d < 0) {
                    throw new IllegalArgumentException("unknown symbol at " + i);
                }
                v = Math.addExact(Math.multiplyExact(v, k), d + 1);
            }
        } catch (ArithmeticException e) {
            throw new IllegalArgumentException("label overflows a long", e);
        }
        return v;
    }

    /** Label steps bins after the given one (steps may be negative; result must stay &gt;= 1). */
    public static String advance(String label, long steps, String alphabet) {
        try {
            return label(Math.addExact(number(label, alphabet), steps), alphabet);
        } catch (ArithmeticException e) {
            throw new IllegalArgumentException("bin number overflows a long", e);
        }
    }

    /** FILED when the claimed label names bin n. */
    public static Grade grade(long n, String claimed) {
        try {
            return number(claimed, LETTERS) == n ? Grade.FILED : Grade.MISFILED;
        } catch (IllegalArgumentException e) {
            return Grade.MISFILED;
        }
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case FILED -> "Forgemaster: right bin, right label. No zero, no gaps, no doubles.";
            case MISFILED -> "Forgemaster: misfiled. After Z comes AA, not BA; count the shelf again.";
        };
    }

    private static int checkAlphabet(String alphabet) {
        if (alphabet.isEmpty()) {
            throw new IllegalArgumentException("empty alphabet");
        }
        for (int i = 0; i < alphabet.length(); i++) {
            if (alphabet.indexOf(alphabet.charAt(i)) != i) {
                throw new IllegalArgumentException("repeated symbol in alphabet");
            }
        }
        return alphabet.length();
    }
}
