// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

/**
 * G331 The Paired Pennants: the signal line flies two pennants of each number 1..n, and the
 * two pennants numbered k must have exactly k pennants between them (a Langford pairing).
 * A line exists only when n mod 4 is 0 or 3. A backtracking rigger places the largest pairs
 * first to build one line or count them all (mirror images counted separately).
 */
public final class PairedPennants {

    public static final String QUEST_ID = "q_paired_pennants";

    private PairedPennants() { }

    public static boolean exists(int n) {
        if (n < 1) {
            throw new IllegalArgumentException("n " + n);
        }
        return n % 4 == 0 || n % 4 == 3;
    }

    private static void checkN(int n) {
        if (n < 1 || n > 16) {
            throw new IllegalArgumentException("n must be 1..16: " + n);
        }
    }

    private static long place(int[] line, int k, boolean stopAtFirst) {
        if (k == 0) {
            return 1;
        }
        long total = 0;
        for (int i = 0; i + k + 1 < line.length; i++) {
            int j = i + k + 1;
            if (line[i] == 0 && line[j] == 0) {
                line[i] = k;
                line[j] = k;
                total += place(line, k - 1, stopAtFirst);
                if (stopAtFirst && total > 0) {
                    return total;
                }
                line[i] = 0;
                line[j] = 0;
            }
        }
        return total;
    }

    /** One valid line of length 2n, or an empty array when none exists. */
    public static int[] build(int n) {
        checkN(n);
        if (!exists(n)) {
            return new int[0];
        }
        int[] line = new int[2 * n];
        place(line, n, true);
        return line;
    }

    /** Number of valid lines of length 2n (mirror images counted separately). */
    public static long count(int n) {
        checkN(n);
        return exists(n) ? place(new int[2 * n], n, false) : 0;
    }

    /** True when the line is a valid Langford pairing. */
    public static boolean isValid(int[] line) {
        if (line.length == 0 || line.length % 2 != 0) {
            return false;
        }
        int n = line.length / 2;
        int[] first = new int[n + 1];
        int[] seen = new int[n + 1];
        for (int i = 0; i < line.length; i++) {
            int v = line[i];
            if (v < 1 || v > n) {
                return false;
            }
            seen[v]++;
            if (seen[v] == 1) {
                first[v] = i;
            } else if (seen[v] > 2 || i - first[v] != v + 1) {
                return false;
            }
        }
        return true;
    }

    /** Quest q_paired_pennants: fly a valid line. */
    public static boolean quest(int[] answer) {
        return isValid(answer);
    }
}