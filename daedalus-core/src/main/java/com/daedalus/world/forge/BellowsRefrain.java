// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.Arrays;
import java.util.SplittableRandom;

/**
 * Bellows Refrain (contest gap G230): the bellows wheeze a seeded run of puffs. Find every place a guild refrain occurs
 * (overlaps allowed) and the shortest motif whose repeats build the whole run.
 *
 * <p>The tool is plain: {@link #prefixFunction} is the KMP failure table, {@link #occurrences} the O(n+m) search for
 * every start of a pattern in a text, and {@link #period} the shortest period of a string. Any project can use it for
 * pattern search or repeat detection.
 */
public final class BellowsRefrain {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_bellows_refrain";

    /** Puffs the bellows can make. */
    public static final String PUFFS = "hwo";

    /** How a guess went. */
    public enum Grade { IN_TUNE, OFF }

    private BellowsRefrain() {
    }

    /** A seeded run of {@code n} puffs from the first {@code k} of {@link #PUFFS}. Same seed, same run. */
    public static String run(long seed, int n, int k) {
        if (n < 0 || k < 1 || k > PUFFS.length()) {
            throw new IllegalArgumentException("need n >= 0 and 1 <= k <= " + PUFFS.length());
        }
        SplittableRandom r = new SplittableRandom(seed);
        StringBuilder sb = new StringBuilder(n);
        for (int i = 0; i < n; i++) {
            sb.append(PUFFS.charAt(r.nextInt(k)));
        }
        return sb.toString();
    }

    /** pi[i] = length of the longest proper prefix of s[0..i] that is also its suffix. */
    public static int[] prefixFunction(String s) {
        int[] pi = new int[s.length()];
        for (int i = 1; i < s.length(); i++) {
            int k = pi[i - 1];
            while (k > 0 && s.charAt(i) != s.charAt(k)) {
                k = pi[k - 1];
            }
            if (s.charAt(i) == s.charAt(k)) {
                k++;
            }
            pi[i] = k;
        }
        return pi;
    }

    /** Every start index of {@code pattern} in {@code text}, ascending, overlaps allowed. */
    public static int[] occurrences(String text, String pattern) {
        if (pattern.isEmpty()) {
            throw new IllegalArgumentException("pattern must not be empty");
        }
        int[] pi = prefixFunction(pattern);
        int m = pattern.length();
        int[] out = new int[Math.max(0, text.length() - m + 1)];
        int found = 0;
        int k = 0;
        for (int i = 0; i < text.length(); i++) {
            while (k > 0 && text.charAt(i) != pattern.charAt(k)) {
                k = pi[k - 1];
            }
            if (text.charAt(i) == pattern.charAt(k)) {
                k++;
            }
            if (k == m) {
                out[found++] = i - m + 1;
                k = pi[k - 1];
            }
        }
        return Arrays.copyOf(out, found);
    }

    /** Length of the shortest motif whose whole repeats build {@code s}; 0 for an empty string. */
    public static int period(String s) {
        int n = s.length();
        if (n == 0) {
            return 0;
        }
        int p = n - prefixFunction(s)[n - 1];
        return n % p == 0 ? p : n;
    }

    /** IN_TUNE only if the guess lists exactly the occurrences. */
    public static Grade grade(String text, String pattern, int[] guess) {
        return Arrays.equals(occurrences(text, pattern), guess) ? Grade.IN_TUNE : Grade.OFF;
    }

    /** The Forgemaster's line for a guess. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case IN_TUNE -> "Forgemaster: every refrain marked, not one false wheeze. The bellows sing for you.";
            case OFF -> "Forgemaster: you missed a refrain or heard one that was not there. Listen again.";
        };
    }
}
