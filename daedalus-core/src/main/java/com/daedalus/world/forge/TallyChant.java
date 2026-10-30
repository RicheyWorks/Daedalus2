// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

/**
 * Tally Chant: apprentices chant the look-and-say tally, reading the previous chant aloud as (run length, digit)
 * pairs. "1" becomes "11", then "21", "1211", "111221", and so on.
 *
 * <p>Reusable plain String API: {@link #describe}, {@link #undescribe}, {@link #nth}, {@link #lengthOf}.
 */
public final class TallyChant {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_tally_chant";

    /** Longest chant produced. */
    public static final int MAX_LEN = 1 << 22;

    /** Grade band. */
    public enum Grade { CHANTED, STAMMERED }

    private TallyChant() {
    }

    /** Next chant: run lengths (in decimal) followed by the digit. */
    public static String describe(String s) {
        StringBuilder sb = new StringBuilder();
        int i = 0;
        while (i < s.length()) {
            char c = s.charAt(i);
            if (c < '0' || c > '9') {
                throw new IllegalArgumentException("not a digit at " + i);
            }
            int j = i;
            while (j < s.length() && s.charAt(j) == c) {
                j++;
            }
            sb.append(j - i).append(c);
            if (sb.length() > MAX_LEN) {
                throw new IllegalArgumentException("chant too long");
            }
            i = j;
        }
        return sb.toString();
    }

    /** Predecessor of a chant whose run lengths are single digits; throws when no such predecessor exists. */
    public static String undescribe(String s) {
        if ((s.length() & 1) == 1) {
            throw new IllegalArgumentException("odd length");
        }
        StringBuilder sb = new StringBuilder();
        char last = 0;
        for (int i = 0; i < s.length(); i += 2) {
            char cnt = s.charAt(i);
            char d = s.charAt(i + 1);
            if (cnt < '1' || cnt > '9' || d < '0' || d > '9' || d == last) {
                throw new IllegalArgumentException("bad pair at " + i / 2);
            }
            for (int k = 0; k < cnt - '0'; k++) {
                sb.append(d);
            }
            last = d;
        }
        return sb.toString();
    }

    /** The n-th chant (1-based) starting from seed. */
    public static String nth(String seed, int n) {
        if (n < 1) {
            throw new IllegalArgumentException("n must be positive");
        }
        String s = seed;
        for (int i = 1; i < n; i++) {
            s = describe(s);
        }
        return s;
    }

    /** Length of the n-th chant from "1". */
    public static int lengthOf(int n) {
        return nth("1", n).length();
    }

    /** CHANTED when claimed is the chant after prev. */
    public static Grade grade(String prev, String claimed) {
        return describe(prev).equals(claimed) ? Grade.CHANTED : Grade.STAMMERED;
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case CHANTED -> "Forgemaster: read aloud true, run by run. The apprentices keep the beat.";
            case STAMMERED -> "Forgemaster: you stammered. Count each run before you name its digit.";
        };
    }
}
