// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.Arrays;
import java.util.List;
import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class HoldBlocksTest {

    private static boolean reach(HoldBlocks hb, int[] pos, int d) {
        if (hb.solved(pos)) {
            return true;
        }
        if (d == 0) {
            return false;
        }
        for (int[] mv : hb.moves(pos)) {
            if (reach(hb, hb.apply(pos, mv), d - 1)) {
                return true;
            }
        }
        return false;
    }

    private static int deepening(HoldBlocks hb, int[] pos, int cap) {
        for (int d = 0; d <= cap; d++) {
            if (reach(hb, pos, d)) {
                return d;
            }
        }
        return -1;
    }

    /** Random blocks placed with the lead on its goal, then a random scramble. */
    private static Object[] scrambled(SplittableRandom rnd, int w, int h, int blocks, int steps) {
        while (true) {
            int[] bw = new int[blocks];
            int[] bh = new int[blocks];
            int[] pos = new int[2 * blocks];
            bw[0] = 2;
            bh[0] = 2;
            for (int i = 1; i < blocks; i++) {
                bw[i] = 1 + rnd.nextInt(2);
                bh[i] = 1 + rnd.nextInt(2);
                pos[2 * i] = rnd.nextInt(w - bw[i] + 1);
                pos[2 * i + 1] = rnd.nextInt(h - bh[i] + 1);
            }
            HoldBlocks hb = new HoldBlocks(w, h, bw, bh, 0, 0);
            if (!hb.fits(pos)) {
                continue;
            }
            for (int s = 0; s < steps; s++) {
                List<int[]> mv = hb.moves(pos);
                if (mv.isEmpty()) {
                    break;
                }
                pos = hb.apply(pos, mv.get(rnd.nextInt(mv.size())));
            }
            return new Object[] {hb, pos};
        }
    }

    @Test
    void matchesIterativeDeepening() {
        SplittableRandom rnd = new SplittableRandom(426);
        for (int t = 0; t < 40; t++) {
            Object[] s = scrambled(rnd, 4, 4, 3 + rnd.nextInt(3), 1 + rnd.nextInt(6));
            HoldBlocks hb = (HoldBlocks) s[0];
            int[] pos = (int[]) s[1];
            int f = hb.fewest(pos);
            assertThat(f).isBetween(0, 6);
            assertThat(deepening(hb, pos, 6)).isEqualTo(f);
        }
    }

    @Test
    void plansReplayOnBiggerHolds() {
        SplittableRandom rnd = new SplittableRandom(4260);
        for (int t = 0; t < 20; t++) {
            Object[] s = scrambled(rnd, 5, 5, 5 + rnd.nextInt(4), 60);
            HoldBlocks hb = (HoldBlocks) s[0];
            int[] pos = (int[]) s[1];
            int[][] p = hb.plan(pos);
            assertThat(hb.fewest(pos)).isEqualTo(p.length);
            assertThat(hb.valid(pos, p)).isTrue();
            if (p.length > 0) {
                assertThat(hb.valid(pos, Arrays.copyOf(p, p.length - 1))).isFalse();
            }
        }
    }

    @Test
    void jammedAndSmallCases() {
        HoldBlocks one = new HoldBlocks(3, 3, new int[] {2, 1}, new int[] {2, 1}, 0, 0);
        assertThat(one.fewest(new int[] {1, 0, 0, 0})).isEqualTo(3);
        assertThat(deepening(one, new int[] {1, 0, 0, 0}, 5)).isEqualTo(3);
        HoldBlocks jam = new HoldBlocks(2, 3, new int[] {2, 2}, new int[] {1, 2}, 0, 0);
        assertThat(jam.fewest(new int[] {0, 2, 0, 0})).isEqualTo(-1);
        assertThat(jam.plan(new int[] {0, 2, 0, 0})).isEmpty();
        assertThat(jam.fits(new int[] {0, 1, 0, 0})).isFalse();
    }

    @Test
    void questAndBounds() {
        HoldBlocks one = new HoldBlocks(3, 3, new int[] {2, 1}, new int[] {2, 1}, 0, 0);
        assertThat(one.quest(new int[] {1, 0, 0, 0}, 3)).isTrue();
        assertThat(one.quest(new int[] {1, 0, 0, 0}, 2)).isFalse();
        assertThat(one.fewest(new int[] {0, 0, 2, 1})).isZero();
        assertThat(HoldBlocks.QUEST_ID).isEqualTo("q_hold_blocks");
        assertThatThrownBy(() -> new HoldBlocks(7, 2, new int[] {1}, new int[] {1}, 0, 0))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new HoldBlocks(3, 3, new int[] {4}, new int[] {1}, 0, 0))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> one.apply(new int[] {1, 0, 0, 0}, new int[] {0, 0}))
                .isInstanceOf(IllegalArgumentException.class);
    }
}