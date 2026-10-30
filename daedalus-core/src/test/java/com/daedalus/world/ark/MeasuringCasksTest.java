// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.ark.MeasuringCasks.Move;
import java.util.ArrayDeque;
import java.util.Arrays;
import java.util.List;
import org.junit.jupiter.api.Test;

class MeasuringCasksTest {

    /** Fewest moves by breadth-first search over (A, B) levels, or -1. */
    private static int bfs(int a, int b, int c) {
        int[][] dist = new int[a + 1][b + 1];
        for (int[] row : dist) {
            Arrays.fill(row, -1);
        }
        ArrayDeque<int[]> q = new ArrayDeque<>();
        dist[0][0] = 0;
        q.add(new int[] {0, 0});
        while (!q.isEmpty()) {
            int[] s = q.poll();
            int x = s[0];
            int y = s[1];
            if (x == c || y == c) {
                return dist[x][y];
            }
            int ab = Math.min(x, b - y);
            int ba = Math.min(y, a - x);
            int[][] next = {{a, y}, {x, b}, {0, y}, {x, 0}, {x - ab, y + ab}, {x + ba, y - ba}};
            for (int[] n : next) {
                if (dist[n[0]][n[1]] < 0) {
                    dist[n[0]][n[1]] = dist[x][y] + 1;
                    q.add(n);
                }
            }
        }
        return -1;
    }

    @Test
    void planMatchesBreadthFirstSearch() {
        for (int a = 1; a <= 14; a++) {
            for (int b = 1; b <= 14; b++) {
                for (int c = 0; c <= 15; c++) {
                    int want = bfs(a, b, c);
                    List<Move> plan = MeasuringCasks.plan(a, b, c);
                    if (want < 0) {
                        assertThat(plan).as("%d,%d,%d", a, b, c).isNull();
                        assertThat(MeasuringCasks.solvable(a, b, c)).isFalse();
                    } else {
                        assertThat(plan).as("%d,%d,%d", a, b, c).hasSize(want);
                        int[] end = MeasuringCasks.play(a, b, plan);
                        assertThat(end[0] == c || end[1] == c).isTrue();
                    }
                }
            }
        }
    }

    @Test
    void bezoutIdentity() {
        for (long a = 0; a <= 60; a++) {
            for (long b = 0; b <= 60; b++) {
                MeasuringCasks.Bezout z = MeasuringCasks.bezout(a, b);
                assertThat(a * z.x() + b * z.y()).isEqualTo(z.g());
                assertThat(z.g()).isEqualTo(java.math.BigInteger.valueOf(a).gcd(java.math.BigInteger.valueOf(b)).longValue());
            }
        }
        assertThat(MeasuringCasks.bezout(240, 46)).isEqualTo(new MeasuringCasks.Bezout(2, -9, 47));
    }

    @Test
    void dieHardAndQuest() {
        List<Move> p = MeasuringCasks.plan(3, 5, 4);
        assertThat(p).hasSize(6);
        assertThat(MeasuringCasks.quest(3, 5, 4, p)).isTrue();
        assertThat(MeasuringCasks.quest(3, 5, 4, List.of(Move.FILL_B, Move.POUR_B_TO_A, Move.EMPTY_A,
            Move.POUR_B_TO_A, Move.FILL_B, Move.POUR_B_TO_A))).isTrue();
        assertThat(MeasuringCasks.quest(3, 5, 4, List.of(Move.FILL_B, Move.POUR_B_TO_A))).isFalse();
        assertThat(MeasuringCasks.solvable(6, 9, 4)).isFalse();
        assertThat(MeasuringCasks.plan(6, 9, 4)).isNull();
        assertThat(MeasuringCasks.plan(4, 9, 0)).isEmpty();
        assertThat(MeasuringCasks.plan(99_991, 99_989, 1)).isNotNull();
        assertThat(MeasuringCasks.QUEST_ID).isEqualTo("q_measuring_casks");
        assertThatThrownBy(() -> MeasuringCasks.plan(0, 5, 1)).isInstanceOf(IllegalArgumentException.class);
    }
}
