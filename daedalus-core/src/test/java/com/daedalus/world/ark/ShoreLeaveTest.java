// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class ShoreLeaveTest {

    private static long brute(int[][] rooms, int[] clues) {
        int h = rooms.length;
        int w = rooms[0].length;
        long found = 0;
        int[][] b = new int[h][w];
        for (int mask = 0; mask < (1 << (h * w)); mask++) {
            for (int i = 0; i < h * w; i++) {
                b[i / w][i % w] = mask >> i & 1;
            }
            if (ShoreLeave.isValid(rooms, clues, b)) {
                found++;
            }
        }
        return found;
    }

    /** Rooms as rectangles from cutting rows and columns at random. */
    private static int[][] rectRooms(SplittableRandom rnd, int h, int w, int[] countOut) {
        int[] rowBand = new int[h];
        int[] colBand = new int[w];
        int rb = 0;
        for (int r = 1; r < h; r++) {
            rb += rnd.nextInt(2);
            rowBand[r] = rb;
        }
        int cb = 0;
        for (int c = 1; c < w; c++) {
            cb += rnd.nextInt(2);
            colBand[c] = cb;
        }
        int[][] g = new int[h][w];
        for (int r = 0; r < h; r++) {
            for (int c = 0; c < w; c++) {
                g[r][c] = rowBand[r] * (cb + 1) + colBand[c];
            }
        }
        countOut[0] = (rb + 1) * (cb + 1);
        return g;
    }

    @Test
    void countMatchesBruteForceUpToFour() {
        SplittableRandom rnd = new SplittableRandom(405);
        int solvable = 0;
        for (int t = 0; t < 40; t++) {
            int h = rnd.nextInt(1, 5);
            int w = rnd.nextInt(1, 5);
            int[] k = new int[1];
            int[][] rooms = rectRooms(rnd, h, w, k);
            int[] clues = new int[k[0]];
            for (int i = 0; i < k[0]; i++) {
                clues[i] = rnd.nextInt(3) - 1;
            }
            long want = brute(rooms, clues);
            if (want > 0) {
                solvable++;
            }
            assertThat(ShoreLeave.count(rooms, clues, Long.MAX_VALUE)).as("t%d", t)
                .isEqualTo(want);
            assertThat(ShoreLeave.solve(rooms, clues).length == 0).isEqualTo(want == 0);
        }
        assertThat(solvable).isPositive();
    }

    @Test
    void longOpenRunAcrossThreeRoomsIsRefused() {
        int[][] rooms = {{0, 1, 2}};
        int[] clues = {-1, -1, -1};
        assertThat(ShoreLeave.isValid(rooms, clues, new int[][] {{0, 0, 0}})).isFalse();
        assertThat(ShoreLeave.isValid(rooms, clues, new int[][] {{0, 1, 0}})).isFalse();
        assertThat(ShoreLeave.isValid(rooms, clues, new int[][] {{1, 0, 0}})).isTrue();
        assertThat(ShoreLeave.count(rooms, clues, Long.MAX_VALUE)).isEqualTo(3)
            .isEqualTo(brute(rooms, clues));
    }

    @Test
    void solveAndQuestFiveByFive() {
        int[][] rooms = {
            {0, 0, 1, 1, 1},
            {0, 0, 1, 1, 1},
            {2, 2, 3, 3, 4},
            {2, 2, 3, 3, 4},
            {2, 2, 3, 3, 4},
        };
        int[] clues = {1, -1, 2, -1, 1};
        int[][] s = ShoreLeave.solve(rooms, clues);
        assertThat(s).hasNumberOfRows(5);
        assertThat(ShoreLeave.quest(rooms, clues, s)).isTrue();
        assertThat(ShoreLeave.count(rooms, clues, Long.MAX_VALUE)).isPositive();
        s[0][0] ^= 1;
        assertThat(ShoreLeave.quest(rooms, clues, s)).isFalse();
        assertThat(ShoreLeave.QUEST_ID).isEqualTo("q_shore_leave");
        assertThatThrownBy(() -> ShoreLeave.count(new int[6][1], new int[1], 1))
            .isInstanceOf(IllegalArgumentException.class);
    }
}