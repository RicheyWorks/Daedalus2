// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.Arrays;
import java.util.SplittableRandom;

/**
 * Scroll Fold (contest gap G364): the archivist folds rune scrolls for storage with a Burrows-Wheeler transform and
 * move-to-front coding, and must unfold them exactly.
 *
 * <p>The tool is plain: {@link #fold} sorts cyclic rotations by prefix doubling over packed {@code long} keys (ties by
 * start index) and returns the last column plus the primary row; {@link #unfold} inverts it with the LF mapping in
 * O(n); {@link #mtf} and {@link #unmtf} code characters below 256. Any project can use it as a compression stage.
 */
public final class ScrollFold {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_scroll_fold";

    /** Runes used for seeded scrolls. */
    public static final String RUNES = "fuxae";

    /** Longest scroll the packed sort supports. */
    public static final int MAX_LEN = 1 << 20;

    /** How a folding went. */
    public enum Grade { UNFOLDED, TORN }

    /** A folded scroll: the last column of sorted rotations and the row holding the original. */
    public record Folded(String last, int primary) {
    }

    private ScrollFold() {
    }

    /** A seeded scroll of {@code n} runes from the first {@code k} of {@link #RUNES}. */
    public static String scroll(long seed, int n, int k) {
        if (n < 0 || k < 1 || k > RUNES.length()) {
            throw new IllegalArgumentException("need n >= 0 and 1 <= k <= " + RUNES.length());
        }
        SplittableRandom r = new SplittableRandom(seed);
        StringBuilder sb = new StringBuilder(n);
        for (int i = 0; i < n; i++) {
            sb.append(RUNES.charAt(r.nextInt(k)));
        }
        return sb.toString();
    }

    /** Start indices of cyclic rotations in sorted order (equal rotations by start index). */
    public static int[] rotations(String s) {
        int n = s.length();
        if (n >= MAX_LEN) {
            throw new IllegalArgumentException("scroll too long: " + n);
        }
        int[] rank = new int[n];
        for (int i = 0; i < n; i++) {
            rank[i] = s.charAt(i);
        }
        int[] order = new int[n];
        long[] keys = new long[n];
        for (int k = 1; ; k <<= 1) {
            for (int i = 0; i < n; i++) {
                keys[i] = ((long) rank[i] << 41) | ((long) rank[(i + k % n) % n] << 20) | i;
            }
            Arrays.sort(keys);
            int[] nr = new int[n];
            for (int j = 0; j < n; j++) {
                order[j] = (int) (keys[j] & (MAX_LEN - 1));
                boolean fresh = j == 0 || (keys[j] >>> 20) != (keys[j - 1] >>> 20);
                nr[order[j]] = fresh ? j : nr[order[j - 1]];
            }
            rank = nr;
            if (k >= n) {
                break;
            }
        }
        return order;
    }

    /** Burrows-Wheeler fold. */
    public static Folded fold(String s) {
        int n = s.length();
        if (n == 0) {
            return new Folded("", 0);
        }
        int[] order = rotations(s);
        StringBuilder sb = new StringBuilder(n);
        int primary = 0;
        for (int j = 0; j < n; j++) {
            sb.append(s.charAt((order[j] + n - 1) % n));
            if (order[j] == 0) {
                primary = j;
            }
        }
        return new Folded(sb.toString(), primary);
    }

    /** Inverse fold by LF mapping. */
    public static String unfold(Folded f) {
        String l = f.last();
        int n = l.length();
        if (n == 0) {
            return "";
        }
        if (f.primary() < 0 || f.primary() >= n) {
            throw new IllegalArgumentException("primary row out of range");
        }
        int[] count = new int[Character.MAX_VALUE + 1];
        int[] occ = new int[n];
        for (int j = 0; j < n; j++) {
            occ[j] = count[l.charAt(j)]++;
        }
        int[] start = new int[count.length];
        int sum = 0;
        for (int c = 0; c < count.length; c++) {
            start[c] = sum;
            sum += count[c];
        }
        char[] out = new char[n];
        int p = f.primary();
        for (int t = n - 1; t >= 0; t--) {
            char c = l.charAt(p);
            out[t] = c;
            p = start[c] + occ[p];
        }
        return new String(out);
    }

    /** Move-to-front codes for characters below 256. */
    public static int[] mtf(String s) {
        int[] table = new int[256];
        for (int i = 0; i < 256; i++) {
            table[i] = i;
        }
        int[] out = new int[s.length()];
        for (int i = 0; i < s.length(); i++) {
            int c = s.charAt(i);
            if (c >= 256) {
                throw new IllegalArgumentException("move-to-front needs characters below 256");
            }
            int j = 0;
            while (table[j] != c) {
                j++;
            }
            out[i] = j;
            System.arraycopy(table, 0, table, 1, j);
            table[0] = c;
        }
        return out;
    }

    /** Inverse of {@link #mtf}. */
    public static String unmtf(int[] codes) {
        int[] table = new int[256];
        for (int i = 0; i < 256; i++) {
            table[i] = i;
        }
        StringBuilder sb = new StringBuilder(codes.length);
        for (int j : codes) {
            if (j < 0 || j >= 256) {
                throw new IllegalArgumentException("bad code " + j);
            }
            int c = table[j];
            sb.append((char) c);
            System.arraycopy(table, 0, table, 1, j);
            table[0] = c;
        }
        return sb.toString();
    }

    /** UNFOLDED only if the claimed fold is exactly right. */
    public static Grade grade(String s, Folded claimed) {
        return fold(s).equals(claimed) ? Grade.UNFOLDED : Grade.TORN;
    }

    /** The Forgemaster's line for a folding. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case UNFOLDED -> "Forgemaster: folded tight and opened whole, not a rune astray. The archive thanks you.";
            case TORN -> "Forgemaster: that scroll will not open the same. Fold it again, slower.";
        };
    }
}
