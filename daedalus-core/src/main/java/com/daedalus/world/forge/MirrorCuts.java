// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.ArrayList;
import java.util.List;
import java.util.SplittableRandom;

/**
 * Mirror Cuts (contest gap G361): a strip of runes must be sheared into pieces that each read the same both ways. Find
 * the fewest shears and one way to cut.
 *
 * <p>The tool is plain: an O(n^2) palindrome table by centre expansion, then a min-cut array with back-pointers, so
 * {@link #minCuts} and {@link #pieces} both run in O(n^2) time. Any project can use it for palindrome partitioning.
 */
public final class MirrorCuts {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_mirror_cuts";

    /** Runes used for seeded strips. */
    public static final String RUNES = "fux";

    /** How a cutting went. */
    public enum Grade { MIRRORED, WARPED }

    private MirrorCuts() {
    }

    /** A seeded strip of {@code n} runes from the first {@code k} of {@link #RUNES}. */
    public static String strip(long seed, int n, int k) {
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

    private static boolean[][] table(String s) {
        int n = s.length();
        boolean[][] pal = new boolean[n][n];
        for (int c = 0; c < 2 * n - 1; c++) {
            int l = c / 2;
            int r = l + (c & 1);
            while (l >= 0 && r < n && s.charAt(l) == s.charAt(r)) {
                pal[l][r] = true;
                l--;
                r++;
            }
        }
        return pal;
    }

    /** Start index of the last piece in an optimal cut of s[0..i], for each i; plus cut counts. */
    private static int[][] plan(String s) {
        int n = s.length();
        boolean[][] pal = table(s);
        int[] cuts = new int[n];
        int[] from = new int[n];
        for (int i = 0; i < n; i++) {
            cuts[i] = Integer.MAX_VALUE;
            for (int j = 0; j <= i; j++) {
                if (pal[j][i]) {
                    int c = j == 0 ? 0 : cuts[j - 1] + 1;
                    if (c < cuts[i]) {
                        cuts[i] = c;
                        from[i] = j;
                    }
                }
            }
        }
        return new int[][] {cuts, from};
    }

    /** Fewest shears so every piece is a palindrome; 0 for an empty strip. */
    public static int minCuts(String s) {
        return s.isEmpty() ? 0 : plan(s)[0][s.length() - 1];
    }

    /** One optimal list of pieces, left to right. */
    public static List<String> pieces(String s) {
        List<String> out = new ArrayList<>();
        if (s.isEmpty()) {
            return out;
        }
        int[] from = plan(s)[1];
        int end = s.length() - 1;
        while (end >= 0) {
            int j = from[end];
            out.add(0, s.substring(j, end + 1));
            end = j - 1;
        }
        return out;
    }

    /** True if s reads the same both ways. */
    public static boolean isMirror(String s) {
        for (int i = 0, j = s.length() - 1; i < j; i++, j--) {
            if (s.charAt(i) != s.charAt(j)) {
                return false;
            }
        }
        return true;
    }

    /** MIRRORED only if the pieces rebuild the strip, all read both ways, and use the fewest shears. */
    public static Grade grade(String s, List<String> claimed) {
        boolean ok = String.join("", claimed).equals(s) && claimed.stream().allMatch(p -> !p.isEmpty() && isMirror(p))
                && claimed.size() - 1 == minCuts(s);
        return ok || (s.isEmpty() && claimed.isEmpty()) ? Grade.MIRRORED : Grade.WARPED;
    }

    /** The Forgemaster's line for a cutting. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case MIRRORED -> "Forgemaster: every charm reads true from either side, and not a shear wasted.";
            case WARPED -> "Forgemaster: a charm reads crooked, or you sheared more than you needed. Again.";
        };
    }
}
