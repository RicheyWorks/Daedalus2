// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.AlloyWindow.Grade;
import com.daedalus.world.forge.AlloyWindow.Window;
import org.junit.jupiter.api.Test;

import java.util.SplittableRandom;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class AlloyWindowTest {

    @Test
    void matchesBruteForceOnSeededTrains() {
        SplittableRandom r = new SplittableRandom(5);
        int found = 0;
        for (long seed = 0; seed < 300; seed++) {
            int kinds = 1 + (int) (seed % 4);
            int[] t = AlloyWindow.train(seed, (int) (seed % 40), kinds);
            int[] need = new int[kinds];
            for (int k = 0; k < kinds; k++) {
                need[k] = r.nextInt(3);
            }
            Window best = Window.NONE;
            for (int i = 0; i <= t.length; i++) {
                for (int j = i; j <= t.length; j++) {
                    Window w = new Window(i, j);
                    if (AlloyWindow.holds(t, need, w) && (best == Window.NONE || w.length() < best.length())) {
                        best = w;
                    }
                }
            }
            Window got = AlloyWindow.shortest(t, need);
            assertThat(got).as("seed %d", seed).isEqualTo(best);
            if (best != Window.NONE) {
                found++;
                assertThat(AlloyWindow.grade(t, need, got)).isEqualTo(Grade.PURE);
            }
        }
        assertThat(found).isGreaterThan(100);
    }

    @Test
    void knownTrains() {
        int[] t = {0, 1, 2, 0, 1, 2, 2, 0};
        assertThat(AlloyWindow.shortest(t, new int[] {1, 1, 2})).isEqualTo(new Window(2, 6));
        assertThat(AlloyWindow.shortest(t, new int[] {0, 0, 4})).isEqualTo(Window.NONE);
        assertThat(AlloyWindow.shortest(t, new int[] {0, 0, 0})).isEqualTo(new Window(0, 0));
        assertThat(Window.NONE.length()).isZero();
        assertThatThrownBy(() -> AlloyWindow.shortest(new int[] {3}, new int[] {1}))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> AlloyWindow.shortest(new int[] {0}, new int[] {-1}))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void gradesLinesAndReplay() {
        int[] t = {0, 1, 0, 1};
        int[] need = {1, 1};
        assertThat(AlloyWindow.grade(t, need, new Window(1, 3))).isEqualTo(Grade.PURE);
        assertThat(AlloyWindow.grade(t, need, new Window(0, 3))).isEqualTo(Grade.SLAG);
        assertThat(AlloyWindow.grade(t, need, new Window(0, 1))).isEqualTo(Grade.SLAG);
        assertThat(AlloyWindow.grade(t, new int[] {3, 0}, new Window(0, 4))).isEqualTo(Grade.SLAG);
        assertThat(AlloyWindow.holds(t, need, new Window(2, 9))).isFalse();
        for (Grade g : Grade.values()) {
            assertThat(AlloyWindow.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(AlloyWindow.QUEST_ID).isEqualTo("q_alloy_window");
        assertThat(AlloyWindow.train(2, 30, 3)).isEqualTo(AlloyWindow.train(2, 30, 3)).hasSize(30);
        assertThatThrownBy(() -> AlloyWindow.train(1, 3, 0)).isInstanceOf(IllegalArgumentException.class);
    }
}
