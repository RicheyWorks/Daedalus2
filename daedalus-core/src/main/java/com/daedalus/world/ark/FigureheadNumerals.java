// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.OptionalInt;

/**
 * G325 The Figurehead Numerals: the carver cuts the ark's tally in Roman numerals on the
 * figurehead. Carving is greedy over the subtractive pairs; reading is strict, accepting only
 * the one canonical carving of each number from 1 to 3999 (so IIII, VX and IC are refused).
 */
public final class FigureheadNumerals {

    public static final String QUEST_ID = "q_figurehead_numerals";

    private static final int[] VALUES = {1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1};
    private static final String[] MARKS = {"M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I"};

    private FigureheadNumerals() { }

    public static String carve(int n) {
        if (n < 1 || n > 3999) {
            throw new IllegalArgumentException("only 1..3999 can be carved: " + n);
        }
        StringBuilder sb = new StringBuilder();
        int left = n;
        for (int i = 0; i < VALUES.length; i++) {
            while (left >= VALUES[i]) {
                sb.append(MARKS[i]);
                left -= VALUES[i];
            }
        }
        return sb.toString();
    }

    private static final String LETTERS = "IVXLCDM";
    private static final int[] LETTER_VALUES = {1, 5, 10, 50, 100, 500, 1000};

    private static int mark(char c) {
        int i = LETTERS.indexOf(c);
        return i < 0 ? 0 : LETTER_VALUES[i];
    }

    /** Read a carving; empty unless it is the canonical numeral of some 1..3999. */
    public static OptionalInt read(String s) {
        if (s.isEmpty() || s.length() > 15) {
            return OptionalInt.empty();
        }
        int total = 0;
        for (int i = 0; i < s.length(); i++) {
            int v = mark(s.charAt(i));
            if (v == 0) {
                return OptionalInt.empty();
            }
            int next = i + 1 < s.length() ? mark(s.charAt(i + 1)) : 0;
            total += v < next ? -v : v;
        }
        if (total < 1 || total > 3999 || !carve(total).equals(s)) {
            return OptionalInt.empty();
        }
        return OptionalInt.of(total);
    }

    /** Quest q_figurehead_numerals: carve the tally correctly. */
    public static boolean quest(int tally, String answer) {
        return carve(tally).equals(answer);
    }
}