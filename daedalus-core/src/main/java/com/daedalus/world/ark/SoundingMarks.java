// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

/**
 * G336 The Sounding Marks: the leadsman ties k knots on the sounding line so that every pair of
 * knots measures a different depth (a Golomb ruler). A checker validates a line, and a
 * backtracking search finds the shortest line for up to 8 knots, trying lengths in order.
 */
public final class SoundingMarks {

    public static final String QUEST_ID = "q_sounding_marks";

    private SoundingMarks() { }

    /** True when the marks start at 0, strictly rise, and all pair distances differ. */
    public static boolean isGolomb(int[] marks) {
        if (marks.length == 0 || marks[0] != 0) {
            return false;
        }
        for (int i = 1; i < marks.length; i++) {
            if (marks[i] <= marks[i - 1]) {
                return false;
            }
        }
        int top = marks[marks.length - 1];
        boolean[] seen = new boolean[top + 1];
        for (int i = 0; i < marks.length; i++) {
            for (int j = i + 1; j < marks.length; j++) {
                int dist = marks[j] - marks[i];
                if (seen[dist]) {
                    return false;
                }
                seen[dist] = true;
            }
        }
        return true;
    }

    /** A shortest Golomb ruler with k marks (1 &lt;= k &lt;= 8). */
    public static int[] shortest(int k) {
        if (k < 1 || k > 8) {
            throw new IllegalArgumentException("knots must be 1..8: " + k);
        }
        if (k == 1) {
            return new int[] {0};
        }
        for (int len = k - 1;; len++) {
            int[] marks = new int[k];
            marks[k - 1] = len;
            boolean[] used = new boolean[len + 1];
            used[len] = true;
            if (place(marks, 1, k, len, used)) {
                return marks;
            }
        }
    }

    private static boolean place(int[] marks, int idx, int k, int len, boolean[] used) {
        if (idx == k - 1) {
            return true;
        }
        int remaining = k - 1 - idx;
        for (int p = marks[idx - 1] + 1; p <= len - remaining; p++) {
            if (fits(marks, idx, p, k, len, used, true)) {
                marks[idx] = p;
                if (place(marks, idx + 1, k, len, used)) {
                    return true;
                }
                fits(marks, idx, p, k, len, used, false);
            }
        }
        return false;
    }

    private static boolean fits(int[] marks, int idx, int p, int k, int len, boolean[] used, boolean add) {
        if (!add) {
            for (int i = 0; i < idx; i++) {
                used[p - marks[i]] = false;
            }
            used[len - p] = false;
            return true;
        }
        int n = 0;
        int[] got = new int[idx + 1];
        for (int i = 0; i < idx; i++) {
            got[n++] = p - marks[i];
        }
        got[n++] = len - p;
        for (int a = 0; a < n; a++) {
            if (used[got[a]]) {
                return false;
            }
            for (int b = a + 1; b < n; b++) {
                if (got[a] == got[b]) {
                    return false;
                }
            }
        }
        for (int a = 0; a < n; a++) {
            used[got[a]] = true;
        }
        return true;
    }

    /** Quest q_sounding_marks: tie k knots as a valid line no longer than the shortest. */
    public static boolean quest(int k, int[] answer) {
        int[] best = shortest(k);
        return answer.length == k && isGolomb(answer) && answer[k - 1] == best[k - 1];
    }
}