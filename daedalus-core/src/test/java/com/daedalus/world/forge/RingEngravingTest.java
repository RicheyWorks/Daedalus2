// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.RingEngraving.Grade;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class RingEngravingTest {

    @Test
    void leastRotationAndZMatchBruteForce() {
        for (long seed = 0; seed < 300; seed++) {
            String s = RingEngraving.band(seed, (int) (seed % 30), 1 + (int) (seed % 4));
            int n = s.length();
            int best = 0;
            String bestRot = s;
            for (int r = 1; r < n; r++) {
                String rot = s.substring(r) + s.substring(0, r);
                if (rot.compareTo(bestRot) < 0) {
                    bestRot = rot;
                    best = r;
                }
            }
            assertThat(RingEngraving.leastRotation(s)).as("seed %d %s", seed, s).isEqualTo(best);
            assertThat(RingEngraving.canonical(s)).isEqualTo(bestRot);
            int[] z = RingEngraving.zArray(s);
            for (int i = 0; i < n; i++) {
                int v = 0;
                while (i + v < n && s.charAt(v) == s.charAt(i + v)) {
                    v++;
                }
                assertThat(z[i]).as("seed %d z[%d]", seed, i).isEqualTo(v);
            }
            if (n > 0) {
                int cut = (int) (seed % n);
                String turned = s.substring(cut) + s.substring(0, cut);
                assertThat(RingEngraving.sameRing(s, turned)).isTrue();
            }
        }
    }

    @Test
    void knownBands() {
        assertThat(RingEngraving.leastRotation("bca")).isEqualTo(2);
        assertThat(RingEngraving.leastRotation("abab")).isZero();
        assertThat(RingEngraving.leastRotation("")).isZero();
        assertThat(RingEngraving.sameRing("fuxa", "xafu")).isTrue();
        assertThat(RingEngraving.sameRing("fuxa", "fuax")).isFalse();
        assertThat(RingEngraving.sameRing("fu", "fux")).isFalse();
        assertThat(RingEngraving.zArray("aabxaab")).containsExactly(7, 1, 0, 0, 3, 1, 0);
    }

    @Test
    void gradesLinesAndReplay() {
        assertThat(RingEngraving.grade("bca", "abc", 2, true)).isEqualTo(Grade.MATCHED);
        assertThat(RingEngraving.grade("bca", "abc", 0, true)).isEqualTo(Grade.MISREAD);
        assertThat(RingEngraving.grade("bca", "acb", 2, true)).isEqualTo(Grade.MISREAD);
        for (Grade g : Grade.values()) {
            assertThat(RingEngraving.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(RingEngraving.QUEST_ID).isEqualTo("q_ring_engraving");
        assertThat(RingEngraving.band(5, 16, 4)).isEqualTo(RingEngraving.band(5, 16, 4)).hasSize(16);
        assertThatThrownBy(() -> RingEngraving.band(1, 3, 5)).isInstanceOf(IllegalArgumentException.class);
    }
}
