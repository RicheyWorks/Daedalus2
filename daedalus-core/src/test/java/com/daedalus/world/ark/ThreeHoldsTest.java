// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayDeque;
import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;
import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class ThreeHoldsTest {

    private static int bfs(int[] start) {
        int[] goal = start.clone();
        Arrays.sort(goal);
        String g = Arrays.toString(goal);
        Map<String, Integer> dist = new HashMap<>();
        ArrayDeque<int[]> q = new ArrayDeque<>();
        dist.put(Arrays.toString(start), 0);
        q.add(start);
        while (!q.isEmpty()) {
            int[] a = q.poll();
            String k = Arrays.toString(a);
            int d = dist.get(k);
            if (k.equals(g)) {
                return d;
            }
            for (int i = 0; i < a.length; i++) {
                for (int j = i + 1; j < a.length; j++) {
                    if (a[i] != a[j]) {
                        int[] b = a.clone();
                        b[i] = a[j];
                        b[j] = a[i];
                        if (dist.putIfAbsent(Arrays.toString(b), d + 1) == null) {
                            q.add(b);
                        }
                    }
                }
            }
        }
        throw new AssertionError("unreachable");
    }

    @Test
    void minSwapsMatchesBfsOnEveryRowUpToSeven() {
        for (int n = 0; n <= 7; n++) {
            int total = 1;
            for (int i = 0; i < n; i++) {
                total *= 3;
            }
            for (int code = 0; code < total; code++) {
                int[] row = new int[n];
                int x = code;
                for (int i = 0; i < n; i++) {
                    row[i] = x % 3;
                    x /= 3;
                }
                assertThat(ThreeHolds.minSwaps(row)).isEqualTo(bfs(row));
            }
        }
    }

    @Test
    void partitionMatchesSort() {
        SplittableRandom rnd = new SplittableRandom(327);
        for (int t = 0; t < 3000; t++) {
            int[] row = new int[rnd.nextInt(0, 200)];
            for (int i = 0; i < row.length; i++) {
                row[i] = rnd.nextInt(3);
            }
            int[] want = row.clone();
            Arrays.sort(want);
            assertThat(ThreeHolds.partition(row)).containsExactly(want);
        }
    }

    @Test
    void questAndGuards() {
        assertThat(ThreeHolds.QUEST_ID).isEqualTo("q_three_holds");
        assertThat(ThreeHolds.quest(new int[] {2, 0, 1}, 2)).isTrue();
        assertThat(ThreeHolds.quest(new int[] {1, 0}, 2)).isFalse();
        assertThatThrownBy(() -> ThreeHolds.partition(new int[] {3})).isInstanceOf(IllegalArgumentException.class);
    }
}