// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.FurnaceWatch.Grade;
import com.daedalus.world.forge.FurnaceWatch.Stretch;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class FurnaceWatchTest {

    @Test
    void windowsMatchBruteForceOnSeededLogs() {
        for (long seed = 1; seed <= 300; seed++) {
            int[] a = FurnaceWatch.log(seed, 1 + (int) (seed % 40), 800, 1 + (int) (seed % 9));
            int k = 1 + (int) (seed % a.length);
            int[] mx = FurnaceWatch.windowMax(a, k);
            int[] mn = FurnaceWatch.windowMin(a, k);
            assertThat(mx).hasSize(a.length - k + 1);
            for (int s = 0; s + k <= a.length; s++) {
                int hi = Integer.MIN_VALUE;
                int lo = Integer.MAX_VALUE;
                for (int i = s; i < s + k; i++) {
                    hi = Math.max(hi, a[i]);
                    lo = Math.min(lo, a[i]);
                }
                assertThat(mx[s]).as("seed %d", seed).isEqualTo(hi);
                assertThat(mn[s]).isEqualTo(lo);
            }
        }
    }

    @Test
    void longestInBandMatchesBruteForce() {
        for (long seed = 1; seed <= 300; seed++) {
            int[] a = FurnaceWatch.log(seed * 3L, 1 + (int) (seed % 35), 800, 1 + (int) (seed % 7));
            int width = (int) (seed % 12);
            int best = 0;
            int bf = 0;
            for (int i = 0; i < a.length; i++) {
                int hi = a[i];
                int lo = a[i];
                for (int j = i; j < a.length; j++) {
                    hi = Math.max(hi, a[j]);
                    lo = Math.min(lo, a[j]);
                    if (hi - lo > width) {
                        break;
                    }
                    if (j - i + 1 > best) {
                        best = j - i + 1;
                        bf = i;
                    }
                }
            }
            Stretch s = FurnaceWatch.longestInBand(a, width);
            assertThat(s.length()).as("seed %d", seed).isEqualTo(best);
            assertThat(s.from()).isEqualTo(bf);
        }
    }

    @Test
    void handWorkedLogAndGrades() {
        int[] a = {1, 3, -1, -3, 5, 3, 6, 7};
        assertThat(FurnaceWatch.windowMax(a, 3)).containsExactly(3, 3, 5, 5, 6, 7);
        assertThat(FurnaceWatch.windowMin(a, 3)).containsExactly(-1, -3, -3, -3, 3, 3);
        assertThat(FurnaceWatch.longestInBand(new int[] {8, 2, 4, 7}, 4)).isEqualTo(new Stretch(1, 2));
        int[] t = {800, 805, 810, 790, 820};
        assertThat(FurnaceWatch.grade(t, new Stretch(0, 2), 795, 815)).isEqualTo(Grade.TEMPERED);
        assertThat(FurnaceWatch.grade(t, new Stretch(2, 4), 780, 815)).isEqualTo(Grade.BRITTLE);
        assertThat(FurnaceWatch.grade(t, new Stretch(1, 3), 795, 815)).isEqualTo(Grade.SOFT);
        assertThat(FurnaceWatch.forgemasterLine(Grade.SOFT)).contains("lead");
    }

    @Test
    void sameSeedReplays() {
        assertThat(FurnaceWatch.log(218L, 50, 800, 5)).isEqualTo(FurnaceWatch.log(218L, 50, 800, 5));
        assertThat(FurnaceWatch.log(219L, 50, 800, 5)).isNotEqualTo(FurnaceWatch.log(218L, 50, 800, 5));
        assertThat(FurnaceWatch.QUEST_ID).isEqualTo("q_furnace_watch");
    }

    @Test
    void edgesAndRejects() {
        assertThat(FurnaceWatch.longestInBand(new int[0], 3)).isNull();
        assertThat(FurnaceWatch.windowMax(new int[] {4}, 1)).containsExactly(4);
        assertThatThrownBy(() -> FurnaceWatch.windowMax(new int[] {1, 2}, 3))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> FurnaceWatch.windowMin(new int[] {1}, 0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> FurnaceWatch.longestInBand(new int[] {1}, -1))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> FurnaceWatch.grade(new int[] {1}, new Stretch(0, 1), 0, 2))
                .isInstanceOf(IllegalArgumentException.class);
    }
}
