// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.Random;
import org.junit.jupiter.api.Test;

class FrobeniusFittingsTest {

    @Test
    void matchesBruteForceKnapsack() {
        Random r = new Random(439);
        int lim = 6000;
        for (int t = 0; t < 300; t++) {
            int k = 1 + r.nextInt(5);
            long[] packs = new long[k];
            for (int i = 0; i < k; i++) {
                packs[i] = 2 + r.nextInt(40);
            }
            boolean[] ok = new boolean[lim + 1];
            ok[0] = true;
            for (int n = 1; n <= lim; n++) {
                for (long p : packs) {
                    if (n >= p && ok[(int) (n - p)]) {
                        ok[n] = true;
                        break;
                    }
                }
            }
            long g = 0;
            for (long p : packs) {
                g = FrobeniusFittings.gcd(g, p);
            }
            long last = -1;
            long gaps = 0;
            for (int n = 1; n <= lim; n++) {
                if (!ok[n]) {
                    last = n;
                    gaps++;
                }
                assertThat(FrobeniusFittings.representable(packs, n)).isEqualTo(ok[n]);
            }
            if (g == 1) {
                assertThat(FrobeniusFittings.frobenius(packs)).isEqualTo(last);
                assertThat(FrobeniusFittings.countGaps(packs)).isEqualTo(gaps);
            } else {
                assertThat(FrobeniusFittings.frobenius(packs)).isEqualTo(Long.MAX_VALUE);
                assertThat(FrobeniusFittings.countGaps(packs)).isEqualTo(Long.MAX_VALUE);
            }
        }
    }

    @Test
    void twoPackFormulasAtScale() {
        assertThat(FrobeniusFittings.frobenius(new long[] {6, 9, 20})).isEqualTo(43);
        assertThat(FrobeniusFittings.frobenius(new long[] {1, 5})).isEqualTo(-1);
        Random r = new Random(4390);
        for (int t = 0; t < 30; t++) {
            long a = 2 + r.nextInt(FrobeniusFittings.MAX_PACK - 1);
            long b = a + 1 + r.nextInt(1_000_000_000 - (int) a);
            if (FrobeniusFittings.gcd(a, b) != 1) {
                continue;
            }
            assertThat(FrobeniusFittings.frobenius(new long[] {b, a})).isEqualTo(a * b - a - b);
            assertThat(FrobeniusFittings.countGaps(new long[] {a, b})).isEqualTo((a - 1) * (b - 1) / 2);
        }
    }

    @Test
    void gradesAndLines() {
        assertThat(FrobeniusFittings.grade(new long[] {6, 9, 20}, 43)).isEqualTo(FrobeniusFittings.Grade.TURNED);
        assertThat(FrobeniusFittings.grade(new long[] {6, 9, 20}, 44)).isEqualTo(FrobeniusFittings.Grade.SLIPPED);
        for (FrobeniusFittings.Grade g : FrobeniusFittings.Grade.values()) {
            assertThat(FrobeniusFittings.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(FrobeniusFittings.QUEST_ID).isEqualTo("q_frobenius_fittings");
    }
}
