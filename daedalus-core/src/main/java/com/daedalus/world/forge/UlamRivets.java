// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.Arrays;

/**
 * Ulam Rivets: rivets are set by Ulam's rule. Start with 1 and 2; each next rivet is the smallest number
 * greater than the last that is the sum of two distinct earlier rivets in exactly one way.
 *
 * <p>Reusable plain int API: {@link #upTo}, {@link #nth}, {@link #isUlam}, {@link #countBelow}.
 */
public final class UlamRivets {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_ulam_rivets";

    /** Largest supported bound. */
    public static final int MAX_LIMIT = 200_000;

    /** Grade band. */
    public enum Grade { TRUE, LOOSE }

    private UlamRivets() {
    }

    /** All Ulam numbers at most limit, ascending. */
    public static int[] upTo(int limit) {
        if (limit < 0 || limit > MAX_LIMIT) {
            throw new IllegalArgumentException("limit out of range: " + limit);
        }
        if (limit < 1) {
            return new int[0];
        }
        if (limit < 2) {
            return new int[] {1};
        }
        byte[] cnt = new byte[limit + 1];
        int[] seq = new int[Math.max(16, limit / 4)];
        seq[0] = 1;
        seq[1] = 2;
        int k = 2;
        if (3 <= limit) {
            cnt[3] = 1;
        }
        for (int c = 3; c <= limit; c++) {
            if (cnt[c] != 1) {
                continue;
            }
            for (int i = 0; i < k; i++) {
                int s = c + seq[i];
                if (s > limit) {
                    break;
                }
                if (cnt[s] < 2) {
                    cnt[s]++;
                }
            }
            if (k == seq.length) {
                seq = Arrays.copyOf(seq, 2 * k);
            }
            seq[k++] = c;
        }
        return Arrays.copyOf(seq, k);
    }

    /** The n-th Ulam number (1-based). */
    public static int nth(int n) {
        if (n < 1) {
            throw new IllegalArgumentException("n must be positive");
        }
        int limit = 64;
        while (true) {
            int[] s = upTo(limit);
            if (s.length >= n) {
                return s[n - 1];
            }
            if (limit == MAX_LIMIT) {
                throw new IllegalArgumentException("n too large: " + n);
            }
            limit = Math.min(MAX_LIMIT, limit * 2);
        }
    }

    /** True when x is an Ulam number. */
    public static boolean isUlam(int x) {
        return x >= 1 && Arrays.binarySearch(upTo(x), x) >= 0;
    }

    /** Number of Ulam numbers below x. */
    public static int countBelow(int x) {
        return x <= 1 ? 0 : upTo(x - 1).length;
    }

    /** TRUE when the claimed n-th rivet is right. */
    public static Grade grade(int n, int claimed) {
        return nth(n) == claimed ? Grade.TRUE : Grade.LOOSE;
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case TRUE -> "Forgemaster: one way and one way only, every rivet set where the rule demands. Tight.";
            case LOOSE -> "Forgemaster: that rivet is loose. Count the pairs again; exactly one, no more.";
        };
    }
}
