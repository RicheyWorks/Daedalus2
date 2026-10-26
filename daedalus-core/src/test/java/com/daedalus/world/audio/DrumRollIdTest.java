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

    @Test void irregularityCutOffHasMargin() {
        double minBroken = Double.MAX_VALUE;
        double maxSmooth = 0;
        for (long s = 0; s < 300; s++) {
            DrumRollId d = DrumRollId.seeded(s);
            double cv = DrumRollId.irregularity(d.onsets());
            if (d.answer().equals("sapsucker")) {
                minBroken = Math.min(minBroken, cv);
            } else {
                maxSmooth = Math.max(maxSmooth, cv);
            }
        }
        assertThat(minBroken).isGreaterThanOrEqualTo(DrumRollId.BROKEN_CV + 0.05);
        assertThat(maxSmooth).isLessThanOrEqualTo(DrumRollId.BROKEN_CV - 0.05);
    }

    @Test void steadyDrummersOpeningRatesAreSeparated() {
        java.util.Map<String, double[]> range = new java.util.HashMap<>();
        for (long s = 0; s < 300; s++) {
            DrumRollId d = DrumRollId.seeded(s);
            DrumRollId.Drummer card = DrumRollId.CARD.stream().filter(c -> c.name().equals(d.answer())).findFirst().orElseThrow();
            if (card.broken() || card.slowing() != 1.0) {
                continue;
            }
            double r = DrumRollId.openingRate(d.onsets());
            range.merge(card.name(), new double[] {r, r}, (a, b) -> new double[] {Math.min(a[0], b[0]), Math.max(a[1], b[1])});
        }
        double[] downy = range.get("downy woodpecker");
        double[] red = range.get("red-bellied woodpecker");
        double[] hairy = range.get("hairy woodpecker");
        assertThat(red[0] - downy[1]).as("downy %s vs red-bellied %s", java.util.Arrays.toString(downy), java.util.Arrays.toString(red))
            .isGreaterThanOrEqualTo(1.0);
        assertThat(hairy[0] - red[1]).as("red-bellied %s vs hairy %s", java.util.Arrays.toString(red), java.util.Arrays.toString(hairy))
            .isGreaterThanOrEqualTo(1.0);
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