// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;
import org.junit.jupiter.api.Test;

class RecordIngotsTest {

    private static long trialDivisors(long n) {
        long c = 0;
        for (long d = 1; d * d <= n; d++) {
            if (n % d == 0) {
                c += d * d == n ? 1 : 2;
            }
        }
        return c;
    }

    @Test
    void recordsMatchDivisorSieveBruteForce() {
        int n = 200_000;
        int[] d = new int[n + 1];
        for (int i = 1; i <= n; i++) {
            for (int j = i; j <= n; j += i) {
                d[j]++;
            }
        }
        List<Long> want = new ArrayList<>();
        int best = 0;
        for (int i = 1; i <= n; i++) {
            assertThat(RecordIngots.divisorCount(i)).as("d(%d)", i).isEqualTo(d[i]);
            if (d[i] > best) {
                best = d[i];
                want.add((long) i);
            }
            if (i < 3000 || i % 997 == 0) {
                assertThat(RecordIngots.isRecord(i)).as("n=%d", i).isEqualTo(want.get(want.size() - 1) == i);
            }
        }
        assertThat(RecordIngots.recordsUpTo(n)).isEqualTo(want);
    }

    @Test
    void knownRecordIngots() {
        assertThat(RecordIngots.recordsUpTo(720_720)).containsExactly(1L, 2L, 4L, 6L, 12L, 24L, 36L, 48L, 60L, 120L,
                180L, 240L, 360L, 720L, 840L, 1260L, 1680L, 2520L, 5040L, 7560L, 10080L, 15120L, 20160L, 25200L,
                27720L, 45360L, 50400L, 55440L, 83160L, 110880L, 166320L, 221760L, 277200L, 332640L, 498960L,
                554400L, 665280L, 720720L);
        assertThat(RecordIngots.isRecord(963_761_198_400L)).isTrue();
        assertThat(RecordIngots.divisorCount(963_761_198_400L)).isEqualTo(6720);
        assertThat(RecordIngots.isRecord(963_761_198_401L)).isFalse();
    }

    @Test
    void divisorCountsAgreeWithTrialDivisionOnRandomSweeps() {
        Random r = new Random(475);
        for (int t = 0; t < 300; t++) {
            long n = 1 + (long) (r.nextDouble() * 9_999_999_999L);
            assertThat(RecordIngots.divisorCount(n)).as("n=%d", n).isEqualTo(trialDivisors(n));
        }
        List<Long> rec = RecordIngots.recordsUpTo(RecordIngots.MAX_N);
        long prev = 0;
        for (long x : rec) {
            long dx = RecordIngots.divisorCount(x);
            assertThat(dx).as("record %d", x).isGreaterThan(prev);
            prev = dx;
            if (x > 2) {
                assertThat(RecordIngots.isRecord(x - 1)).isFalse();
            }
        }
        assertThat(rec.get(rec.size() - 1)).isEqualTo(963_761_198_400L);
    }

    @Test
    void edgesAndGuards() {
        assertThat(RecordIngots.recordsUpTo(0)).isEmpty();
        assertThat(RecordIngots.recordsUpTo(1)).containsExactly(1L);
        assertThat(RecordIngots.recordsUpTo(5)).containsExactly(1L, 2L, 4L);
        assertThat(RecordIngots.divisorCount(1)).isEqualTo(1);
        assertThat(RecordIngots.divisorCount(999_999_999_989L)).isEqualTo(2);
        assertThat(RecordIngots.divisorCount(RecordIngots.MAX_N)).isEqualTo(169);
        assertThat(RecordIngots.isRecord(3)).isFalse();
        assertThatThrownBy(() -> RecordIngots.divisorCount(0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> RecordIngots.isRecord(RecordIngots.MAX_N + 1))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> RecordIngots.recordsUpTo(-1)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void gradesAndLines() {
        assertThat(RecordIngots.grade(12, true)).isEqualTo(RecordIngots.Grade.TURNED);
        assertThat(RecordIngots.grade(18, true)).isEqualTo(RecordIngots.Grade.SLIPPED);
        assertThat(RecordIngots.grade(18, false)).isEqualTo(RecordIngots.Grade.TURNED);
        for (RecordIngots.Grade g : RecordIngots.Grade.values()) {
            assertThat(RecordIngots.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(RecordIngots.QUEST_ID).isEqualTo("q_record_ingots");
    }
}
