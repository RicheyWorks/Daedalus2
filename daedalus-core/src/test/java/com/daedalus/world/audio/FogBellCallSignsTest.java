// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.HashSet;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.Test;

class FogBellCallSignsTest {
    @Test void signsAreSpreadAndEveryNightDecodesToTheArrivingArk() {
        Set<Integer> blurs = new HashSet<>();
        for (long s = 0; s < 200; s++) {
            FogBellCallSigns f = FogBellCallSigns.seeded(s);
            int n = f.roster().size();
            assertThat(n).isBetween(4, 6);
            assertThat(new HashSet<>(f.roster())).hasSize(n);
            for (int i = 0; i < n; i++) {
                for (int j = i + 1; j < n; j++) {
                    assertThat(FogBellCallSigns.distance(f.sign(i), f.sign(j))).isGreaterThanOrEqualTo(3);
                }
            }
            String ark = f.decode(f.heard());
            assertThat(f.judge(ark).correct()).isTrue();
            assertThat(f.judge("Nobody").correct()).isFalse();
            blurs.add(f.blurred());
        }
        assertThat(blurs).contains(-1, 0, 6);
    }

    @Test void anySingleBlurStillDecodes() {
        FogBellCallSigns f = FogBellCallSigns.seeded(7);
        for (int i = 0; i < f.roster().size(); i++) {
            for (int b = 0; b < FogBellCallSigns.STROKES; b++) {
                assertThat(f.decode(f.sign(i) ^ 1 << b)).isEqualTo(f.roster().get(i));
            }
        }
    }

    @Test void seededIsDeterministic() {
        FogBellCallSigns a = FogBellCallSigns.seeded(42);
        FogBellCallSigns b = FogBellCallSigns.seeded(42);
        assertThat(a.roster()).isEqualTo(b.roster());
        assertThat(a.heard()).isEqualTo(b.heard());
        assertThat(a.seed()).isEqualTo(42);
    }

    @Test void textRoundTripsAndRejectsJunk() {
        assertThat(FogBellCallSigns.text(0b1010011)).isEqualTo("-.-..--");
        assertThat(FogBellCallSigns.parse("-.-..--")).isEqualTo(0b1010011);
        assertThatThrownBy(() -> FogBellCallSigns.parse("-.-")).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> FogBellCallSigns.parse(null)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> FogBellCallSigns.parse("-.-..-x")).isInstanceOf(IllegalArgumentException.class);
    }

    @Test void playbackFollowsEarRules() {
        FogBellCallSigns f = FogBellCallSigns.seeded(3);
        List<FogBellCallSigns.Stroke> p = f.playback();
        assertThat(p).hasSize(7);
        assertThat(p.get(0).onsetMs()).isZero();
        String h = f.judge("x").heard();
        for (int i = 0; i < 7; i++) {
            FogBellCallSigns.Stroke s = p.get(i);
            assertThat(s.isLong()).isEqualTo(h.charAt(i) == '-');
            assertThat(s.lengthMs()).isEqualTo(s.isLong() ? 540 : 180);
            if (i > 0) {
                assertThat(s.onsetMs()).isEqualTo(p.get(i - 1).onsetMs() + p.get(i - 1).lengthMs() + 240);
            }
        }
    }
}