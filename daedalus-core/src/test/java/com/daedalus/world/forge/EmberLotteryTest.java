// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.EmberLottery.Grade;
import org.junit.jupiter.api.Test;

import java.util.SplittableRandom;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;

class EmberLotteryTest {

    @Test
    void tableReproducesExactOddsOnSeededWeights() {
        SplittableRandom r = new SplittableRandom(17);
        for (int c = 0; c < 300; c++) {
            int n = 1 + c % 12;
            double[] w = new double[n];
            double total = 0;
            for (int i = 0; i < n; i++) {
                w[i] = r.nextInt(4) == 0 ? 0 : r.nextDouble() * 10;
                total += w[i];
            }
            if (total <= 0) {
                w[0] = 1;
                total = 1;
            }
            EmberLottery lot = new EmberLottery(w);
            double sum = 0;
            for (int i = 0; i < n; i++) {
                assertThat(lot.probability(i)).as("case %d outcome %d", c, i).isCloseTo(w[i] / total, within(1e-9));
                sum += lot.probability(i);
            }
            assertThat(sum).isCloseTo(1.0, within(1e-9));
        }
    }

    @Test
    void seededDrawsFollowTheOddsAndReplay() {
        double[] w = {50, 30, 15, 4, 1, 0};
        EmberLottery lot = new EmberLottery(w);
        int[] d = lot.draws(2026, 200_000);
        int[] hits = new int[w.length];
        for (int x : d) {
            hits[x]++;
        }
        for (int i = 0; i < w.length; i++) {
            assertThat(hits[i] / 200_000.0).as("outcome %d", i).isCloseTo(w[i] / 100, within(0.005));
        }
        assertThat(hits[5]).isZero();
        assertThat(lot.draws(7, 50)).isEqualTo(lot.draws(7, 50));
        assertThat(new EmberLottery(new double[] {3}).draws(1, 10)).containsOnly(0);
    }

    @Test
    void badInputGradesAndLines() {
        assertThatThrownBy(() -> new EmberLottery(new double[0])).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new EmberLottery(new double[] {0, 0})).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new EmberLottery(new double[] {-1, 2})).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new EmberLottery(new double[] {Double.NaN}))
                .isInstanceOf(IllegalArgumentException.class);
        EmberLottery lot = new EmberLottery(new double[] {1, 3});
        assertThat(lot.size()).isEqualTo(2);
        assertThatThrownBy(() -> lot.probability(2)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> lot.draws(1, -1)).isInstanceOf(IllegalArgumentException.class);
        assertThat(lot.grade(1, 0.75)).isEqualTo(Grade.FAIR);
        assertThat(lot.grade(1, 0.5)).isEqualTo(Grade.RIGGED);
        for (Grade g : Grade.values()) {
            assertThat(EmberLottery.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(EmberLottery.QUEST_ID).isEqualTo("q_ember_lottery");
    }
}
