// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.ark.ArkCellar.State;

import org.junit.jupiter.api.Test;

class RainPocketsTest {

    @Test
    void twoPointerMatchesBruteForcePerColumn() {
        for (long seed = 1; seed <= 400; seed++) {
            int[] h = RainPockets.columns(seed, (int) (seed % 40), 15);
            assertThat(RainPockets.pockets(h)).as("seed %d", seed).containsExactly(brute(h));
        }
    }

    @Test
    void handPickedShelf() {
        int[] h = {0, 1, 0, 2, 1, 0, 1, 3, 2, 1, 2, 1};
        assertThat(RainPockets.pockets(h)).containsExactly(0, 0, 1, 0, 1, 2, 1, 0, 0, 1, 0, 0);
        assertThat(RainPockets.total(h)).isEqualTo(6);
        assertThat(RainPockets.total(new int[] {4, 2, 0, 3, 2, 5})).isEqualTo(9);
    }

    @Test
    void slopesAndEdgesHoldNothing() {
        assertThat(RainPockets.total(new int[0])).isZero();
        assertThat(RainPockets.total(new int[] {7})).isZero();
        assertThat(RainPockets.total(new int[] {1, 2, 3, 4})).isZero();
        assertThat(RainPockets.total(new int[] {4, 3, 2, 1})).isZero();
        assertThat(RainPockets.columns(9, 30, 8)).isEqualTo(RainPockets.columns(9, 30, 8));
        assertThatThrownBy(() -> RainPockets.pockets(new int[] {1, -1}))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> RainPockets.columns(1, 3, 0))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void topUpFeedsTheArkCisternAndSpillsOverCap() {
        ArkCellar cellar = new ArkCellar(ArkCellar.Rules.defaults());
        State s = cellar.start(100);
        assertThat(RainPockets.topUp(cellar, s, 9).cisternL()).isEqualTo(109.0);
        assertThat(RainPockets.topUp(cellar, s, 1_000).cisternL()).isEqualTo(400.0);
        assertThatThrownBy(() -> RainPockets.topUp(cellar, s, -1))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void questHook() {
        int[] h = {4, 2, 0, 3, 2, 5};
        assertThat(RainPockets.quest(h, 9)).isTrue();
        assertThat(RainPockets.quest(h, 10)).isFalse();
        assertThat(RainPockets.QUEST_ID).isEqualTo("q_rain_pockets");
    }

    private static int[] brute(int[] h) {
        int[] w = new int[h.length];
        for (int i = 0; i < h.length; i++) {
            int lm = 0;
            int rm = 0;
            for (int j = 0; j <= i; j++) {
                lm = Math.max(lm, h[j]);
            }
            for (int j = i; j < h.length; j++) {
                rm = Math.max(rm, h[j]);
            }
            w[i] = Math.min(lm, rm) - h[i];
        }
        return w;
    }
}
