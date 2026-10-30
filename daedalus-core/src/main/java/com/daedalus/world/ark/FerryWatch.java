// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.ArrayDeque;
import java.util.Arrays;

/**
 * G412 The Ferry Watch: m crew and c raiders must cross from the near bank to the ark with a
 * ferry that holds 1 to b people. On either bank the raiders may never outnumber the crew while
 * any crew stand there. Gives the fewest crossings (breadth-first search over the
 * (crew near, raiders near, ferry side) states), one shortest plan and a plan checker.
 */
public final class FerryWatch {

    public static final String QUEST_ID = "q_ferry_watch";
    public static final int MAX_PEOPLE = 50;

    private FerryWatch() { }

    private static void check(int m, int c, int b) {
        if (m < 0 || c < 0 || m > MAX_PEOPLE || c > MAX_PEOPLE || m + c == 0 || b < 1 || b > 2 * MAX_PEOPLE) {
            throw new IllegalArgumentException("bad ferry setup");
        }
    }

    /** True when neither bank has crew outnumbered by raiders. */
    public static boolean safe(int m, int c, int crewNear, int raidersNear) {
        if (crewNear < 0 || raidersNear < 0 || crewNear > m || raidersNear > c) {
            return false;
        }
        int crewFar = m - crewNear;
        int raidersFar = c - raidersNear;
        return (crewNear == 0 || crewNear >= raidersNear) && (crewFar == 0 || crewFar >= raidersFar);
    }

    /** Shortest plan as loads {crew, raiders}, one per crossing; empty when impossible. */
    public static int[][] plan(int m, int c, int b) {
        check(m, c, b);
        int w = c + 1;
        int states = (m + 1) * w * 2;
        int[] prev = new int[states];
        Arrays.fill(prev, -2);
        int start = (m * w + c) * 2;
        prev[start] = -1;
        ArrayDeque<Integer> q = new ArrayDeque<>();
        q.add(start);
        int goal = 1;
        while (!q.isEmpty() && prev[goal] == -2) {
            int s = q.poll();
            int side = s & 1;
            int mn = (s >> 1) / w;
            int cn = (s >> 1) % w;
            int sign = side == 0 ? -1 : 1;
            for (int i = 0; i <= b; i++) {
                for (int j = 0; i + j <= b; j++) {
                    if (i + j == 0) {
                        continue;
                    }
                    int nm = mn + sign * i;
                    int nc = cn + sign * j;
                    if (safe(m, c, nm, nc)) {
                        int t = (nm * w + nc) * 2 + (1 - side);
                        if (prev[t] == -2) {
                            prev[t] = s;
                            q.add(t);
                        }
                    }
                }
            }
        }
        if (prev[goal] == -2) {
            return new int[0][];
        }
        ArrayDeque<int[]> out = new ArrayDeque<>();
        for (int s = goal; prev[s] != -1; s = prev[s]) {
            int p = prev[s];
            int dm = Math.abs((s >> 1) / w - (p >> 1) / w);
            int dc = Math.abs((s >> 1) % w - (p >> 1) % w);
            out.push(new int[] {dm, dc});
        }
        return out.toArray(new int[0][]);
    }

    /** Fewest crossings, or -1 when the crossing is impossible. */
    public static int fewest(int m, int c, int b) {
        int[][] p = plan(m, c, b);
        return p.length == 0 ? -1 : p.length;
    }

    /** True when the loads, ferried alternately out and back, bring everyone across safely. */
    public static boolean valid(int m, int c, int b, int[][] loads) {
        check(m, c, b);
        int mn = m;
        int cn = c;
        for (int k = 0; k < loads.length; k++) {
            int[] l = loads[k];
            if (l == null || l.length != 2 || l[0] < 0 || l[1] < 0 || l[0] + l[1] < 1 || l[0] + l[1] > b) {
                return false;
            }
            int sign = (k & 1) == 0 ? -1 : 1;
            mn += sign * l[0];
            cn += sign * l[1];
            if (!safe(m, c, mn, cn)) {
                return false;
            }
        }
        return mn == 0 && cn == 0 && (loads.length & 1) != 0;
    }

    /** Quest q_ferry_watch: the bosun names the fewest crossings for m crew and m raiders. */
    public static boolean quest(int m, int b, int answer) {
        return fewest(m, m, b) == answer;
    }
}