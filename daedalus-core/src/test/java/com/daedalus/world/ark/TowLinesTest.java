// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class TowLinesTest {

    /** Brute force: plain adjacency lists, path found by breadth-first search. */
    private static final class Fleet {
        final List<List<Integer>> adj = new ArrayList<>();
        final long[] load;

        Fleet(long[] loads) {
            load = loads.clone();
            for (int i = 0; i < loads.length; i++) {
                adj.add(new ArrayList<>());
            }
        }

        int[] path(int a, int b) {
            int[] from = new int[load.length];
            Arrays.fill(from, -2);
            from[a] = -1;
            ArrayDeque<Integer> q = new ArrayDeque<>();
            q.add(a);
            while (!q.isEmpty()) {
                int x = q.poll();
                for (int y : adj.get(x)) {
                    if (from[y] == -2) {
                        from[y] = x;
                        q.add(y);
                    }
                }
            }
            if (from[b] == -2) {
                return new int[0];
            }
            List<Integer> p = new ArrayList<>();
            for (int x = b; x != -1; x = from[x]) {
                p.add(x);
            }
            return p.stream().mapToInt(Integer::intValue).toArray();
        }
    }

    @Test
    void smallFleetByHand() {
        TowLines t = new TowLines(new long[] {5, 1, 9, 3, 7});
        assertTrue(t.link(0, 1));
        assertTrue(t.link(1, 2));
        assertTrue(t.link(1, 3));
        assertFalse(t.link(0, 3));
        assertEquals(9, t.pathMax(0, 2));
        assertEquals(15, t.pathSum(0, 2));
        assertEquals(9, t.pathSum(3, 0));
        assertFalse(t.joined(0, 4));
        assertFalse(t.cut(0, 2));
        assertTrue(t.cut(1, 2));
        assertFalse(t.joined(0, 2));
        assertTrue(t.link(4, 2));
        assertTrue(t.link(3, 4));
        assertEquals(1 + 3 + 7 + 9, t.pathSum(1, 2));
        t.setLoad(4, 20);
        assertEquals(20, t.pathMax(0, 2));
        assertEquals(20, t.load(4));
    }

    @Test
    void randomOperationsMatchBruteForce() {
        for (long seed = 1; seed <= 40; seed++) {
            SplittableRandom rnd = new SplittableRandom(seed);
            int n = 2 + rnd.nextInt(30);
            long[] loads = new long[n];
            for (int i = 0; i < n; i++) {
                loads[i] = rnd.nextLong(-50, 100);
            }
            TowLines t = new TowLines(loads);
            Fleet f = new Fleet(loads);
            for (int op = 0; op < 1500; op++) {
                int a = rnd.nextInt(n);
                int b = rnd.nextInt(n);
                int[] p = f.path(a, b);
                switch (rnd.nextInt(4)) {
                    case 0 -> {
                        boolean ok = p.length == 0;
                        assertEquals(ok, t.link(a, b));
                        if (ok) {
                            f.adj.get(a).add(b);
                            f.adj.get(b).add(a);
                        }
                    }
                    case 1 -> {
                        boolean ok = a != b && f.adj.get(a).contains(b);
                        assertEquals(ok, t.cut(a, b));
                        if (ok) {
                            f.adj.get(a).remove(Integer.valueOf(b));
                            f.adj.get(b).remove(Integer.valueOf(a));
                        }
                    }
                    case 2 -> {
                        long v = rnd.nextLong(-50, 100);
                        t.setLoad(a, v);
                        f.load[a] = v;
                    }
                    default -> {
                        assertEquals(p.length > 0, t.joined(a, b));
                        if (p.length > 0) {
                            long mx = Long.MIN_VALUE;
                            long sum = 0;
                            for (int x : p) {
                                mx = Math.max(mx, f.load[x]);
                                sum += f.load[x];
                            }
                            assertEquals(mx, t.pathMax(a, b), "seed " + seed);
                            assertEquals(sum, t.pathSum(a, b), "seed " + seed);
                        }
                    }
                }
            }
        }
    }

    @Test
    void longChainStaysFast() {
        int n = 200_000;
        long[] loads = new long[n];
        for (int i = 0; i < n; i++) {
            loads[i] = i % 1000;
        }
        TowLines t = new TowLines(loads);
        for (int i = 0; i + 1 < n; i++) {
            assertTrue(t.link(i, i + 1));
        }
        long expected = 0;
        for (long v : loads) {
            expected += v;
        }
        assertEquals(expected, t.pathSum(0, n - 1));
        assertEquals(999, t.pathMax(n - 1, 0));
        assertTrue(t.cut(n / 2, n / 2 + 1));
        assertFalse(t.joined(0, n - 1));
        assertTrue(t.link(0, n - 1));
        assertTrue(t.joined(n / 2, n / 2 + 1));
    }

    @Test
    void questAndBadInput() {
        long[] loads = {4, 8, 2, 6};
        int[][] lines = {{0, 1}, {1, 2}, {2, 0}};
        assertEquals(8, TowLines.quest(loads, lines, 0, 2));
        assertEquals(-1, TowLines.quest(loads, lines, 0, 3));
        assertEquals("q_tow_lines", TowLines.QUEST_ID);
        TowLines t = new TowLines(loads);
        assertThrows(IllegalArgumentException.class, () -> t.pathMax(0, 3));
        assertThrows(IllegalArgumentException.class, () -> t.link(0, 9));
        assertThrows(IllegalArgumentException.class, () -> new TowLines(new long[0]));
        assertFalse(t.cut(1, 1));
    }
}
