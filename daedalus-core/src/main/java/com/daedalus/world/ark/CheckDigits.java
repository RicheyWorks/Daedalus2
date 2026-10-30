// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

/**
 * G317 The Check Digits: the purser stamps each manifest number with a check character so a
 * clerk's slip is caught. Luhn (mod 10, doubling every second digit from the right) catches every
 * single-digit slip and every neighbour swap except 09/90; weighted mod 11 (weights 2, 3, 4, ...
 * from the right, check 'X' for ten, payload up to 9 digits) catches every single slip and every neighbour swap.
 */
public final class CheckDigits {

    public static final String QUEST_ID = "q_check_digits";

    private CheckDigits() { }

    private static void digitsOnly(String s) {
        if (s.isEmpty()) {
            throw new IllegalArgumentException("empty number");
        }
        for (int i = 0; i < s.length(); i++) {
            if (s.charAt(i) < '0' || s.charAt(i) > '9') {
                throw new IllegalArgumentException("not a digit at " + i);
            }
        }
    }

    private static int luhnSum(String s, boolean doubleLast) {
        int sum = 0;
        boolean dbl = doubleLast;
        for (int i = s.length() - 1; i >= 0; i--) {
            int d = s.charAt(i) - '0';
            if (dbl) {
                d *= 2;
                if (d > 9) {
                    d -= 9;
                }
            }
            sum += d;
            dbl = !dbl;
        }
        return sum;
    }

    /** Luhn check digit for a payload of digits. */
    public static char luhnDigit(String payload) {
        digitsOnly(payload);
        return (char) ('0' + (10 - luhnSum(payload, true) % 10) % 10);
    }

    public static boolean luhnValid(String full) {
        digitsOnly(full);
        return full.length() >= 2 && luhnSum(full, false) % 10 == 0;
    }

    private static int mod11Sum(String payload) {
        if (payload.length() > 9) {
            throw new IllegalArgumentException("mod 11 payload is at most 9 digits");
        }
        int sum = 0;
        for (int i = 0; i < payload.length(); i++) {
            int w = payload.length() - i + 1;
            sum += w * (payload.charAt(i) - '0');
        }
        return sum;
    }

    /** Weighted mod 11 check character ('0'..'9' or 'X'). */
    public static char mod11Digit(String payload) {
        digitsOnly(payload);
        int c = (11 - mod11Sum(payload) % 11) % 11;
        return c == 10 ? 'X' : (char) ('0' + c);
    }

    public static boolean mod11Valid(String full) {
        if (full.length() < 2) {
            return false;
        }
        String payload = full.substring(0, full.length() - 1);
        digitsOnly(payload);
        return mod11Digit(payload) == full.charAt(full.length() - 1);
    }

    /** Quest q_check_digits: stamp the right Luhn check digit on the manifest number. */
    public static boolean quest(String payload, char answer) {
        return luhnDigit(payload) == answer;
    }
}