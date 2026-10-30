// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

/**
 * G349 The Flag Runs: the signal mate hangs a row of red and blue flags, and the line is safe when
 * no k evenly spaced flags share a colour (no monochrome arithmetic progression of length k). A
 * backtracking finder colours flags left to right, checking only progressions that end at the new
 * flag; the first unsafe length is the van der Waerden number W(2, k).
 */
public final class FlagRuns {

    public static final String QUEST_ID = "q_flag_runs";

    private FlagRuns() { }

    /** True when colours are 0/1 and no k evenly spaced flags share a colour (k &gt;= 2). */
    public static boolean isSafe(int[] line, int k) {
        if (k < 2) {
            throw new IllegalArgumentException("k >= 2");
        }
        for (int c : line) {
            if (c != 0 && c != 1) {
                return false;
            }
        }
        for (int i = 0; i < line.length; i++) {
            if (endsRun(line, i, k)) {
                return false;
            }
        }
        return true;
    }

    private static boolean endsRun(int[] line, int i, int k) {
        for (int step = 1; step * (k - 1) <= i; step++) {
            boolean same = true;
            for (int j = 1; same && j < k; j++) {
                same = line[i - j * step] == line[i];
            }
            if (same) {
                return true;
            }
        }
        return false;
    }

    /** A safe line of length n for run length k (k 2..4), or an empty array when none exists. */
    public static int[] find(int n, int k) {
        if (k < 2 || k > 4 || n < 0 || n > 40) {
            throw new IllegalArgumentException("k 2..4 and n 0..40");
        }
        int[] line = new int[n];
        return n == 0 || place(line, 1, k) ? line : new int[0];
    }

    private static boolean place(int[] line, int i, int k) {
        if (i == line.length) {
            return true;
        }
        for (int c = 0; c < 2; c++) {
            line[i] = c;
            if (!endsRun(line, i, k) && place(line, i + 1, k)) {
                return true;
            }
        }
        return false;
    }

    /** Van der Waerden number W(2, k): the first length with no safe line (k 2..4). */
    public static int waerden(int k) {
        int n = 1;
        while (find(n, k).length == n) {
            n++;
        }
        return n;
    }

    /** Quest q_flag_runs: hang a safe line of n flags for run length k. */
    public static boolean quest(int n, int k, int[] answer) {
        return answer.length == n && isSafe(answer, k);
    }
}