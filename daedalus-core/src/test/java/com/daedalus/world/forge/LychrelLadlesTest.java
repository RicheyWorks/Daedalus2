// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.math.BigInteger;
import java.util.Random;
import org.junit.jupiter.api.Test;

class LychrelLadlesTest {

    private static int brutePours(long n, int limit) {
        String s = Long.toString(n);
        for (int k = 0; k <= limit; k++) {
            if (new StringBuilder(s).reverse().toString().equals(s)) {
                return k;
            }
            if (k == limit) {
                break;
            }
            s = new BigInteger(s).add(new BigInteger(new StringBuilder(s).reverse().toString())).toString();
        }
        return -1;
    }

    @Test
    void matchesStringBruteForce() {
        for (long n = 1; n <= 20_000; n++) {
            assertThat(LychrelLadles.pours(n, 120)).as("%d", n).isEqualTo(brutePours(n, 120));
        }
        Random r = new Random(514);
        for (int t = 0; t < 300; t++) {
            long n = 1 + (r.nextLong() >>> 1) % LychrelLadles.MAX_N;
            int lim = r.nextInt(80);
            assertThat(LychrelLadles.pours(n, lim)).as("%d/%d", n, lim).isEqualTo(brutePours(n, lim));
        }
    }

    @Test
    void knownPourCounts() {
        assertThat(LychrelLadles.pours(89)).isEqualTo(24);
        assertThat(LychrelLadles.pours(10_911)).isEqualTo(55);
        assertThat(LychrelLadles.pours(1_186_060_307_891_929_990L)).isEqualTo(261);
        assertThat(LychrelLadles.pours(56)).isEqualTo(1);
        assertThat(LychrelLadles.melt(56, 1)).isEqualTo(BigInteger.valueOf(121));
        assertThat(LychrelLadles.pours(89, 23)).isEqualTo(-1);
        assertThat(LychrelLadles.melt(89, 24).toString()).isEqualTo("8813200023188");
    }

    @Test
    void knownCandidatesAndSeeds() {
        assertThat(LychrelLadles.candidatesUpTo(1000)).containsExactly(196L, 295L, 394L, 493L, 592L, 689L, 691L,
                788L, 790L, 879L, 887L, 978L, 986L);
        assertThat(LychrelLadles.seed(196)).isEqualTo(196);
        assertThat(LychrelLadles.seed(887)).isEqualTo(196);
        assertThat(LychrelLadles.seed(1675)).isEqualTo(196);
        for (int n = 1; n <= 3000; n++) {
            long s = LychrelLadles.seed(n);
            assertThat(s).isBetween(1L, (long) n);
            if (s < n) {
                boolean hit = false;
                for (int k = 1; k <= 20 && !hit; k++) {
                    hit = LychrelLadles.melt(s, k).equals(BigInteger.valueOf(n));
                }
                assertThat(hit).as("seed %d of %d", s, n).isTrue();
            }
        }
    }

    @Test
    void palindromesAndEdges() {
        for (long p : new long[] {1, 9, 11, 121, 4994, 1_234_554_321L, LychrelLadles.MAX_N - 1}) {
            if (new StringBuilder(Long.toString(p)).reverse().toString().equals(Long.toString(p))) {
                assertThat(LychrelLadles.pours(p)).isZero();
            }
        }
        assertThat(LychrelLadles.pours(196, 0)).isEqualTo(-1);
        assertThat(LychrelLadles.pours(1, 0)).isZero();
        assertThat(LychrelLadles.candidatesUpTo(0)).isEmpty();
        assertThat(LychrelLadles.candidatesUpTo(195)).isEmpty();
        assertThatThrownBy(() -> LychrelLadles.pours(0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> LychrelLadles.pours(-5))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> LychrelLadles.pours(5, -1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> LychrelLadles.pours(5, LychrelLadles.MAX_LIMIT + 1))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> LychrelLadles.candidatesUpTo(LychrelLadles.SCAN_MAX + 1))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> LychrelLadles.seed(0)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void gradesAndLines() {
        assertThat(LychrelLadles.grade(196, true)).isEqualTo(LychrelLadles.Grade.TURNED);
        assertThat(LychrelLadles.grade(89, true)).isEqualTo(LychrelLadles.Grade.SLIPPED);
        assertThat(LychrelLadles.grade(89, false)).isEqualTo(LychrelLadles.Grade.TURNED);
        for (LychrelLadles.Grade g : LychrelLadles.Grade.values()) {
            assertThat(LychrelLadles.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(LychrelLadles.QUEST_ID).isEqualTo("q_lychrel_ladles");
    }
}
