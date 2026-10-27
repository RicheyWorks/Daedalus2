// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.DamperPact.Grade;
import org.junit.jupiter.api.Test;

import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class DamperPactTest {

    @Test
    void matchesBruteForceOnSeededRuleSets() {
        int sat = 0;
        for (long seed = 0; seed < 400; seed++) {
            int n = 1 + (int) (seed % 8);
            int[][] cl = DamperPact.rules(seed, n, (int) (seed % 20));
            boolean truth = false;
            for (int mask = 0; mask < (1 << n) && !truth; mask++) {
                boolean[] o = new boolean[n];
                for (int i = 0; i < n; i++) {
                    o[i] = ((mask >> i) & 1) == 1;
                }
                truth = DamperPact.honours(o, cl);
            }
            Optional<boolean[]> got = DamperPact.solve(n, cl);
            assertThat(got.isPresent()).as("seed %d", seed).isEqualTo(truth);
            if (truth) {
                sat++;
                assertThat(DamperPact.honours(got.get(), cl)).as("seed %d honours", seed).isTrue();
                assertThat(DamperPact.grade(n, cl, got.get())).isEqualTo(Grade.HONOURED);
            } else {
                assertThat(DamperPact.grade(n, cl, null)).isEqualTo(Grade.HONOURED);
            }
        }
        assertThat(sat).isBetween(50, 399);
    }

    @Test
    void knownPacts() {
        assertThat(DamperPact.solve(1, new int[][] {{1, 1}, {-1, -1}})).isEmpty();
        assertThat(DamperPact.solve(2, new int[][] {{1, 2}, {-1, 2}, {-2, 1}}))
                .hasValueSatisfying(o -> assertThat(o).containsExactly(true, true));
        assertThat(DamperPact.solve(3, new int[0][])).hasValueSatisfying(o -> assertThat(o).hasSize(3));
        assertThatThrownBy(() -> DamperPact.solve(2, new int[][] {{0, 1}}))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> DamperPact.solve(2, new int[][] {{3, 1}}))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void gradesLinesAndReplay() {
        int[][] cl = {{1, 2}, {-1, -2}};
        assertThat(DamperPact.grade(2, cl, new boolean[] {true, false})).isEqualTo(Grade.HONOURED);
        assertThat(DamperPact.grade(2, cl, new boolean[] {true, true})).isEqualTo(Grade.BROKEN);
        assertThat(DamperPact.grade(2, cl, null)).isEqualTo(Grade.BROKEN);
        assertThat(DamperPact.grade(2, cl, new boolean[] {true})).isEqualTo(Grade.BROKEN);
        for (Grade g : Grade.values()) {
            assertThat(DamperPact.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(DamperPact.QUEST_ID).isEqualTo("q_damper_pact");
        assertThat(DamperPact.rules(6, 4, 5)).isDeepEqualTo(DamperPact.rules(6, 4, 5));
        assertThatThrownBy(() -> DamperPact.rules(1, 0, 2)).isInstanceOf(IllegalArgumentException.class);
    }
}
