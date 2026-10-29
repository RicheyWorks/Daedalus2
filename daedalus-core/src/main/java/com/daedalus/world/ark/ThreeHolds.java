// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

/**
 * G327 The Three Holds: crates tagged 0 (fore), 1 (mid) and 2 (aft) sit in one row. The
 * stevedore sorts them in a single pass with the Dutch national flag partition, and the
 * quartermaster can price the job as the fewest crate swaps that sort the row: swap every
 * crossed pair directly, then each leftover three-way cycle costs two swaps.
 */
public final class ThreeHolds {

    public static final String QUEST_ID = "q_three_holds";

    private ThreeHolds() { }

    private static void checkTags(int[] row) {
        for (int v : row) {
            if (v < 0 || v > 2) {
                throw new IllegalArgumentException("hold tag must be 0, 1 or 2: " + v);
            }
        }
    }

    /** One-pass Dutch flag partition of a copy; returns the sorted row. */
    public static int[] partition(int[] row) {
        checkTags(row);
        int[] a = row.clone();
        int lo = 0;
        int mid = 0;
        int hi = a.length - 1;
        while (mid <= hi) {
            if (a[mid] == 0) {
                int x = a[lo];
                a[lo] = a[mid];
                a[mid] = x;
                lo++;
                mid++;
            } else if (a[mid] == 1) {
                mid++;
            } else {
                int x = a[hi];
                a[hi] = a[mid];
                a[mid] = x;
                hi--;
            }
        }
        return a;
    }

    /** Fewest swaps of any two crates that sort the row. */
    public static long minSwaps(int[] row) {
        checkTags(row);
        int[] count = new int[3];
        for (int v : row) {
            count[v]++;
        }
        long[][] c = new long[3][3];
        int pos = 0;
        for (int zone = 0; zone < 3; zone++) {
            for (int k = 0; k < count[zone]; k++) {
                c[zone][row[pos++]]++;
            }
        }
        long swaps = 0;
        long left = 0;
        for (int i = 0; i < 3; i++) {
            for (int j = i + 1; j < 3; j++) {
                long p = Math.min(c[i][j], c[j][i]);
                swaps += p;
                left += c[i][j] + c[j][i] - 2 * p;
            }
        }
        return swaps + left / 3 * 2;
    }

    /** Quest q_three_holds: name the fewest swaps to stow the row. */
    public static boolean quest(int[] row, long answer) {
        return minSwaps(row) == answer;
    }
}