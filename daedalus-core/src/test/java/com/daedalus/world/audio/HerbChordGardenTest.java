// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.HashSet;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.Test;

class HerbChordGardenTest {
    @Test void everyCommissionIsSolvableAndTheSolutionIsPerfect() {
        Set<HerbChord.Effect> asked = new HashSet<>();
        for (long s = 0; s < 40; s++) {
            HerbChordGarden g = HerbChordGarden.seeded(s);
            asked.add(g.wanted());
            assertThat(g.target()).isBetween(2, 8);
            HerbChordGarden.Verdict v = g.judge(g.solution());
            assertThat(v.perfect()).isTrue();
            assertThat(v.lines()).isEqualTo(g.target());
            assertThat(g.hand().stream().map(Herb::id).distinct().count()).isEqualTo(9);
        }
        assertThat(asked).hasSizeGreaterThan(1);
    }

    @Test void noPlantingBeatsTheTarget() {
        HerbChordGarden g = HerbChordGarden.seeded(7);
        java.util.Random r = new java.util.Random(1);
        for (int k = 0; k < 3000; k++) {
            int[] bed = {0, 1, 2, 3, 4, 5, 6, 7, 8};
            for (int i = 8; i > 0; i--) {
                int j = r.nextInt(i + 1);
                int t = bed[i];
                bed[i] = bed[j];
                bed[j] = t;
            }
            HerbChordGarden.Verdict v = g.judge(bed);
            assertThat(v.lines()).isLessThanOrEqualTo(g.target());
            assertThat(v.perfect()).isEqualTo(v.lines() == g.target());
        }
    }

    @Test void linesMatchHerbChordAndPlayLowAndSoft() {
        HerbChordGarden g = HerbChordGarden.seeded(42);
        HerbChordGarden.Verdict v = g.judge(new int[] {0, 1, 2, 3, 4, 5, 6, 7, 8});
        assertThat(v.detail()).hasSize(HerbChordGarden.lineCount());
        for (HerbChordGarden.Line l : v.detail()) {
            int[] cells = HerbChordGarden.line(l.index());
            HerbChord.Result r = HerbChord.sound(List.of(g.hand().get(cells[0]), g.hand().get(cells[1]), g.hand().get(cells[2])));
            assertThat(l.chord().effect()).isEqualTo(r.effect());
            assertThat(l.fills()).isEqualTo(r.effect() == g.wanted());
            assertThat(l.playHz()).hasSize(r.frequencies().size());
            for (double hz : l.playHz()) {
                assertThat(hz).isBetween(60.0, 360.0);
            }
        }
        assertThat(HerbChordGarden.LINE_GAIN).isLessThanOrEqualTo(0.3);
        assertThat(v.lines()).isEqualTo((int) v.detail().stream().filter(HerbChordGarden.Line::fills).count());
    }

    @Test void seededIsRepeatableAndCommissionsAreConsonant() {
        HerbChordGarden a = HerbChordGarden.seeded(99);
        HerbChordGarden b = HerbChordGarden.seeded(99);
        assertThat(a.hand()).isEqualTo(b.hand());
        assertThat(a.wanted()).isEqualTo(b.wanted());
        assertThat(a.solution()).isEqualTo(b.solution());
        assertThat(a.seed()).isEqualTo(99);
        assertThat(HerbChordGarden.COMMISSIONS).doesNotContain(HerbChord.Effect.CHAOS, HerbChord.Effect.HASTE);
        int[] sol = a.solution();
        sol[0] = -5;
        assertThat(a.solution()[0]).isNotEqualTo(-5);
    }

    @Test void rejectsBadBeds() {
        HerbChordGarden g = HerbChordGarden.seeded(1);
        assertThatThrownBy(() -> g.judge(null)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> g.judge(new int[8])).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> g.judge(new int[] {0, 0, 1, 2, 3, 4, 5, 6, 7})).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> g.judge(new int[] {0, 1, 2, 3, 4, 5, 6, 7, 9})).isInstanceOf(IllegalArgumentException.class);
    }
}
