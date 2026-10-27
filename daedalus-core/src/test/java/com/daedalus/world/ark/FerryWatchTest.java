// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.Arrays;
import org.junit.jupiter.api.Test;

class FerryWatchTest {

    /** Depth-limited search: can everyone be across within d crossings? */
    private static boolean reach(int m, int c, int b, int mn, int cn, int side, int d) {
        if (mn == 0 && cn == 0 && side == 1) {
            return true;
        }
        if (d == 0) {
            return false;
        }
        int sign = side == 0 ? -1 : 1;
        for (int i = 0; i <= b; i++) {
            for (int j = 0; i + j <= b; j++) {
                int nm = mn + sign * i;
                int nc = cn + sign * j;
                if (i + j > 0 && FerryWatch.safe(m, c, nm, nc) && reach(m, c, b, nm, nc, 1 - side, d - 1)) {
                    return true;
                }
            }
        }
        return false;
    }

    private static int deepening(int m, int c, int b, int cap) {
        for (int d = 1; d <= cap; d++) {
            if (reach(m, c, b, m, c, 0, d)) {
                return d;
            }
        }
        return -1;
    }

    @Test
    void matchesIterativeDeepening() {
        for (int m = 0; m <= 4; m++) {
            for (int c = 0; c <= 4; c++) {
                for (int b = 1; b <= 3; b++) {
                    if (m + c == 0) {
                        continue;
                    }
                    int f = FerryWatch.fewest(m, c, b);
                    int brute = deepening(m, c, b, f > 0 ? f : 13);
                    assertThat(f).as("m=%d c=%d b=%d", m, c, b).isEqualTo(brute);
                }
            }
        }
    }

    @Test
    void classicCrossing() {
        assertThat(FerryWatch.fewest(3, 3, 2)).isEqualTo(11);
        assertThat(deepening(3, 3, 2, 11)).isEqualTo(11);
        assertThat(FerryWatch.fewest(1, 0, 1)).isEqualTo(1);
    }

    @Test
    void plansReplay() {
        for (int m = 1; m <= 8; m++) {
            for (int b = 1; b <= 4; b++) {
                int[][] p = FerryWatch.plan(m, m, b);
                if (p.length > 0) {
                    assertThat(FerryWatch.valid(m, m, b, p)).isTrue();
                    int[][] cut = Arrays.copyOf(p, p.length - 1);
                    assertThat(FerryWatch.valid(m, m, b, cut)).isFalse();
                }
            }
        }
        assertThat(FerryWatch.valid(3, 3, 2, new int[][] {{2, 0}})).isFalse();
        assertThat(FerryWatch.valid(1, 1, 2, new int[][] {{1, 1}})).isTrue();
    }

    @Test
    void questAndBounds() {
        assertThat(FerryWatch.quest(3, 2, 11)).isTrue();
        assertThat(FerryWatch.quest(3, 2, 9)).isFalse();
        assertThat(FerryWatch.QUEST_ID).isEqualTo("q_ferry_watch");
        assertThat(FerryWatch.plan(2, 2, 1)).isEmpty();
        assertThat(FerryWatch.fewest(2, 2, 1)).isEqualTo(-1);
        assertThatThrownBy(() -> FerryWatch.plan(0, 0, 2)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> FerryWatch.plan(51, 1, 2)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> FerryWatch.plan(1, 1, 0)).isInstanceOf(IllegalArgumentException.class);
    }
}