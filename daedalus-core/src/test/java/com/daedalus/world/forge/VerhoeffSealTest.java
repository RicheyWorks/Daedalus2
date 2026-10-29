// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class VerhoeffSealTest {

    private static final int[][] PUB_D = {
        {0, 1, 2, 3, 4, 5, 6, 7, 8, 9}, {1, 2, 3, 4, 0, 6, 7, 8, 9, 5}, {2, 3, 4, 0, 1, 7, 8, 9, 5, 6},
        {3, 4, 0, 1, 2, 8, 9, 5, 6, 7}, {4, 0, 1, 2, 3, 9, 5, 6, 7, 8}, {5, 9, 8, 7, 6, 0, 4, 3, 2, 1},
        {6, 5, 9, 8, 7, 1, 0, 4, 3, 2}, {7, 6, 5, 9, 8, 2, 1, 0, 4, 3}, {8, 7, 6, 5, 9, 3, 2, 1, 0, 4},
        {9, 8, 7, 6, 5, 4, 3, 2, 1, 0}};
    private static final int[][] PUB_P = {
        {0, 1, 2, 3, 4, 5, 6, 7, 8, 9}, {1, 5, 7, 6, 2, 8, 3, 0, 9, 4}, {5, 8, 0, 3, 7, 9, 6, 1, 4, 2},
        {8, 9, 1, 6, 0, 4, 3, 5, 2, 7}, {9, 4, 5, 3, 1, 2, 6, 8, 7, 0}, {4, 2, 8, 6, 5, 7, 3, 9, 0, 1},
        {2, 7, 9, 3, 8, 0, 6, 4, 1, 5}, {7, 0, 4, 6, 9, 1, 3, 2, 5, 8}};
    private static final int[] PUB_INV = {0, 4, 3, 2, 1, 5, 6, 7, 8, 9};

    @Test
    void tablesMatchPublished() {
        for (int j = 0; j < 10; j++) {
            for (int k = 0; k < 10; k++) {
                assertThat(VerhoeffSeal.multiply(j, k)).isEqualTo(PUB_D[j][k]);
            }
            assertThat(VerhoeffSeal.inverse(j)).isEqualTo(PUB_INV[j]);
        }
        for (int i = 0; i < 8; i++) {
            for (int k = 0; k < 10; k++) {
                assertThat(VerhoeffSeal.permute(i, k)).isEqualTo(PUB_P[i][k]);
            }
        }
    }

    @Test
    void catchesAllSingleErrorsAndAdjacentSwaps() {
        for (int v = 0; v < 10_000; v++) {
            String s = VerhoeffSeal.seal(String.format("%04d", v));
            assertThat(VerhoeffSeal.isValid(s)).isTrue();
            char[] c = s.toCharArray();
            for (int i = 0; i < c.length; i++) {
                char orig = c[i];
                for (char d = '0'; d <= '9'; d++) {
                    if (d != orig) {
                        c[i] = d;
                        assertThat(VerhoeffSeal.isValid(new String(c))).isFalse();
                    }
                }
                c[i] = orig;
                if (i + 1 < c.length && c[i] != c[i + 1]) {
                    char t = c[i];
                    c[i] = c[i + 1];
                    c[i + 1] = t;
                    assertThat(VerhoeffSeal.isValid(new String(c))).isFalse();
                    c[i + 1] = c[i];
                    c[i] = t;
                }
            }
        }
        assertThat(VerhoeffSeal.seal("236")).isEqualTo("2363");
        assertThat(VerhoeffSeal.checkDigit("12345")).isEqualTo(1);
    }

    @Test
    void grades() {
        assertThat(VerhoeffSeal.grade("2363")).isEqualTo(VerhoeffSeal.Grade.SEALED);
        assertThat(VerhoeffSeal.grade("2364")).isEqualTo(VerhoeffSeal.Grade.TAMPERED);
        assertThat(VerhoeffSeal.grade("")).isEqualTo(VerhoeffSeal.Grade.TAMPERED);
        assertThat(VerhoeffSeal.forgemasterLine(VerhoeffSeal.Grade.SEALED)).contains("Forgemaster");
        assertThat(VerhoeffSeal.forgemasterLine(VerhoeffSeal.Grade.TAMPERED)).contains("tampered");
        assertThat(VerhoeffSeal.QUEST_ID).isEqualTo("q_verhoeff_seal");
    }
}
