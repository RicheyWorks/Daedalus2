// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.SplittableRandom;

/**
 * Ring Engraving (contest gap G292): the jeweller engraves a rune band around a ring. A ring has no start, so two bands
 * match if one is a rotation of the other. Find the canonical start and tell whether two rings carry the same band.
 *
 * <p>The tool is plain: {@link #leastRotation} is the O(n) two-pointer search for the lexicographically least rotation
 * of a {@code String}, {@link #sameRing} compares canonical forms, and {@link #zArray} is the O(n) Z-function. Any
 * project can use it for cyclic string canonicalisation and prefix matching.
 */
public final class RingEngraving {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_ring_engraving";

    /** Runes the jeweller can cut. */
    public static final String RUNES = "fuxa";

    /** How a reading went. */
    public enum Grade { MATCHED, MISREAD }

    private RingEngraving() {
    }

    /** A seeded band of {@code n} runes from the first {@code k} of {@link #RUNES}. Same seed, same band. */
    public static String band(long seed, int n, int k) {
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

    /** Start index of the lexicographically least rotation (smallest such index); 0 for an empty band. */
    public static int leastRotation(String s) {
        int n = s.length();
        int i = 0;
        int j = 1;
        int k = 0;
        while (i < n && j < n && k < n) {
            char a = s.charAt((i + k) % n);
            char b = s.charAt((j + k) % n);
            if (a == b) {
                k++;
                continue;
            }
            if (a > b) {
                i += k + 1;
            } else {
                j += k + 1;
            }
            if (i == j) {
                j++;
            }
            k = 0;
        }
        return n == 0 ? 0 : Math.min(i, j);
    }

    /** The band read from its canonical start. */
    public static String canonical(String s) {
        int r = leastRotation(s);
        return s.substring(r) + s.substring(0, r);
    }

    /** True if one band is a rotation of the other. */
    public static boolean sameRing(String a, String b) {
        return a.length() == b.length() && canonical(a).equals(canonical(b));
    }

    /** z[i] = length of the longest common prefix of s and s[i..]; z[0] = n. */
    public static int[] zArray(String s) {
        int n = s.length();
        int[] z = new int[n];
        if (n == 0) {
            return z;
        }
        z[0] = n;
        int l = 0;
        int r = 0;
        for (int i = 1; i < n; i++) {
            int v = i < r ? Math.min(r - i, z[i - l]) : 0;
            while (i + v < n && s.charAt(v) == s.charAt(i + v)) {
                v++;
            }
            z[i] = v;
            if (i + v > r) {
                l = i;
                r = i + v;
            }
        }
        return z;
    }

    /** MATCHED only if the claimed canonical start and the same-ring call are both right. */
    public static Grade grade(String a, String b, int start, boolean same) {
        return start == leastRotation(a) && same == sameRing(a, b) ? Grade.MATCHED : Grade.MISREAD;
    }

    /** The Forgemaster's line for a reading. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case MATCHED -> "Forgemaster: you found where the band begins and knew its twin. A jeweller's eye.";
            case MISREAD -> "Forgemaster: turn the ring again. The runes are not where you think.";
        };
    }
}
