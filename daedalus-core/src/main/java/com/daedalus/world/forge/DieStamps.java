// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.SplittableRandom;

/**
 * Die Stamps (contest gap G352): the mint keeps die patterns where {@code ?} stands for any one rune and {@code *} for
 * any run of runes, including none. Say which coin inscriptions a die could have struck.
 *
 * <p>The tool is plain: {@link #matches} is greedy wildcard matching that remembers the last star and backtracks to it
 * (O(n + m) typical, O(nm) worst), and {@link #matchesDp} is the O(nm) table used as a cross-check. Any project can use
 * it for simple glob-style filters on whole strings.
 */
public final class DieStamps {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_die_stamps";

    /** Runes used for seeded inscriptions. */
    public static final String RUNES = "fux";

    /** How an assay went. */
    public enum Grade { STRUCK, MISSTRUCK }

    private DieStamps() {
    }

    /** A seeded inscription of {@code n} runes. */
    public static String coin(long seed, int n) {
        return seeded(seed, n, RUNES);
    }

    /** A seeded die pattern of {@code n} symbols from runes, ? and *. */
    public static String die(long seed, int n) {
        return seeded(seed, n, RUNES + "?*");
    }

    private static String seeded(long seed, int n, String alphabet) {
        if (n < 0) {
            throw new IllegalArgumentException("need n >= 0");
        }
        SplittableRandom r = new SplittableRandom(seed);
        StringBuilder sb = new StringBuilder(n);
        for (int i = 0; i < n; i++) {
            sb.append(alphabet.charAt(r.nextInt(alphabet.length())));
        }
        return sb.toString();
    }

    /** True if the whole text matches the whole pattern. */
    public static boolean matches(String pattern, String text) {
        int p = 0;
        int t = 0;
        int star = -1;
        int mark = 0;
        while (t < text.length()) {
            if (p < pattern.length() && (pattern.charAt(p) == '?' || pattern.charAt(p) == text.charAt(t))) {
                p++;
                t++;
            } else if (p < pattern.length() && pattern.charAt(p) == '*') {
                star = p++;
                mark = t;
            } else if (star >= 0) {
                p = star + 1;
                t = ++mark;
            } else {
                return false;
            }
        }
        while (p < pattern.length() && pattern.charAt(p) == '*') {
            p++;
        }
        return p == pattern.length();
    }

    /** The same answer by dynamic programming over prefixes. */
    public static boolean matchesDp(String pattern, String text) {
        int n = pattern.length();
        int m = text.length();
        boolean[] prev = new boolean[m + 1];
        prev[0] = true;
        for (int i = 1; i <= n; i++) {
            char c = pattern.charAt(i - 1);
            boolean[] cur = new boolean[m + 1];
            cur[0] = c == '*' && prev[0];
            for (int j = 1; j <= m; j++) {
                if (c == '*') {
                    cur[j] = prev[j] || cur[j - 1];
                } else {
                    cur[j] = prev[j - 1] && (c == '?' || c == text.charAt(j - 1));
                }
            }
            prev = cur;
        }
        return prev[m];
    }

    /** STRUCK only if the claimed call is right. */
    public static Grade grade(String pattern, String text, boolean claimed) {
        return matches(pattern, text) == claimed ? Grade.STRUCK : Grade.MISSTRUCK;
    }

    /** The Forgemaster's line for an assay. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case STRUCK -> "Forgemaster: you matched coin to die at a glance. The mint master wants you.";
            case MISSTRUCK -> "Forgemaster: that die never struck that coin. Lay them side by side again.";
        };
    }
}
