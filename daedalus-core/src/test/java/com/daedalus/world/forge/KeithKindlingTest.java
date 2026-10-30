// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;
import org.junit.jupiter.api.Test;

class KeithKindlingTest {

    private static boolean brute(long n) {
        if (n < 10) {
            return false;
        }
        List<Long> seq = new ArrayList<>();
        for (char c : Long.toString(n).toCharArray()) {
            seq.add((long) (c - '0'));
        }
        int d = seq.size();
        while (seq.get(seq.size() - 1) < n) {
            long s = 0;
            for (int i = seq.size() - d; i < seq.size(); i++) {
                s += seq.get(i);
            }
            seq.add(s);
        }
        return seq.get(seq.size() - 1) == n;
    }

    @Test
    void matchesListChainBruteForce() {
        List<Long> want = new ArrayList<>();
        for (long n = 1; n <= 200_000; n++) {
            boolean b = brute(n);
            assertThat(KeithKindling.isKeith(n)).as("n=%d", n).isEqualTo(b);
            if (b) {
                want.add(n);
            }
        }
        assertThat(KeithKindling.keithUpTo(200_000)).isEqualTo(want);
        Random r = new Random(488);
        for (int t = 0; t < 2000; t++) {
            long n = 10 + (long) (r.nextDouble() * 1e14);
            assertThat(KeithKindling.isKeith(n)).as("n=%d", n).isEqualTo(brute(n));
        }
    }

    @Test
    void knownKeithEmbers() {
        assertThat(KeithKindling.keithUpTo(1_000_000)).containsExactly(14L, 19L, 28L, 47L, 61L, 75L, 197L, 742L,
                1104L, 1537L, 2208L, 2580L, 3684L, 4788L, 7385L, 7647L, 7909L, 31331L, 34285L, 34348L, 55604L,
                62662L, 86935L, 93993L, 120284L, 129106L, 147640L, 156146L, 174680L, 183186L, 298320L, 355419L,
                694280L, 925993L);
        assertThat(KeithKindling.isKeith(1_084_051L)).isTrue();
        assertThat(KeithKindling.isKeith(7_913_837L)).isTrue();
        assertThat(KeithKindling.isKeith(11_436_171L)).isTrue();
    }

    @Test
    void trailsAreSound() {
        assertThat(KeithKindling.trail(14)).containsExactly(1L, 4L, 5L, 9L, 14L);
        assertThat(KeithKindling.trail(15)).containsExactly(1L, 5L, 6L, 11L, 17L);
        Random r = new Random(4880);
        for (int t = 0; t < 300; t++) {
            long n = 10 + (long) (r.nextDouble() * 1e15 - 10);
            List<Long> tr = KeithKindling.trail(n);
            int d = Long.toString(n).length();
            for (int i = d; i < tr.size(); i++) {
                long s = 0;
                for (int j = i - d; j < i; j++) {
                    s += tr.get(j);
                }
                assertThat(tr.get(i)).isEqualTo(s);
            }
            assertThat(tr.get(tr.size() - 1)).isGreaterThanOrEqualTo(n);
            assertThat(tr.get(tr.size() - 2)).isLessThan(n);
        }
    }

    @Test
    void edgesAndGuards() {
        for (long n = 1; n <= 9; n++) {
            assertThat(KeithKindling.isKeith(n)).isFalse();
            assertThat(KeithKindling.trail(n)).containsExactly(n);
        }
        assertThat(KeithKindling.isKeith(10)).isFalse();
        assertThat(KeithKindling.isKeith(KeithKindling.MAX_N)).isFalse();
        assertThat(KeithKindling.keithUpTo(13)).isEmpty();
        assertThat(KeithKindling.keithUpTo(14)).containsExactly(14L);
        assertThatThrownBy(() -> KeithKindling.isKeith(0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> KeithKindling.trail(KeithKindling.MAX_N + 1))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> KeithKindling.keithUpTo(KeithKindling.MAX_LIST + 1))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void gradesAndLines() {
        assertThat(KeithKindling.grade(197, true)).isEqualTo(KeithKindling.Grade.TURNED);
        assertThat(KeithKindling.grade(198, true)).isEqualTo(KeithKindling.Grade.SLIPPED);
        assertThat(KeithKindling.grade(198, false)).isEqualTo(KeithKindling.Grade.TURNED);
        for (KeithKindling.Grade g : KeithKindling.Grade.values()) {
            assertThat(KeithKindling.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(KeithKindling.QUEST_ID).isEqualTo("q_keith_kindling");
    }
}
