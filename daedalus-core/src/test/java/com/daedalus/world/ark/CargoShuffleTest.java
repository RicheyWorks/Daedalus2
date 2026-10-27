// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.Arrays;
import java.util.List;
import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class CargoShuffleTest {

    /** Depth-limited search for a solution within d moves. */
    private static boolean reach(CargoShuffle h, int[] pos, int d) {
        if (h.solved(pos)) {
            return true;
        }
        if (d == 0) {
            return false;
        }
        for (int[] mv : h.moves(pos)) {
            int[] nx = pos.clone();
            nx[mv[0]] = mv[1];
            if (reach(h, nx, d - 1)) {
                return true;
            }
        }
        return false;
    }

    private static int deepening(CargoShuffle h, int[] pos, int cap) {
        for (int d = 0; d <= cap; d++) {
            if (reach(h, pos, d)) {
                return d;
            }
        }
        return -1;
    }

    /** A random hold with the lead crate on row 2 at the hatch, then a random backward scramble. */
    private static Object[] scrambled(SplittableRandom rnd, int n, int crates, int steps) {
        while (true) {
            boolean[] across = new boolean[crates];
            int[] len = new int[crates];
            int[] lane = new int[crates];
            int[] pos = new int[crates];
            across[0] = true;
            len[0] = 2;
            lane[0] = 2;
            pos[0] = n - 2;
            for (int i = 1; i < crates; i++) {
                across[i] = rnd.nextBoolean();
                len[i] = 2 + rnd.nextInt(2);
                lane[i] = rnd.nextInt(n);
                pos[i] = rnd.nextInt(n - len[i] + 1);
            }
            CargoShuffle h = new CargoShuffle(n, across, len, lane);
            if (!h.fits(pos)) {
                continue;
            }
            for (int s = 0; s < steps; s++) {
                List<int[]> mv = h.moves(pos);
                if (mv.isEmpty()) {
                    break;
                }
                int[] m = mv.get(rnd.nextInt(mv.size()));
                pos[m[0]] = m[1];
            }
            return new Object[] {h, pos};
        }
    }

    @Test
    void matchesIterativeDeepening() {
        SplittableRandom rnd = new SplittableRandom(422);
        for (int t = 0; t < 40; t++) {
            Object[] s = scrambled(rnd, 4 + rnd.nextInt(2), 3 + rnd.nextInt(3), 1 + rnd.nextInt(6));
            CargoShuffle h = (CargoShuffle) s[0];
            int[] pos = (int[]) s[1];
            int f = h.fewest(pos);
            assertThat(f).isBetween(0, 6);
            assertThat(deepening(h, pos, 6)).isEqualTo(f);
        }
    }

    @Test
    void plansReplayOnBiggerHolds() {
        SplittableRandom rnd = new SplittableRandom(4220);
        for (int t = 0; t < 30; t++) {
            Object[] s = scrambled(rnd, 6, 6 + rnd.nextInt(5), 40);
            CargoShuffle h = (CargoShuffle) s[0];
            int[] pos = (int[]) s[1];
            int[][] p = h.plan(pos);
            assertThat(h.fewest(pos)).isEqualTo(p.length);
            assertThat(h.valid(pos, p)).isTrue();
            if (p.length > 0) {
                assertThat(h.valid(pos, Arrays.copyOf(p, p.length - 1))).isFalse();
            }
        }
    }

    @Test
    void blockedHoldHasNoPlan() {
        CargoShuffle h = new CargoShuffle(4, new boolean[] {true, false}, new int[] {2, 2}, new int[] {1, 3});
        int[] pos = {0, 0};
        assertThat(h.fits(pos)).isTrue();
        assertThat(h.fits(new int[] {1, 1})).isTrue();
        assertThat(h.fits(new int[] {3, 0})).isFalse();
        CargoShuffle w = new CargoShuffle(4, new boolean[] {true, false, false},
                new int[] {2, 3, 2}, new int[] {1, 3, 3});
        assertThat(w.fits(new int[] {0, 0, 2})).isFalse();
        CargoShuffle jam = new CargoShuffle(4, new boolean[] {true, false, false},
                new int[] {2, 2, 2}, new int[] {1, 3, 3});
        assertThat(jam.fewest(new int[] {0, 0, 2})).isEqualTo(-1);
        assertThat(jam.plan(new int[] {0, 0, 2})).isEmpty();
        assertThat(h.fewest(pos)).isEqualTo(2);
    }

    @Test
    void questAndBounds() {
        CargoShuffle h = new CargoShuffle(4, new boolean[] {true, false}, new int[] {2, 2}, new int[] {1, 3});
        assertThat(h.quest(new int[] {0, 0}, 2)).isTrue();
        assertThat(h.quest(new int[] {0, 0}, 1)).isFalse();
        assertThat(h.fewest(new int[] {2, 2})).isZero();
        assertThat(CargoShuffle.QUEST_ID).isEqualTo("q_cargo_shuffle");
        assertThatThrownBy(() -> new CargoShuffle(9, new boolean[] {true}, new int[] {2}, new int[] {0}))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new CargoShuffle(4, new boolean[] {false}, new int[] {2}, new int[] {0}))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> h.solved(new int[] {3, 0})).isInstanceOf(IllegalArgumentException.class);
    }
}