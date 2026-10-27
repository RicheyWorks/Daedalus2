// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.ArrayList;
import java.util.List;

/**
 * G438 The Lucky Berths: the purser numbers berths 1, 2, 3, ... and strikes them off by Ulam's
 * lucky sieve. First every second berth goes, leaving the odd ones; then, for each surviving
 * number L after 1 in turn, every L-th berth still standing goes. The survivors are the lucky
 * numbers. Uses a Fenwick tree so each strike finds the k-th survivor in O(log n).
 */
public final class LuckyBerths {

    public static final String QUEST_ID = "q_lucky_berths";
    public static final int MAX_N = 2_000_000;

    private LuckyBerths() { }

    /** Every lucky number up to and including n (1 &lt;= n &lt;= 2000000), ascending. */
    public static int[] upTo(int n) {
        if (n < 1 || n > MAX_N) {
            throw new IllegalArgumentException("n out of range: " + n);
        }
        int m = (n + 1) / 2;
        int[] tree = new int[m + 1];
        for (int i = 1; i <= m; i++) {
            tree[i]++;
            int j = i + (i & -i);
            if (j <= m) {
                tree[j] += tree[i];
            }
        }
        int left = m;
        int log = Integer.highestOneBit(Math.max(1, m));
        for (int pos = 2; pos <= left; pos++) {
            int l = 2 * kth(tree, m, log, pos) - 1;
            if (l > left) {
                break;
            }
            for (int j = left / l * l; j >= l; j -= l) {
                int at = kth(tree, m, log, j);
                for (int x = at; x <= m; x += x & -x) {
                    tree[x]--;
                }
                left--;
            }
        }
        int[] out = new int[left];
        for (int k = 1; k <= left; k++) {
            out[k - 1] = 2 * kth(tree, m, log, k) - 1;
        }
        return out;
    }

    private static int kth(int[] tree, int m, int log, int k) {
        int pos = 0;
        int rem = k;
        for (int step = log; step > 0; step >>= 1) {
            int nx = pos + step;
            if (nx <= m && tree[nx] < rem) {
                pos = nx;
                rem -= tree[nx];
            }
        }
        return pos + 1;
    }

    /** True when x is lucky. */
    public static boolean isLucky(int x) {
        if (x < 1 || x > MAX_N) {
            throw new IllegalArgumentException("x out of range: " + x);
        }
        int[] l = upTo(x);
        return l[l.length - 1] == x;
    }

    /** Lucky numbers below n. */
    public static int countBelow(int n) {
        if (n <= 1) {
            return 0;
        }
        return upTo(n - 1).length;
    }

    private static boolean prime(int x) {
        if (x < 2) {
            return false;
        }
        for (int d = 2; (long) d * d <= x; d++) {
            if (x % d == 0) {
                return false;
            }
        }
        return true;
    }

    /** Lucky numbers up to n that are also prime. */
    public static List<Integer> luckyPrimes(int n) {
        List<Integer> out = new ArrayList<>();
        for (int v : upTo(n)) {
            if (prime(v)) {
                out.add(v);
            }
        }
        return List.copyOf(out);
    }

    /** Pairs of lucky numbers up to n that differ by 2, as their smaller member. */
    public static List<Integer> twins(int n) {
        int[] l = upTo(n);
        List<Integer> out = new ArrayList<>();
        for (int i = 1; i < l.length; i++) {
            if (l[i] - l[i - 1] == 2) {
                out.add(l[i - 1]);
            }
        }
        return List.copyOf(out);
    }

    /** Quest q_lucky_berths: the purser names how many lucky berths lie below n. */
    public static boolean quest(int n, int answer) {
        return countBelow(n) == answer;
    }
}