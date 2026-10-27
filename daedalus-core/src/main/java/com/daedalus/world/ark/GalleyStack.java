// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * G428 The Galley Stack: the cook has a stack of n plates of sizes 0..n-1 (index 0 is the top)
 * and may only slide a spatula under the top k plates and flip them over (pancake sorting). The
 * goal puts the plates in order 0, 1, ..., n-1 from the top. Gives a greedy sort in at most
 * 2n - 3 flips, the exact fewest flips by breadth-first search for up to {@link #MAX_EXACT}
 * plates and the pancake numbers (the worst stack's fewest flips).
 */
public final class GalleyStack {

    public static final String QUEST_ID = "q_galley_stack";
    public static final int MAX_PLATES = 12;
    public static final int MAX_EXACT = 8;

    private GalleyStack() { }

    private static void check(int[] s) {
        if (s == null || s.length < 1 || s.length > MAX_PLATES) {
            throw new IllegalArgumentException("stack must hold 1 to " + MAX_PLATES + " plates");
        }
        boolean[] seen = new boolean[s.length];
        for (int v : s) {
            if (v < 0 || v >= s.length || seen[v]) {
                throw new IllegalArgumentException("stack must be a permutation of 0..n-1");
            }
            seen[v] = true;
        }
    }

    /** The stack after flipping the top k plates (1 &lt;= k &lt;= n). */
    public static int[] flip(int[] s, int k) {
        check(s);
        if (k < 1 || k > s.length) {
            throw new IllegalArgumentException("flip size out of range: " + k);
        }
        int[] out = s.clone();
        for (int i = 0, j = k - 1; i < j; i++, j--) {
            int t = out[i];
            out[i] = out[j];
            out[j] = t;
        }
        return out;
    }

    /** True when the plates run 0, 1, ..., n-1 from the top. */
    public static boolean sorted(int[] s) {
        check(s);
        for (int i = 0; i < s.length; i++) {
            if (s[i] != i) {
                return false;
            }
        }
        return true;
    }

    /** Greedy flips: bring the largest unsorted plate to the top, then flip it down. */
    public static int[] greedy(int[] start) {
        check(start);
        int[] s = start.clone();
        List<Integer> out = new ArrayList<>();
        for (int size = s.length; size > 1; size--) {
            int at = 0;
            while (s[at] != size - 1) {
                at++;
            }
            if (at == size - 1) {
                continue;
            }
            if (at > 0) {
                s = flip(s, at + 1);
                out.add(at + 1);
            }
            s = flip(s, size);
            out.add(size);
        }
        return out.stream().mapToInt(Integer::intValue).toArray();
    }

    private static long key(int[] s) {
        long k = 0;
        for (int v : s) {
            k = k << 4 | v;
        }
        return k;
    }

    /** One shortest list of flip sizes (empty when already sorted). */
    public static int[] fewest(int[] start) {
        check(start);
        if (start.length > MAX_EXACT) {
            throw new IllegalArgumentException("exact search limited to " + MAX_EXACT + " plates");
        }
        Map<Long, long[]> prev = new HashMap<>();
        ArrayDeque<int[]> q = new ArrayDeque<>();
        prev.put(key(start), new long[] {-1, 0});
        q.add(start.clone());
        long goal = -1;
        while (!q.isEmpty()) {
            int[] cur = q.poll();
            long ck = key(cur);
            if (sorted(cur)) {
                goal = ck;
                break;
            }
            for (int k = 2; k <= cur.length; k++) {
                int[] nx = flip(cur, k);
                long nk = key(nx);
                if (!prev.containsKey(nk)) {
                    prev.put(nk, new long[] {ck, k});
                    q.add(nx);
                }
            }
        }
        ArrayDeque<Integer> out = new ArrayDeque<>();
        for (long k = goal; prev.get(k)[0] >= 0; k = prev.get(k)[0]) {
            out.push((int) prev.get(k)[1]);
        }
        return out.stream().mapToInt(Integer::intValue).toArray();
    }

    /** Pancake number: the most flips any stack of n plates needs (n = 1 to 8). */
    public static int pancakeNumber(int n) {
        if (n < 1 || n > MAX_EXACT) {
            throw new IllegalArgumentException("n out of range: " + n);
        }
        int[] id = new int[n];
        for (int i = 0; i < n; i++) {
            id[i] = i;
        }
        Map<Long, Integer> dist = new HashMap<>();
        ArrayDeque<int[]> q = new ArrayDeque<>();
        dist.put(key(id), 0);
        q.add(id);
        int far = 0;
        while (!q.isEmpty()) {
            int[] cur = q.poll();
            int dc = dist.get(key(cur));
            far = Math.max(far, dc);
            for (int k = 2; k <= n; k++) {
                int[] nx = flip(cur, k);
                if (dist.putIfAbsent(key(nx), dc + 1) == null) {
                    q.add(nx);
                }
            }
        }
        return far;
    }

    /** Quest q_galley_stack: the cook names the fewest flips for this stack. */
    public static boolean quest(int[] stack, int answer) {
        return fewest(stack).length == answer;
    }
}