// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.Arrays;
import java.util.SplittableRandom;

/**
 * Maker Marks (contest gap G304): the guild archivist indexes a strip of maker's marks. Count how many distinct mark
 * sequences appear and find the longest sequence stamped twice, the forger's tell.
 *
 * <p>The tool is plain: {@link #suffixArray} is prefix doubling over packed {@code long} keys (O(n log^2 n)),
 * {@link #lcp} is Kasai's O(n) longest-common-prefix array, and the two answers fall out of them. Any project can use
 * it for substring statistics on strings shorter than {@link #MAX_LEN}.
 */
public final class MakerMarks {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_maker_marks";

    /** Marks used for seeded strips. */
    public static final String MARKS = "fuxa";

    /** Longest strip the packed-key sort supports. */
    public static final int MAX_LEN = 1 << 20;

    /** How an indexing went. */
    public enum Grade { INDEXED, SMUDGED }

    private MakerMarks() {
    }

    /** A seeded strip of {@code n} marks from the first {@code k} of {@link #MARKS}. */
    public static String strip(long seed, int n, int k) {
        if (n < 0 || k < 1 || k > MARKS.length()) {
            throw new IllegalArgumentException("need n >= 0 and 1 <= k <= " + MARKS.length());
        }
        SplittableRandom r = new SplittableRandom(seed);
        StringBuilder sb = new StringBuilder(n);
        for (int i = 0; i < n; i++) {
            sb.append(MARKS.charAt(r.nextInt(k)));
        }
        return sb.toString();
    }

    /** Start indices of all suffixes in lexicographic order. */
    public static int[] suffixArray(String s) {
        int n = s.length();
        if (n >= MAX_LEN) {
            throw new IllegalArgumentException("strip too long: " + n);
        }
        int[] rank = new int[n];
        for (int i = 0; i < n; i++) {
            rank[i] = s.charAt(i);
        }
        int[] sa = new int[n];
        long[] keys = new long[n];
        for (int k = 1; ; k <<= 1) {
            for (int i = 0; i < n; i++) {
                long second = i + k < n ? rank[i + k] + 1L : 0L;
                keys[i] = ((long) rank[i] << 41) | (second << 20) | i;
            }
            Arrays.sort(keys);
            int[] nr = new int[n];
            boolean tied = false;
            for (int j = 0; j < n; j++) {
                sa[j] = (int) (keys[j] & (MAX_LEN - 1));
                boolean fresh = j == 0 || (keys[j] >>> 20) != (keys[j - 1] >>> 20);
                tied |= !fresh;
                nr[sa[j]] = fresh ? j : nr[sa[j - 1]];
            }
            rank = nr;
            if (!tied || k >= n) {
                break;
            }
        }
        return sa;
    }

    /** lcp[j] = common prefix length of suffixes sa[j] and sa[j-1]; lcp[0] = 0 (Kasai). */
    public static int[] lcp(String s, int[] sa) {
        int n = s.length();
        int[] rank = new int[n];
        for (int j = 0; j < n; j++) {
            rank[sa[j]] = j;
        }
        int[] out = new int[n];
        int h = 0;
        for (int i = 0; i < n; i++) {
            if (rank[i] > 0) {
                int p = sa[rank[i] - 1];
                while (i + h < n && p + h < n && s.charAt(i + h) == s.charAt(p + h)) {
                    h++;
                }
                out[rank[i]] = h;
                if (h > 0) {
                    h--;
                }
            } else {
                h = 0;
            }
        }
        return out;
    }

    /** Number of distinct non-empty substrings. */
    public static long distinctSubstrings(String s) {
        int n = s.length();
        int[] sa = suffixArray(s);
        int[] l = lcp(s, sa);
        long total = (long) n * (n + 1) / 2;
        for (int v : l) {
            total -= v;
        }
        return total;
    }

    /** Longest substring occurring at least twice (overlaps allowed; earliest in suffix order on ties), or "". */
    public static String longestRepeat(String s) {
        int[] sa = suffixArray(s);
        int[] l = lcp(s, sa);
        int best = 0;
        int at = 0;
        for (int j = 1; j < l.length; j++) {
            if (l[j] > best) {
                best = l[j];
                at = sa[j];
            }
        }
        return s.substring(at, at + best);
    }

    /** INDEXED only if the distinct count and the repeat length are both right. */
    public static Grade grade(String s, long distinct, int repeatLength) {
        return distinct == distinctSubstrings(s) && repeatLength == longestRepeat(s).length()
                ? Grade.INDEXED : Grade.SMUDGED;
    }

    /** The Forgemaster's line for an indexing. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case INDEXED -> "Forgemaster: every mark tallied, and you caught the forger's double stamp.";
            case SMUDGED -> "Forgemaster: your ledger is smudged. Walk the strip again, mark by mark.";
        };
    }
}
