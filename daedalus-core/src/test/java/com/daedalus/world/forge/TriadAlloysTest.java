// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;
import org.junit.jupiter.api.Test;

class TriadAlloysTest {

    private static boolean brute(long n) {
        List<Long> f = new ArrayList<>();
        long m = n;
        for (long d = 2; d * d <= m; d++) {
            while (m % d == 0) {
                f.add(d);
                m /= d;
            }
        }
        if (m > 1) {
            f.add(m);
        }
        return f.size() == 3 && !f.get(0).equals(f.get(1)) && !f.get(1).equals(f.get(2));
    }

    @Test
    void matchesTrialDivisionBruteForce() {
        long run = 0;
        for (int n = 1; n <= 100_000; n++) {
            boolean b = brute(n);
            assertThat(TriadAlloys.isSphenic(n)).as("n=%d", n).isEqualTo(b);
            if (b) {
                run++;
                long[] o = TriadAlloys.ores(n);
                assertThat(o[0] * o[1] * o[2]).isEqualTo(n);
                assertThat(o[0]).isLessThan(o[1]);
                assertThat(o[1]).isLessThan(o[2]);
            }
            if (n % 911 == 0 || n < 120) {
                assertThat(TriadAlloys.countSphenic(n)).isEqualTo(run);
            }
        }
    }

    @Test
    void knownTriadsAndRuns() {
        List<Long> first = new ArrayList<>();
        for (long n = 1; first.size() < 20; n++) {
            if (TriadAlloys.isSphenic(n)) {
                first.add(n);
            }
        }
        assertThat(first).containsExactly(30L, 42L, 66L, 70L, 78L, 102L, 105L, 110L, 114L, 130L, 138L, 154L, 165L,
                170L, 174L, 182L, 186L, 190L, 195L, 222L);
        assertThat(TriadAlloys.firstRun(2, 10_000)).isEqualTo(230);
        assertThat(TriadAlloys.firstRun(3, 10_000)).isEqualTo(1309);
        assertThat(TriadAlloys.firstRun(4, 100_000)).isEqualTo(-1);
        assertThat(TriadAlloys.ores(30)).containsExactly(2, 3, 5);
    }

    @Test
    void sieveAgreesWithChecksOnRandomWindows() {
        Random r = new Random(494);
        for (int t = 0; t < 6; t++) {
            int lo = 100_000 + r.nextInt(5_000_000);
            int hi = lo + r.nextInt(3000);
            long c = TriadAlloys.countSphenic(lo);
            for (long n = lo + 1; n <= hi; n++) {
                c += TriadAlloys.isSphenic(n) ? 1 : 0;
            }
            assertThat(TriadAlloys.countSphenic(hi)).isEqualTo(c);
        }
        for (int t = 0; t < 200; t++) {
            long n = 1 + (long) (r.nextDouble() * 1e9);
            assertThat(TriadAlloys.isSphenic(n)).as("n=%d", n).isEqualTo(brute(n));
        }
    }

    @Test
    void edgesAndGuards() {
        assertThat(TriadAlloys.isSphenic(1)).isFalse();
        assertThat(TriadAlloys.isSphenic(60)).isFalse();
        assertThat(TriadAlloys.isSphenic(210)).isFalse();
        assertThat(TriadAlloys.isSphenic(6_000_018L)).isTrue();
        assertThat(TriadAlloys.ores(6_000_018L)).containsExactly(2, 3, 1_000_003);
        assertThat(TriadAlloys.isSphenic(TriadAlloys.MAX_N)).isFalse();
        assertThat(TriadAlloys.countSphenic(0)).isZero();
        assertThat(TriadAlloys.countSphenic(29)).isZero();
        assertThatThrownBy(() -> TriadAlloys.ores(0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> TriadAlloys.isSphenic(TriadAlloys.MAX_N + 1))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> TriadAlloys.countSphenic(-1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> TriadAlloys.firstRun(0, 10)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void gradesAndLines() {
        assertThat(TriadAlloys.grade(30, true)).isEqualTo(TriadAlloys.Grade.TURNED);
        assertThat(TriadAlloys.grade(60, true)).isEqualTo(TriadAlloys.Grade.SLIPPED);
        assertThat(TriadAlloys.grade(60, false)).isEqualTo(TriadAlloys.Grade.TURNED);
        for (TriadAlloys.Grade g : TriadAlloys.Grade.values()) {
            assertThat(TriadAlloys.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(TriadAlloys.QUEST_ID).isEqualTo("q_triad_alloys");
    }
}
