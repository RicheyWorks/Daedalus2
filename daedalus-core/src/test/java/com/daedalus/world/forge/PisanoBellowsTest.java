// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class PisanoBellowsTest {

    private static long brute(long m) {
        long a = 0;
        long b = 1 % m;
        long t = 0;
        do {
            long c = (a + b) % m;
            a = b;
            b = c;
            t++;
        } while (!(a == 0 && b == 1 % m));
        return t;
    }

    @Test
    void matchesBruteForce() {
        for (long m = 1; m <= 2000; m++) {
            assertThat(PisanoBellows.period(m)).as("m=%d", m).isEqualTo(brute(m));
        }
        long a = 0;
        long b = 1;
        for (int n = 0; n < 500; n++) {
            assertThat(PisanoBellows.fibMod(n, 1_000_003)).isEqualTo(a);
            long c = (a + b) % 1_000_003;
            a = b;
            b = c;
        }
        for (long s = 0; s < 40; s++) {
            long m = PisanoBellows.bellows(s);
            long p = PisanoBellows.period(m);
            assertThat(PisanoBellows.isPeriod(p, m)).isTrue();
            for (long r = 2; r <= 50; r++) {
                if (p % r == 0) {
                    assertThat(PisanoBellows.isPeriod(p / r, m)).isFalse();
                }
            }
        }
    }

    @Test
    void knownValues() {
        assertThat(PisanoBellows.period(2)).isEqualTo(3);
        assertThat(PisanoBellows.period(5)).isEqualTo(20);
        assertThat(PisanoBellows.period(10)).isEqualTo(60);
        assertThat(PisanoBellows.period(1_000_000_000L)).isEqualTo(1_500_000_000L);
        long f90 = 2_880_067_194_370_816_120L;
        assertThat(PisanoBellows.fibMod(90, Integer.MAX_VALUE)).isEqualTo(f90 % Integer.MAX_VALUE);
    }

    @Test
    void grades() {
        assertThat(PisanoBellows.grade(10, 60)).isEqualTo(PisanoBellows.Grade.TRUE);
        assertThat(PisanoBellows.grade(10, 120)).isEqualTo(PisanoBellows.Grade.OFFBEAT);
        assertThat(PisanoBellows.forgemasterLine(PisanoBellows.Grade.TRUE)).contains("Forgemaster");
        assertThat(PisanoBellows.forgemasterLine(PisanoBellows.Grade.OFFBEAT)).contains("offbeat");
        assertThat(PisanoBellows.QUEST_ID).isEqualTo("q_pisano_bellows");
    }
}
