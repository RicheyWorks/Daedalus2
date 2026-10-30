// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;
import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class TallyRailsTest {

    private static int[][] board(int n, int mask) {
        int[][] b = new int[n][n];
        for (int i = 0; i < n * n; i++) {
            b[i / n][i % n] = mask >> i & 1;
        }
        return b;
    }

    private static int[][] clues(int[][] b) {
        int n = b.length;
        int[][] out = new int[2][n];
        for (int r = 0; r < n; r++) {
            for (int c = 0; c < n; c++) {
                out[0][r] += b[r][c] * (c + 1);
                out[1][c] += b[r][c] * (r + 1);
            }
        }
        return out;
    }

    private static long brute(int[] rows, int[] cols) {
        int n = rows.length;
        long found = 0;
        for (int mask = 0; mask < (1 << (n * n)); mask++) {
            if (TallyRails.isValid(rows, cols, board(n, mask))) {
                found++;
            }
        }
        return found;
    }

    @Test
    void countMatchesBruteForceUpToFour() {
        SplittableRandom rnd = new SplittableRandom(394);
        for (int n = 1; n <= 4; n++) {
            for (int t = 0; t < 12; t++) {
                int[][] k = clues(board(n, rnd.nextInt(1 << (n * n))));
                long want = brute(k[0], k[1]);
                assertThat(want).isPositive();
                assertThat(TallyRails.count(k[0], k[1], Long.MAX_VALUE)).as("n%d t%d", n, t)
                    .isEqualTo(want);
            }
        }
        int[] r = {3, 0, 0};
        int[] c = {0, 0, 0};
        assertThat(TallyRails.count(r, c, Long.MAX_VALUE)).isZero().isEqualTo(brute(r, c));
        assertThat(TallyRails.solve(r, c)).isEmpty();
    }

    @Test
    void everyFourByFourBoardIsCountedOnce() {
        long total = 0;
        Map<String, Long> seen = new HashMap<>();
        for (int mask = 0; mask < (1 << 16); mask++) {
            int[][] k = clues(board(4, mask));
            seen.merge(Arrays.toString(k[0]) + Arrays.toString(k[1]), 1L,
                Long::sum);
        }
        for (Map.Entry<String, Long> e : seen.entrySet()) {
            total += e.getValue();
        }
        assertThat(total).isEqualTo(1L << 16);
        int[][] k = clues(board(4, 0x1234));
        String key = Arrays.toString(k[0]) + Arrays.toString(k[1]);
        assertThat(TallyRails.count(k[0], k[1], Long.MAX_VALUE)).isEqualTo(seen.get(key));
    }

    @Test
    void solveAndQuestSixBySix() {
        SplittableRandom rnd = new SplittableRandom(6394);
        int[][] hidden = new int[6][6];
        for (int[] row : hidden) {
            for (int c = 0; c < 6; c++) {
                row[c] = rnd.nextInt(2);
            }
        }
        int[][] k = clues(hidden);
        int[][] s = TallyRails.solve(k[0], k[1]);
        assertThat(s).hasNumberOfRows(6);
        assertThat(TallyRails.quest(k[0], k[1], s)).isTrue();
        s[0][0] ^= 1;
        assertThat(TallyRails.quest(k[0], k[1], s)).isFalse();
        assertThat(TallyRails.QUEST_ID).isEqualTo("q_tally_rails");
        assertThatThrownBy(() -> TallyRails.count(new int[7], new int[7], 1))
            .isInstanceOf(IllegalArgumentException.class);
    }
}