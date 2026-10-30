// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

/**
 * Harshad Hammers: a hammer stamped n strikes clean when n is divisible by the sum of its digits (a Harshad or Niven
 * number). The smith checks single hammers in any base and counts clean hammers in a rack 1..N without striking
 * each one, by a digit-sum / remainder table over every possible digit sum.
 *
 * <p>Reusable plain long API: {@link #digitSum}, {@link #isHarshad} (bases 2..36) and {@link #countHarshad} (base 10,
 * N up to {@link #MAX_N}).
 */
public final class HarshadHammers {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_harshad_hammers";
    /** Largest supported rack for counting. */
    public static final long MAX_N = 1_000_000_000_000L;

    /** Grade band. */
    public enum Grade { TURNED, SLIPPED }

    private HarshadHammers() {
    }

    /** Sum of the base-b digits of n &gt;= 0. */
    public static long digitSum(long n, int base) {
        if (n < 0 || base < 2 || base > 36) {
            throw new IllegalArgumentException("bad digit-sum query");
        }
        long s = 0;
        long m = n;
        while (m > 0) {
            s += m % base;
            m /= base;
        }
        return s;
    }

    /** True when n &gt;= 1 is divisible by its base-b digit sum. */
    public static boolean isHarshad(long n, int base) {
        return n >= 1 && n % digitSum(n, base) == 0;
    }

    private static long countForSum(int[] digits, int s) {
        int len = digits.length;
        long[][][] ways = new long[len + 1][s + 1][s];
        ways[0][0][0] = 1;
        long pow = 1 % s;
        for (int l = 0; l < len; l++) {
            for (int sum = 0; sum <= s; sum++) {
                for (int r = 0; r < s; r++) {
                    long w = ways[l][sum][r];
                    if (w == 0) {
                        continue;
                    }
                    for (int d = 0; d <= 9 && sum + d <= s; d++) {
                        ways[l + 1][sum + d][(int) ((d * pow + r) % s)] += w;
                    }
                }
            }
            pow = pow * 10 % s;
        }
        long[] pw = new long[len + 1];
        pw[0] = 1 % s;
        for (int i = 1; i <= len; i++) {
            pw[i] = pw[i - 1] * 10 % s;
        }
        long total = 0;
        long pref = 0;
        int prefSum = 0;
        for (int i = 0; i < len; i++) {
            int rest = len - 1 - i;
            for (int d = 0; d < digits[i]; d++) {
                int need = s - prefSum - d;
                if (need < 0) {
                    break;
                }
                long head = ((pref * 10 + d) % s) * pw[rest] % s;
                int r = (int) ((s - head) % s);
                total += ways[rest][need][r];
            }
            pref = (pref * 10 + digits[i]) % s;
            prefSum += digits[i];
            if (prefSum > s) {
                return total;
            }
        }
        if (prefSum == s && pref == 0) {
            total++;
        }
        return total;
    }

    /** Number of base-10 Harshad numbers in 1..N. */
    public static long countHarshad(long bigN) {
        if (bigN < 0 || bigN > MAX_N) {
            throw new IllegalArgumentException("rack out of range: " + bigN);
        }
        if (bigN == 0) {
            return 0;
        }
        String t = Long.toString(bigN);
        int[] digits = new int[t.length()];
        for (int i = 0; i < digits.length; i++) {
            digits[i] = t.charAt(i) - '0';
        }
        long total = 0;
        for (int s = 1; s <= 9 * digits.length; s++) {
            total += countForSum(digits, s);
        }
        return total;
    }

    /** Grade a claimed count of Harshad numbers in 1..N. */
    public static Grade grade(long bigN, long claimed) {
        return countHarshad(bigN) == claimed ? Grade.TURNED : Grade.SLIPPED;
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case TURNED -> "Forgemaster: every clean hammer counted, none struck. The rack is true.";
            case SLIPPED -> "Forgemaster: the count slipped. Fix the digit sum first, then track the remainder.";
        };
    }
}
