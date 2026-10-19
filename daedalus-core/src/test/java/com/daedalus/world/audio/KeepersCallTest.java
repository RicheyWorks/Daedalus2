// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

class KeepersCallTest {
    @Test void perfectEchoReachesTheEndAndPhrasesAvoidTripleRepeats() {
        for (long s = 0; s < 200; s++) {
            KeepersCall k = KeepersCall.seeded(s);
            List<KeepersCall.Stroke> full = k.call(KeepersCall.MAX_LENGTH);
            for (int i = 2; i < full.size(); i++) {
                assertThat(full.get(i).bell() == full.get(i - 1).bell() && full.get(i).bell() == full.get(i - 2).bell()).isFalse();
            }
            KeepersCall.Run r = k.start();
            while (!r.over()) {
                assertThat(r.echo(new ArrayList<>(r.call()))).isTrue();
            }
            assertThat(r.score()).isEqualTo(KeepersCall.MAX_LENGTH);
            assertThat(KeepersCall.stars(r.score())).isEqualTo(3);
            assertThat(k.seed()).isEqualTo(s);
        }
    }

    @Test void wrongBellOrLengthEndsTheRun() {
        KeepersCall k = KeepersCall.seeded(3);
        KeepersCall.Run r = k.start();
        for (int i = 0; i < 6; i++) {
            r.echo(r.call());
        }
        List<KeepersCall.Stroke> wrong = new ArrayList<>(r.call());
        KeepersCall.Stroke last = wrong.get(wrong.size() - 1);
        wrong.set(wrong.size() - 1, new KeepersCall.Stroke(last.bell(), !last.isLong()));
        assertThat(r.echo(wrong)).isFalse();
        assertThat(r.over()).isTrue();
        assertThat(r.score()).isEqualTo(6);
        assertThat(KeepersCall.stars(6)).isEqualTo(1);
        assertThat(KeepersCall.stars(5)).isZero();
        assertThat(KeepersCall.stars(9)).isEqualTo(2);
        assertThatThrownBy(() -> r.echo(List.of())).isInstanceOf(IllegalStateException.class);
    }

    @Test void timingPitchAndValidation() {
        List<KeepersCall.Stroke> c = List.of(new KeepersCall.Stroke(0, false), new KeepersCall.Stroke(4, true),
            new KeepersCall.Stroke(2, false));
        assertThat(KeepersCall.onsets(c)).containsExactly(0, 400, 1160);
        assertThat(c.get(0).hz()).isEqualTo(220.0);
        assertThat(c.get(1).lengthMs()).isEqualTo(540);
        assertThatThrownBy(() -> new KeepersCall.Stroke(5, false)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> KeepersCall.seeded(1).call(0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> KeepersCall.seeded(1).call(17)).isInstanceOf(IllegalArgumentException.class);
    }
}