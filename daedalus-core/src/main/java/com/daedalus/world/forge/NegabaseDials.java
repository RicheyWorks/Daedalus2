// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.math.BigInteger;

/**
 * Negabase Dials: furnace dials read in a negative base -k (k in 2..10), so every integer has one sign-free digit
 * string. Base -2 (negabinary) dials can also be added digit by digit.
 *
 * <p>Reusable plain long/String API: {@link #toNegabase}, {@link #fromNegabase}, {@link #addNegabinary}.
 */
public final class NegabaseDials {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_negabase_dials";

    /** Grade band. */
    public enum Grade { TRUE, SKEWED }

    private NegabaseDials() {
    }

    /** Digits of n in base -k, most significant first ("0" for zero). */
    public static String toNegabase(long n, int k) {
        checkBase(k);
        if (n == 0) {
            return "0";
        }
        StringBuilder sb = new StringBuilder();
        long x = n;
        while (x != 0) {
            long r = Math.floorMod(x, (long) k);
            sb.append((char) ('0' + r));
            x = -Math.floorDiv(x, (long) k);
        }
        return sb.reverse().toString();
    }

    /** Value of a base -k digit string; throws on bad digits or overflow. */
    public static long fromNegabase(String digits, int k) {
        checkBase(k);
        if (digits.isEmpty()) {
            throw new IllegalArgumentException("empty dial");
        }
        BigInteger v = BigInteger.ZERO;
        BigInteger base = BigInteger.valueOf(-k);
        for (int i = 0; i < digits.length(); i++) {
            int d = digits.charAt(i) - '0';
            if (d < 0 || d >= k) {
                throw new IllegalArgumentException("bad digit at " + i);
            }
            v = v.multiply(base).add(BigInteger.valueOf(d));
        }
        try {
            return v.longValueExact();
        } catch (ArithmeticException e) {
            throw new IllegalArgumentException("dial overflows a long", e);
        }
    }

    /** Sum of two negabinary strings, computed digit by digit. */
    public static String addNegabinary(String a, String b) {
        StringBuilder sb = new StringBuilder();
        int i = a.length() - 1;
        int j = b.length() - 1;
        int carry = 0;
        while (i >= 0 || j >= 0 || carry != 0) {
            int s = carry + digit(a, i--) + digit(b, j--);
            int d = Math.floorMod(s, 2);
            carry = -(s - d) / 2;
            sb.append((char) ('0' + d));
        }
        while (sb.length() > 1 && sb.charAt(sb.length() - 1) == '0') {
            sb.setLength(sb.length() - 1);
        }
        return sb.length() == 0 ? "0" : sb.reverse().toString();
    }

    /** TRUE when the claimed dial reads n in base -k. */
    public static Grade grade(long n, int k, String claimed) {
        try {
            return fromNegabase(claimed, k) == n ? Grade.TRUE : Grade.SKEWED;
        } catch (IllegalArgumentException e) {
            return Grade.SKEWED;
        }
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case TRUE -> "Forgemaster: the dial reads true, no sign needed. Heat holds where you set it.";
            case SKEWED -> "Forgemaster: skewed reading. Odd places count against you; read the dial again.";
        };
    }

    private static int digit(String s, int i) {
        if (i < 0) {
            return 0;
        }
        char c = s.charAt(i);
        if (c != '0' && c != '1') {
            throw new IllegalArgumentException("bad negabinary digit");
        }
        return c - '0';
    }

    private static void checkBase(int k) {
        if (k < 2 || k > 10) {
            throw new IllegalArgumentException("k out of range: " + k);
        }
    }
}
