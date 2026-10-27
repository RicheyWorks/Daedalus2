// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

/**
 * Verhoeff Seal: blade serials are sealed with a Verhoeff check digit. The multiplication table is the dihedral
 * group D5 (0-4 rotations, 5-9 reflections), built here from the group rules; the position permutation is
 * powers of (1 5 7 6 2 8 3 0 9 4). Catches every single-digit error and every adjacent transposition.
 *
 * <p>Reusable plain String API: {@link #checkDigit}, {@link #seal}, {@link #isValid}.
 */
public final class VerhoeffSeal {

    /** Quest id for the Hephaestus Island forge hook. */
    public static final String QUEST_ID = "q_verhoeff_seal";

    private static final int[][] D = new int[10][10];
    private static final int[][] P = new int[8][10];
    private static final int[] INV = new int[10];

    static {
        for (int j = 0; j < 10; j++) {
            for (int k = 0; k < 10; k++) {
                int a = j % 5;
                int b = k % 5;
                if (j < 5) {
                    D[j][k] = k < 5 ? (a + b) % 5 : 5 + (a + b) % 5;
                } else {
                    D[j][k] = k < 5 ? 5 + Math.floorMod(a - b, 5) : Math.floorMod(a - b, 5);
                }
            }
        }
        int[] base = {1, 5, 7, 6, 2, 8, 3, 0, 9, 4};
        for (int k = 0; k < 10; k++) {
            P[0][k] = k;
        }
        for (int i = 1; i < 8; i++) {
            for (int k = 0; k < 10; k++) {
                P[i][k] = base[P[i - 1][k]];
            }
        }
        for (int j = 0; j < 10; j++) {
            for (int k = 0; k < 10; k++) {
                if (D[j][k] == 0) {
                    INV[j] = k;
                }
            }
        }
    }

    /** Grade band. */
    public enum Grade { SEALED, TAMPERED }

    private VerhoeffSeal() {
    }

    /** D5 product j*k. */
    public static int multiply(int j, int k) {
        return D[j][k];
    }

    /** Position permutation entry p(i mod 8, k). */
    public static int permute(int i, int k) {
        return P[Math.floorMod(i, 8)][k];
    }

    /** Inverse of j in D5. */
    public static int inverse(int j) {
        return INV[j];
    }

    /** Check digit for a digit string. */
    public static int checkDigit(String digits) {
        return INV[fold(digits, 1)];
    }

    /** Digits followed by their check digit. */
    public static String seal(String digits) {
        return digits + checkDigit(digits);
    }

    /** True when the last digit is a correct Verhoeff check digit. */
    public static boolean isValid(String sealed) {
        return !sealed.isEmpty() && fold(sealed, 0) == 0;
    }

    /** SEALED when the serial validates. */
    public static Grade grade(String sealed) {
        return isValid(sealed) ? Grade.SEALED : Grade.TAMPERED;
    }

    /** Forgemaster line for a grade. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case SEALED -> "Forgemaster: the seal holds. Every digit stands where it was stamped.";
            case TAMPERED -> "Forgemaster: tampered. A digit was struck wrong or two were swapped.";
        };
    }

    private static int fold(String s, int shift) {
        int c = 0;
        int n = s.length();
        for (int i = 0; i < n; i++) {
            int d = s.charAt(n - 1 - i) - '0';
            if (d < 0 || d > 9) {
                throw new IllegalArgumentException("not a digit at " + (n - 1 - i));
            }
            c = D[c][P[(i + shift) % 8][d]];
        }
        return c;
    }
}
