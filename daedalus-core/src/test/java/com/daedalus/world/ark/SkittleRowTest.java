// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class SkittleRowTest {

    /** Physical Kayles on a pin bitmask: knock one pin or two adjacent pins. */
    private static boolean kaylesWins(int mask, Map<Integer, Boolean> memo) {
        Boolean c = memo.get(mask);
        if (c != null) {
            return c;
        }
        boolean win = false;
        for (int i = 0; i < 20 && !win; i++) {
            if ((mask >> i & 1) != 0) {
                win = !kaylesWins(mask & ~(1 << i), memo);
                if (!win && (mask >> (i + 1) & 1) != 0) {
                    win = !kaylesWins(mask & ~(3 << i), memo);
                }
            }
        }
        memo.put(mask, win);
        return win;
    }

    private static int[] segments(int mask) {
        List<Integer> out = new ArrayList<>();
        int run = 0;
        for (int i = 0; i <= 20; i++) {
            if ((mask >> i & 1) != 0) {
                run++;
            } else if (run > 0) {
                out.add(run);
                run = 0;
            }
        }
        return out.stream().mapToInt(Integer::intValue).toArray();
    }

    /** Generic brute force over sorted row lists for any octal code. */
    private static boolean wins(String code, List<Integer> rows, Map<List<Integer>, Boolean> memo) {
        Boolean c = memo.get(rows);
        if (c != null) {
            return c;
        }
        boolean win = false;
        for (int i = 0; i < rows.size() && !win; i++) {
            int n = rows.get(i);
            for (int k = 1; k < code.length() - 1 && k <= n && !win; k++) {
                int dg = code.charAt(k + 1) - '0';
                int r = n - k;
                for (int a = 0; a <= r && !win; a++) {
                    int b = r - a;
                    boolean ok = (r == 0 && (dg & 1) != 0)
                            || (r > 0 && (a == 0 || b == 0) && (dg & 2) != 0)
                            || (a > 0 && b > 0 && (dg & 4) != 0);
                    if (ok) {
                        List<Integer> nx = new ArrayList<>(rows);
                        nx.remove(i);
                        if (a > 0) {
                            nx.add(a);
                        }
                        if (b > 0) {
                            nx.add(b);
                        }
                        nx.sort(null);
                        win = !wins(code, nx, memo);
                    }
                }
            }
        }
        memo.put(rows, win);
        return win;
    }

    @Test
    void kaylesMatchesPhysicalPins() {
        Map<Integer, Boolean> memo = new HashMap<>();
        for (int mask = 0; mask < 1 << 14; mask++) {
            boolean grundyWin = SkittleRow.nimSum(SkittleRow.KAYLES, segments(mask)) != 0;
            assertThat(grundyWin).as("mask=%d", mask).isEqualTo(kaylesWins(mask, memo));
        }
    }

    @Test
    void codesMatchBruteForce() {
        SplittableRandom rnd = new SplittableRandom(411);
        for (String code : new String[] {"0.77", "0.137", "0.07", "0.6", "0.73", "0.333", "0.4", "0.157"}) {
            Map<List<Integer>, Boolean> memo = new HashMap<>();
            for (int t = 0; t < 60; t++) {
                List<Integer> rows = new ArrayList<>();
                int cnt = 1 + rnd.nextInt(3);
                for (int j = 0; j < cnt; j++) {
                    rows.add(1 + rnd.nextInt(9));
                }
                rows.sort(null);
                int[] arr = rows.stream().mapToInt(Integer::intValue).toArray();
                boolean w = wins(code, rows, memo);
                assertThat(SkittleRow.nimSum(code, arr) != 0).as("%s %s", code, rows).isEqualTo(w);
                int[] mv = SkittleRow.winningMove(code, arr);
                assertThat(mv.length == 4).isEqualTo(w);
                if (w) {
                    List<Integer> nx = new ArrayList<>(rows);
                    nx.remove(mv[0]);
                    if (mv[2] > 0) {
                        nx.add(mv[2]);
                    }
                    if (mv[3] > 0) {
                        nx.add(mv[3]);
                    }
                    nx.sort(null);
                    assertThat(mv[1] + mv[2] + mv[3]).isEqualTo(arr[mv[0]]);
                    assertThat(wins(code, nx, memo)).isFalse();
                }
            }
        }
    }

    @Test
    void kaylesAndDawsonArePeriodic() {
        int[] k = SkittleRow.grundy(SkittleRow.KAYLES, 400);
        for (int n = 72; n + 12 <= 400; n++) {
            assertThat(k[n + 12]).as("n=%d", n).isEqualTo(k[n]);
        }
        int[] dw = SkittleRow.grundy(SkittleRow.DAWSON, 400);
        for (int n = 52; n + 34 <= 400; n++) {
            assertThat(dw[n + 34]).as("n=%d", n).isEqualTo(dw[n]);
        }
    }

    @Test
    void questAndBounds() {
        Map<List<Integer>, Boolean> memo = new HashMap<>();
        boolean w = wins(SkittleRow.KAYLES, List.of(3, 5, 7), memo);
        assertThat(SkittleRow.quest(new int[] {3, 5, 7}, w)).isTrue();
        assertThat(SkittleRow.quest(new int[] {3, 5, 7}, !w)).isFalse();
        assertThat(SkittleRow.QUEST_ID).isEqualTo("q_skittle_row");
        assertThat(SkittleRow.winningMove(SkittleRow.KAYLES)).isEmpty();
        assertThatThrownBy(() -> SkittleRow.grundy("0.8", 5)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> SkittleRow.grundy("1.7", 5)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> SkittleRow.grundy("0.7", -1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> SkittleRow.nimSum("0.7", -2)).isInstanceOf(IllegalArgumentException.class);
    }
}