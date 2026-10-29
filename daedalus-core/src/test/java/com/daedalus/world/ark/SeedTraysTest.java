// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.Arrays;
import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class SeedTraysTest {

    private static int[] board(int[] r) {
        return Arrays.copyOf(r, r.length - 1);
    }

    /** Plain minimax, no memo. */
    private static int plain(int[] b, int side) {
        int p = (b.length - 2) / 2;
        if (SeedTrays.over(b)) {
            int s0 = Arrays.stream(b, 0, p + 1).sum();
            int s1 = Arrays.stream(b, p + 1, b.length).sum();
            return side == 0 ? s0 - s1 : s1 - s0;
        }
        int best = Integer.MIN_VALUE;
        for (int i = 0; i < p; i++) {
            if (b[side * (p + 1) + i] > 0) {
                int[] r = SeedTrays.sow(b, side, i);
                int next = r[r.length - 1];
                int v = next == side ? plain(board(r), side) : -plain(board(r), next);
                best = Math.max(best, v);
            }
        }
        return best;
    }

    @Test
    void sowingCasesFromTheRules() {
        int[] r = SeedTrays.sow(SeedTrays.start(6, 4), 0, 2);
        assertThat(board(r)).containsExactly(4, 4, 0, 5, 5, 5, 1, 4, 4, 4, 4, 4, 4, 0);
        assertThat(r[14]).isZero();
        int[] cap = {1, 0, 0, 0, 0, 5, 0, 0};
        int[] rc = SeedTrays.sow(cap, 0, 0);
        assertThat(board(rc)).containsExactly(0, 0, 0, 6, 0, 0, 0, 0);
        int[] skip = {0, 0, 9, 0, 1, 0, 0, 0};
        int[] rs = SeedTrays.sow(skip, 0, 2);
        assertThat(rs[7]).isZero();
        assertThat(Arrays.stream(board(rs)).sum()).isEqualTo(10);
    }

    @Test
    void randomGamesConserveSeeds() {
        SplittableRandom rnd = new SplittableRandom(418);
        for (int t = 0; t < 300; t++) {
            int p = 1 + rnd.nextInt(8);
            int s = 1 + rnd.nextInt(12);
            int[] b = SeedTrays.start(p, s);
            int side = 0;
            while (!SeedTrays.over(b)) {
                int i = rnd.nextInt(p);
                if (b[side * (p + 1) + i] == 0) {
                    continue;
                }
                int[] r = SeedTrays.sow(b, side, i);
                side = r[r.length - 1];
                b = board(r);
                assertThat(Arrays.stream(b).sum()).isEqualTo(2 * p * s);
            }
            assertThat(b[p] + b[2 * p + 1]).isEqualTo(2 * p * s);
        }
    }

    @Test
    void solverMatchesPlainMinimax() {
        SeedTrays st = new SeedTrays();
        for (int p = 1; p <= 3; p++) {
            for (int s = 1; s <= 3 && 2 * p * s <= 14; s++) {
                int[] b = SeedTrays.start(p, s);
                assertThat(st.margin(b, 0)).as("p=%d s=%d", p, s).isEqualTo(plain(b, 0));
                assertThat(st.margin(b, 1)).isEqualTo(plain(b, 1));
            }
        }
    }

    @Test
    void bestPlayReplaysAndQuest() {
        SeedTrays st = new SeedTrays();
        int[] b = SeedTrays.start(3, 2);
        int want = st.margin(b, 0);
        int side = 0;
        while (st.bestPit(b, side) >= 0) {
            int[] r = SeedTrays.sow(b, side, st.bestPit(b, side));
            side = r[r.length - 1];
            b = board(r);
        }
        assertThat(b[3] - b[7]).isEqualTo(want);
        assertThat(SeedTrays.quest(want)).isTrue();
        assertThat(SeedTrays.quest(want + 1)).isFalse();
        assertThat(SeedTrays.QUEST_ID).isEqualTo("q_seed_trays");
        assertThatThrownBy(() -> SeedTrays.start(9, 1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> SeedTrays.sow(SeedTrays.start(3, 2), 0, 3)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new SeedTrays().margin(SeedTrays.start(6, 4), 0)).isInstanceOf(IllegalArgumentException.class);
    }
}