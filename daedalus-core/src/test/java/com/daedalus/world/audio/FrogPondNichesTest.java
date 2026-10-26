// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import org.junit.jupiter.api.Test;

class FrogPondNichesTest {
    @Test void everyWetlandHasAValidAssignment() {
        for (long s = 0; s < 300; s++) {
            FrogPondNiches w = FrogPondNiches.seeded(s);
            assertThat(w.frogs().size()).isBetween(5, 7);
            List<Integer> sol = w.solution();
            assertThat(sol).isNotNull();
            assertThat(w.judge(sol).ok()).as("seed %d", s).isTrue();
            assertThat(w.seed()).isEqualTo(s);
        }
    }

    @Test void biggerFrogsCallLower() {
        assertThat(FrogPondNiches.dominantHz(150)).isLessThan(FrogPondNiches.dominantHz(20));
        assertThat(FrogPondNiches.dominantHz(100)).isCloseTo(240.0, within(1e-9));
        assertThat(FrogPondNiches.dominantHz(20)).isLessThan(EarRule.MAX_FUNDAMENTAL_HZ);
        assertThatThrownBy(() -> FrogPondNiches.dominantHz(0)).isInstanceOf(IllegalArgumentException.class);
        FrogPondNiches.Frog a = new FrogPondNiches.Frog("a", 100);
        assertThat(FrogPondNiches.masks(a, new FrogPondNiches.Frog("b", 110))).isTrue();
        assertThat(FrogPondNiches.masks(a, new FrogPondNiches.Frog("c", 30))).isFalse();
    }

    @Test void judgeNamesTheMaskingPair() {
        FrogPondNiches w = FrogPondNiches.seeded(2);
        assertThat(w.judge(null).ok()).isFalse();
        assertThat(w.judge(new ArrayList<>(Collections.nCopies(w.frogs().size(), 3))).reason()).contains("only 3");
        boolean anyMask = false;
        for (int i = 0; i < w.frogs().size() && !anyMask; i++) {
            for (int j = i + 1; j < w.frogs().size(); j++) {
                anyMask |= FrogPondNiches.masks(w.frogs().get(i), w.frogs().get(j));
            }
        }
        FrogPondNiches.Verdict allTogether = w.judge(new ArrayList<>(Collections.nCopies(w.frogs().size(), 0)));
        assertThat(allTogether.ok()).isEqualTo(!anyMask);
        if (anyMask) {
            assertThat(allTogether.reason()).contains("masks the").contains("pond 1");
        }
    }
}