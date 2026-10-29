// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.SplittableRandom;

/**
 * Hammer Echo (contest gap G227): the forgemaster strikes a seeded run of hammer notes, and the guild seeks the
 * longest stretch that rings the same forwards and back.
 *
 * <p>The tool is plain: {@link #longest} is Manacher's O(n) longest palindromic substring and {@link #count} the number
 * of palindromic substrings, both on a {@code String}. Any project can use it for text or sequence symmetry checks.
 */
public final class HammerEcho {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_hammer_echo";

    /** Notes the hammer can ring. */
    public static final String NOTES = "abcd";

    /** How an echo went. */
    public enum Grade { TRUE, FAINT, FALSE }

    /** A stretch [from, to) of the run. */
    public record Echo(int from, int to) {

        /** Stretch length. */
        public int length() {
            return to - from;
        }
    }

    private HammerEcho() {
    }

    /** A seeded run of {@code n} notes from the first {@code k} of {@link #NOTES}. Same seed, same run. */
    public static String run(long seed, int n, int k) {
        if (n < 0 || k < 1 || k > NOTES.length()) {
            throw new IllegalArgumentException("need n >= 0 and 1 <= k <= " + NOTES.length());
        }
        SplittableRandom r = new SplittableRandom(seed);
        StringBuilder sb = new StringBuilder(n);
        for (int i = 0; i < n; i++) {
            sb.append(NOTES.charAt(r.nextInt(k)));
        }
        return sb.toString();
    }

    /** Manacher radii over the transformed string of length 2n+1 (separators between notes). */
    private static int[] radii(String s) {
        int m = 2 * s.length() + 1;
        int[] p = new int[m];
        int c = 0;
        int right = 0;
        for (int i = 0; i < m; i++) {
            int r = i < right ? Math.min(right - i, p[2 * c - i]) : 0;
            while (i - r - 1 >= 0 && i + r + 1 < m && same(s, i - r - 1, i + r + 1)) {
                r++;
            }
            p[i] = r;
            if (i + r > right) {
                c = i;
                right = i + r;
            }
        }
        return p;
    }

    private static boolean same(String s, int a, int b) {
        if ((a & 1) == 0) {
            return true;
        }
        return s.charAt(a / 2) == s.charAt(b / 2);
    }

    /** The longest palindromic stretch (earliest on ties); empty Echo(0, 0) for an empty run. */
    public static Echo longest(String s) {
        int[] p = radii(s);
        int bestLen = 0;
        int bestFrom = 0;
        for (int i = 0; i < p.length; i++) {
            int from = (i - p[i]) / 2;
            if (p[i] > bestLen || (p[i] == bestLen && p[i] > 0 && from < bestFrom)) {
                bestLen = p[i];
                bestFrom = from;
            }
        }
        return new Echo(bestFrom, bestFrom + bestLen);
    }

    /** Number of non-empty palindromic substrings (by position). */
    public static long count(String s) {
        long total = 0;
        for (int r : radii(s)) {
            total += (r + 1) / 2;
        }
        return total;
    }

    /** True if s[from, to) reads the same both ways. */
    public static boolean isEcho(String s, Echo e) {
        if (e.from() < 0 || e.to() > s.length() || e.from() > e.to()) {
            return false;
        }
        for (int i = e.from(), j = e.to() - 1; i < j; i++, j--) {
            if (s.charAt(i) != s.charAt(j)) {
                return false;
            }
        }
        return true;
    }

    /** FALSE if not a palindrome, TRUE at the longest length, FAINT at 75% or more, else FALSE. */
    public static Grade grade(String s, Echo e) {
        if (!isEcho(s, e)) {
            return Grade.FALSE;
        }
        int best = longest(s).length();
        if (e.length() == best) {
            return Grade.TRUE;
        }
        return 4 * e.length() >= 3 * best ? Grade.FAINT : Grade.FALSE;
    }

    /** The Forgemaster's line for an echo. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case TRUE -> "Forgemaster: the hall rings it back note for note. That is the longest echo in the run.";
            case FAINT -> "Forgemaster: it echoes, but a longer song hides in that run.";
            case FALSE -> "Forgemaster: the walls do not answer that. Listen again.";
        };
    }
}
