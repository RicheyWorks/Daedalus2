// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;
import org.junit.jupiter.api.Test;

class EmirpEmbersTest {

    private static boolean trial(long v) {
        if (v < 2) {
            return false;
        }
        for (long d = 2; d * d <= v; d++) {
            if (v % d == 0) {
                return false;
            }
        }
        return true;
    }

    private static long revString(long n) {
        return Long.parseLong(new StringBuilder(Long.toString(n)).reverse().toString());
    }

    @Test
    void matchesTrialDivisionAndSieve() {
        List<Long> want = new ArrayList<>();
        for (long n = 1; n <= 200_000; n++) {
            long r = revString(n);
            boolean e = r != n && trial(n) && trial(r);
            assertThat(EmirpEmbers.reverse(n)).isEqualTo(r);
            assertThat(EmirpEmbers.isEmirp(n)).as("%d", n).isEqualTo(e);
            if (e) {
                want.add(n);
            }
        }
        assertThat(EmirpEmbers.emirpsUpTo(200_000)).isEqualTo(want);
        Random r = new Random(507);
        for (int t = 0; t < 25; t++) {
            int x = r.nextInt(200_000);
            List<Long> part = new ArrayList<>();
            for (long v : want) {
                if (v <= x) {
                    part.add(v);
                }
            }
            assertThat(EmirpEmbers.emirpsUpTo(x)).isEqualTo(part);
        }
    }

    @Test
    void pairSymmetryAndRoundTrips() {
        for (long n = 1; n <= 100_000; n++) {
            if (n % 10 != 0) {
                assertThat(EmirpEmbers.reverse(EmirpEmbers.reverse(n))).isEqualTo(n);
            }
            if (EmirpEmbers.isEmirp(n)) {
                assertThat(EmirpEmbers.isEmirp(EmirpEmbers.reverse(n))).as("%d", n).isTrue();
            }
        }
        assertThat(EmirpEmbers.reverse(120)).isEqualTo(21);
        assertThat(EmirpEmbers.reverse(EmirpEmbers.MAX_N)).isEqualTo(EmirpEmbers.MAX_N);
    }

    @Test
    void knownEmbers() {
        assertThat(EmirpEmbers.emirpsUpTo(400)).containsExactly(13L, 17L, 31L, 37L, 71L, 73L, 79L, 97L, 107L, 113L,
                149L, 157L, 167L, 179L, 199L, 311L, 337L, 347L, 359L, 389L);
        assertThat(EmirpEmbers.isEmirp(11)).isFalse();
        assertThat(EmirpEmbers.isEmirp(101)).isFalse();
        assertThat(EmirpEmbers.isEmirp(19)).isFalse();
        assertThat(EmirpEmbers.isEmirp(1_000_003L)).isEqualTo(trial(3_000_001L));
    }

    @Test
    void randomLargeSweeps() {
        Random r = new Random(5071);
        for (int t = 0; t < 2000; t++) {
            long n = 1 + (r.nextLong() >>> 1) % 1_000_000_000_000L;
            long rv = revString(n);
            assertThat(EmirpEmbers.isEmirp(n)).as("%d", n)
                    .isEqualTo(rv != n && PrimorialPyres.isPrime(n) && trial(n) == PrimorialPyres.isPrime(n)
                            && PrimorialPyres.isPrime(rv));
        }
        long big = 1_000_000_000_000_000_003L % EmirpEmbers.MAX_N;
        assertThat(EmirpEmbers.isEmirp(big)).isEqualTo(
                PrimorialPyres.isPrime(big) && PrimorialPyres.isPrime(revString(big)) && revString(big) != big);
    }

    @Test
    void edgesGuardsAndGrades() {
        assertThat(EmirpEmbers.isEmirp(1)).isFalse();
        assertThat(EmirpEmbers.isEmirp(2)).isFalse();
        assertThat(EmirpEmbers.emirpsUpTo(0)).isEmpty();
        assertThat(EmirpEmbers.emirpsUpTo(12)).isEmpty();
        assertThat(EmirpEmbers.emirpsUpTo(13)).containsExactly(13L);
        assertThat(EmirpEmbers.emirpsUpTo(EmirpEmbers.SIEVE_MAX)).isNotEmpty();
        assertThatThrownBy(() -> EmirpEmbers.reverse(0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> EmirpEmbers.isEmirp(EmirpEmbers.MAX_N + 1))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> EmirpEmbers.emirpsUpTo(-1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> EmirpEmbers.emirpsUpTo(EmirpEmbers.SIEVE_MAX + 1))
                .isInstanceOf(IllegalArgumentException.class);
        assertThat(EmirpEmbers.grade(13, true)).isEqualTo(EmirpEmbers.Grade.TURNED);
        assertThat(EmirpEmbers.grade(11, true)).isEqualTo(EmirpEmbers.Grade.SLIPPED);
        assertThat(EmirpEmbers.grade(11, false)).isEqualTo(EmirpEmbers.Grade.TURNED);
        for (EmirpEmbers.Grade g : EmirpEmbers.Grade.values()) {
            assertThat(EmirpEmbers.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(EmirpEmbers.QUEST_ID).isEqualTo("q_emirp_embers");
    }
}
