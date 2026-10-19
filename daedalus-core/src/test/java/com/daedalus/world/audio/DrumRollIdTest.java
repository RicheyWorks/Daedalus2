// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.Test;

class DrumRollIdTest {
    @Test void identifierNamesEverySeededDrummer() {
        Set<String> seen = new HashSet<>();
        for (long s = 0; s < 300; s++) {
            DrumRollId d = DrumRollId.seeded(s);
            assertThat(d.onsets().get(0)).isZero();
            String id = DrumRollId.identify(d.onsets());
            assertThat(d.judge(id)).as("seed %d: %s heard as %s", s, d.answer(), id).isTrue();
            seen.add(d.answer());
            assertThat(d.seed()).isEqualTo(s);
        }
        assertThat(seen).hasSize(DrumRollId.CARD.size());
    }

    @Test void steadyRollsSeparateByRate() {
        List<Integer> downy = new ArrayList<>();
        List<Integer> hairy = new ArrayList<>();
        for (int i = 0; i < 16; i++) {
            downy.add(i * 1000 / 16);
            hairy.add(i * 1000 / 26);
        }
        assertThat(DrumRollId.identify(downy)).isEqualTo("downy woodpecker");
        assertThat(DrumRollId.identify(hairy)).isEqualTo("hairy woodpecker");
    }

    @Test void validationAndEar() {
        assertThatThrownBy(() -> DrumRollId.identify(List.of(0, 50))).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> DrumRollId.identify(null)).isInstanceOf(IllegalArgumentException.class);
        assertThat(DrumRollId.knockHz()).isEqualTo(110.0);
        assertThat(DrumRollId.seeded(1).judge("nobody")).isFalse();
    }
}