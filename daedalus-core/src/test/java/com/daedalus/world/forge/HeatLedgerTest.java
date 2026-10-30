// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.HeatLedger.Grade;
import org.junit.jupiter.api.Test;

import java.util.SplittableRandom;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class HeatLedgerTest {

    @Test
    void matchesNaiveReplayOnSeededShifts() {
        for (long seed = 0; seed < 150; seed++) {
            int n = 1 + (int) (seed % 33);
            long[] naive = new long[n];
            SplittableRandom r = new SplittableRandom(seed ^ 0x5eedL);
            for (int i = 0; i < n; i++) {
                naive[i] = r.nextInt(100);
            }
            HeatLedger led = new HeatLedger(naive);
            for (long[] b : HeatLedger.blasts(seed, n, 60, 20)) {
                int from = (int) b[0];
                int to = (int) b[1];
                led.add(from, to, b[2]);
                for (int i = from; i <= to; i++) {
                    naive[i] += b[2];
                }
                int qa = r.nextInt(n);
                int qb = r.nextInt(n);
                int lo = Math.min(qa, qb);
                int hi = Math.max(qa, qb);
                long s = 0;
                long m = Long.MIN_VALUE;
                for (int i = lo; i <= hi; i++) {
                    s += naive[i];
                    m = Math.max(m, naive[i]);
                }
                assertThat(led.sum(lo, hi)).as("seed %d", seed).isEqualTo(s);
                assertThat(led.max(lo, hi)).as("seed %d", seed).isEqualTo(m);
            }
        }
    }

    @Test
    void knownRowAndBadSpans() {
        HeatLedger led = new HeatLedger(new long[] {1, 2, 3, 4});
        led.add(1, 2, 10);
        assertThat(led.sum(0, 3)).isEqualTo(30);
        assertThat(led.max(0, 3)).isEqualTo(13);
        led.add(0, 3, -5);
        assertThat(led.sum(3, 3)).isEqualTo(-1);
        assertThat(led.max(0, 0)).isEqualTo(-4);
        assertThatThrownBy(() -> led.sum(2, 1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> led.add(0, 4, 1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new HeatLedger(new long[0]).max(0, 0)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void gradesLinesAndReplay() {
        HeatLedger led = new HeatLedger(new long[] {5, 5});
        assertThat(led.grade(0, 1, 10)).isEqualTo(Grade.BALANCED);
        assertThat(led.grade(0, 1, 11)).isEqualTo(Grade.SMUDGED);
        for (Grade g : Grade.values()) {
            assertThat(HeatLedger.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(HeatLedger.QUEST_ID).isEqualTo("q_heat_ledger");
        assertThat(HeatLedger.blasts(4, 10, 12, 7)).isDeepEqualTo(HeatLedger.blasts(4, 10, 12, 7)).hasNumberOfRows(12);
        assertThatThrownBy(() -> HeatLedger.blasts(1, 0, 1, 1)).isInstanceOf(IllegalArgumentException.class);
    }
}
