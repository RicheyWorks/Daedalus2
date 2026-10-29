// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.Random;
import org.junit.jupiter.api.Test;

class VanEckEchoesTest {

    private static int[] brute(int len) {
        int[] a = new int[len];
        for (int n = 0; n + 1 < len; n++) {
            int nx = 0;
            for (int m = n - 1; m >= 0; m--) {
                if (a[m] == a[n]) {
                    nx = n - m;
                    break;
                }
            }
            a[n + 1] = nx;
        }
        return a;
    }

    @Test
    void matchesBackwardScan() {
        int[] b = brute(6000);
        assertThat(VanEckEchoes.sequence(6000)).isEqualTo(b);
        Random r = new Random(518);
        for (int t = 0; t < 40; t++) {
            int len = r.nextInt(6000);
            int[] s = VanEckEchoes.sequence(len);
            for (int i = 0; i < len; i++) {
                assertThat(s[i]).isEqualTo(b[i]);
            }
        }
    }

    @Test
    void knownEchoes() {
        assertThat(VanEckEchoes.sequence(32)).containsExactly(0, 0, 1, 0, 2, 0, 2, 2, 1, 6, 0, 5, 0, 2, 6, 5, 4, 0, 5,
                3, 0, 3, 2, 9, 0, 4, 9, 3, 6, 14, 0, 6);
        assertThat(VanEckEchoes.term(9)).isEqualTo(6);
        assertThat(VanEckEchoes.firstOccurrence(6, 100)).isEqualTo(9);
        assertThat(VanEckEchoes.firstOccurrence(14, 100)).isEqualTo(29);
        assertThat(VanEckEchoes.zeroCount(32)).isEqualTo(10);
    }

    @Test
    void structuralRules() {
        int[] a = VanEckEchoes.sequence(200_000);
        boolean[] seen = new boolean[200_000];
        for (int n = 0; n + 1 < a.length; n++) {
            assertThat(a[n + 1]).isLessThanOrEqualTo(n);
            assertThat(a[n + 1] == 0).as("n=%d", n).isEqualTo(!seen[a[n]]);
            seen[a[n]] = true;
            if (a[n + 1] > 0) {
                assertThat(a[n - a[n + 1]]).isEqualTo(a[n]);
            }
        }
    }

    @Test
    void firstOccurrencesMatchScan() {
        int[] b = brute(4000);
        for (int v = 0; v < 60; v++) {
            int want = -1;
            for (int i = 0; i < b.length; i++) {
                if (b[i] == v) {
                    want = i;
                    break;
                }
            }
            assertThat(VanEckEchoes.firstOccurrence(v, 4000)).as("v=%d", v).isEqualTo(want);
        }
        assertThat(VanEckEchoes.firstOccurrence(5000, 4000)).isEqualTo(-1);
    }

    @Test
    void edgesGuardsAndGrades() {
        assertThat(VanEckEchoes.sequence(0)).isEmpty();
        assertThat(VanEckEchoes.sequence(1)).containsExactly(0);
        assertThat(VanEckEchoes.zeroCount(0)).isZero();
        assertThat(VanEckEchoes.term(0)).isZero();
        assertThat(VanEckEchoes.sequence(VanEckEchoes.MAX_LEN)).hasSize(VanEckEchoes.MAX_LEN);
        assertThatThrownBy(() -> VanEckEchoes.sequence(-1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> VanEckEchoes.sequence(VanEckEchoes.MAX_LEN + 1))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> VanEckEchoes.term(VanEckEchoes.MAX_LEN)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> VanEckEchoes.firstOccurrence(-1, 10)).isInstanceOf(IllegalArgumentException.class);
        assertThat(VanEckEchoes.grade(9, 6)).isEqualTo(VanEckEchoes.Grade.TURNED);
        assertThat(VanEckEchoes.grade(9, 5)).isEqualTo(VanEckEchoes.Grade.SLIPPED);
        for (VanEckEchoes.Grade g : VanEckEchoes.Grade.values()) {
            assertThat(VanEckEchoes.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(VanEckEchoes.QUEST_ID).isEqualTo("q_van_eck_echoes");
    }
}
